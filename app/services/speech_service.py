"""STT / TTS 서비스."""

from __future__ import annotations

import base64
import os

from fastapi import UploadFile

from app.core.audio_probe import UndecodableAudio, probe_duration_sec
from app.core.audio_storage import save_temp_audio
from app.core.config import settings
from app.core.exceptions import InvalidRequest, SttFailed, UpstreamUnavailable
from app.core.languages import DEFAULT_LANGUAGE_CODE, to_code, to_enum
from app.core.logging import get_logger
from app.providers.base import InferenceProvider
from app.schemas.speech import AudioPayload, SynthesizeData, SynthesizeRequest, TranscribeData

log = get_logger(__name__)

#: 게이트웨이가 200자로 이미 끊지만, 직접 호출도 막는다. 길면 TTS 지연이 급격히 는다.
_MAX_TTS_CHARS = 200


def transcribe_audio(
    provider: InferenceProvider, audio_file: UploadFile, language: str | None
) -> TranscribeData:
    """녹음을 텍스트로 옮긴다.

    ``language`` 는 BCP-47 자유 문자열(``ko-KR``)이고 생략될 수 있다 — 게이트웨이는
    선택 필드를 빈 값이 아니라 파트째로 빼고 보낸다(연동 규약 §2-②). 모르는 값이 와도
    거절하지 않고 한국어로 본다: 아이가 녹음을 마친 뒤에 언어 코드 때문에 실패시키는
    것은 이 앱에서 가장 나쁜 실패다.
    """
    language_code = to_code(language, default=DEFAULT_LANGUAGE_CODE)
    if language_code is None:
        log.info("알 수 없는 language=%r — 한국어로 처리한다", language)
        language_code = DEFAULT_LANGUAGE_CODE

    with save_temp_audio(audio_file) as audio_path:
        _reject_empty(audio_path)
        _reject_too_long(audio_path)

        try:
            result = provider.transcribe(audio_path, language_code)
        except Exception as exc:
            # 엔진이 죽은 경우다. "못 알아들었다"(text: null, 200)와 구분해야 한다 —
            # 앱은 422 를 장애로, null 을 정상 진행으로 다룬다(연동 규약 §5).
            log.warning("STT 실패: %s", exc)
            raise SttFailed("음성을 인식하지 못했습니다.") from exc

    return TranscribeData(
        text=result["text"],
        confidence=result.get("confidence"),
        language=to_enum(result.get("language") or language_code),
        duration_sec=round(float(result.get("duration_sec") or 0.0), 2),
        segments=result.get("segments") or [],
    )


def synthesize_speech(provider: InferenceProvider, request: SynthesizeRequest) -> SynthesizeData:
    """문장을 소리로 바꾼다.

    바이너리가 아니라 base64 JSON 으로 돌려준다 — 게이트웨이가 body 를 String 으로
    받아 그대로 통과시키기 때문에 바이너리는 도중에 깨진다(연동 규약 §1-1 표 1번).
    """
    text = request.text.strip()
    if not text:
        raise InvalidRequest("읽을 문장이 비어 있습니다.", field="text")
    if len(text) > _MAX_TTS_CHARS:
        raise InvalidRequest(f"문장이 {_MAX_TTS_CHARS}자를 넘었습니다.", field="text")

    language_code = to_code(request.language)
    if language_code is None:
        raise InvalidRequest("지원하지 않는 언어입니다.", field="language")

    try:
        result = provider.synthesize(
            text=text,
            language_code=language_code,
            voice=request.voice,
            speed=request.speed,
        )
    except Exception as exc:
        log.warning("TTS 실패: %s", exc)
        raise UpstreamUnavailable("음성 합성 서비스에 연결할 수 없습니다.") from exc

    return SynthesizeData(
        audio=AudioPayload(
            data=base64.b64encode(result["audio"]).decode("ascii"),
            format=result["format"],
        ),
        # 목 제공자의 차임이면 앱이 브라우저 TTS 로 대신 읽어준다. 실제 음성일 때는
        # 키가 아예 내려가지 않아 앱이 서버 음성만 재생한다.
        mock=True if getattr(provider, "is_mock", False) else None,
    )


def _reject_empty(audio_path: str) -> None:
    if os.path.getsize(audio_path) == 0:
        raise InvalidRequest("녹음 파일이 비어 있습니다.", field="audio")


def _reject_too_long(audio_path: str) -> None:
    try:
        duration = probe_duration_sec(audio_path)
    except UndecodableAudio as exc:
        raise InvalidRequest("오디오로 읽을 수 없는 파일입니다.", field="audio") from exc

    if duration is not None and duration > settings.max_audio_duration_sec:
        raise InvalidRequest(
            f"오디오 길이가 {settings.max_audio_duration_sec}초를 넘었습니다.", field="audio"
        )
