"""자유 대화 — STT → LLM → TTS 를 한 번에 돈다.

현재 앱에 이 화면이 없어 호출되지 않지만(화면 매핑 문서), 게이트웨이에 경로가 살아
있어 계약을 맞춰 둔다. 나중에 화면이 생기면 앱에서 부르기만 하면 된다.
"""

from __future__ import annotations

import base64
import json

from fastapi import UploadFile

from app.core.audio_storage import save_temp_audio
from app.core.exceptions import InvalidRequest, SttFailed
from app.core.languages import to_code
from app.core.logging import get_logger
from app.providers.base import InferenceProvider
from app.schemas.chat import ChatData, ChatTurn
from app.schemas.speech import AudioPayload

log = get_logger(__name__)

SCENARIOS = {"ARRIVAL", "CLASS", "LUNCH", "DISMISSAL"}
_MAX_HISTORY_TURNS = 10


def chat(
    provider: InferenceProvider,
    audio_file: UploadFile,
    scenario: str,
    history_raw: str | None,
    nickname: str,
    native_language: str | None,
) -> ChatData:
    if scenario not in SCENARIOS:
        raise InvalidRequest("알 수 없는 시나리오입니다.", field="scenario")
    nickname = (nickname or "").strip()
    if not nickname or len(nickname) > 20:
        raise InvalidRequest("아이 호칭이 올바르지 않습니다.", field="nickname")

    history = _parse_history(history_raw)

    with save_temp_audio(audio_file) as audio_path:
        try:
            result = provider.chat(
                audio_path=audio_path,
                scenario=scenario,
                history=history,
                nickname=nickname,
                native_language=to_code(native_language, default=None),
            )
        except Exception as exc:
            log.warning("대화 실패: %s", exc)
            raise SttFailed("음성을 인식하지 못했습니다.") from exc

    reply_text = result["reply_text"]
    audio = None
    try:
        speech = provider.synthesize(reply_text, "ko", "TEACHER", 0.9)
        audio = AudioPayload(
            data=base64.b64encode(speech["audio"]).decode("ascii"), format=speech["format"]
        )
    except Exception as exc:
        # 음성이 없어도 대사는 화면에 뜬다. 여기서 전체를 실패시키면 대화가 끊긴다.
        log.info("대화 음성 합성 생략(실패): %s", exc)

    next_history = [*history, {"role": "assistant", "content": reply_text}]
    if result["user_text"]:
        next_history.insert(len(history), {"role": "user", "content": result["user_text"]})

    return ChatData(
        user_text=result["user_text"],
        reply_text=reply_text,
        audio=audio,
        history=[ChatTurn(**turn) for turn in next_history[-_MAX_HISTORY_TURNS:]],
        mock=True if getattr(provider, "is_mock", False) else None,
    )


def _parse_history(raw: str | None) -> list[dict]:
    """``history`` 는 파싱된 배열이 아니라 **JSON 문자열**로 온다(연동 규약 §3).

    빈 대화는 ``"[]"`` 로 오지만, 파트 자체가 없을 수도 있다 — 둘 다 "아직 대화가
    없다"로 같게 다룬다.
    """
    if not raw or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidRequest("history 형식이 올바르지 않습니다.", field="history") from exc
    if not isinstance(parsed, list):
        raise InvalidRequest("history는 배열이어야 합니다.", field="history")

    turns = []
    for turn in parsed:
        if (
            isinstance(turn, dict)
            and turn.get("role") in ("user", "assistant")
            and isinstance(turn.get("content"), str)
        ):
            turns.append({"role": turn["role"], "content": turn["content"]})
    return turns[-_MAX_HISTORY_TURNS:]
