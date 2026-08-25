from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator

from app.core.config import settings
from app.schemas.common import CamelModel, CamelRequest


class SynthesizeRequest(CamelRequest):
    """TTS 요청 — 연동 규약 §3.

    ``language`` 는 필수다. 같은 엔드포인트로 한국어 문장과 모국어 번역이 둘 다
    오기 때문에 텍스트로 추측하지 않는다. 초기 명세의 ``language_code`` 로 보내도
    받는다(별칭이 아니라 아래 validator 가 표기를 흡수한다).
    """

    text: str
    # 초기 명세의 language_code 로 보내도 받는다. 한쪽만 받으면 그쪽으로 부르던
    # 호출이 전부 조용히 기본값(KOREAN)으로 떨어져 모국어 재생이 한국어로 나온다.
    language: str = Field(
        default="KOREAN",
        validation_alias=AliasChoices("language", "languageCode", "language_code"),
    )
    voice: str | None = None  # TEACHER | FRIEND
    speed: float = settings.tts_default_speed

    @field_validator("speed")
    @classmethod
    def _clamp_speed(cls, value: float) -> float:
        # 게이트웨이가 0.5~1.5 로 이미 검증하지만, 직접 호출도 막는다.
        return min(1.5, max(0.5, value))


class WordTiming(CamelModel):
    word: str
    start: float
    end: float


class Segment(CamelModel):
    start: float
    end: float
    text: str
    words: list[WordTiming] = Field(default_factory=list)


class TranscribeData(CamelModel):
    """STT 성공 응답의 ``data``.

    ``text``/``confidence`` 가 ``None`` 인 200 응답은 정상이다 — "못 알아들었다"는
    뜻이고, 엔진 장애(422 STT_FAILED)와 구분된다(연동 규약 §5).
    """

    text: str | None
    confidence: float | None = None
    language: str = "KOREAN"
    duration_sec: float = 0.0
    segments: list[Segment] = Field(default_factory=list)


class AudioPayload(CamelModel):
    """base64 로 실어 보내는 오디오.

    게이트웨이가 body 를 String 으로 받기 때문에 바이너리(audio/mpeg)를 그대로
    내보내면 깨진다(연동 규약 §1-1 표 1번). 그래서 JSON 안에 base64 로 담는다.
    """

    data: str
    format: str = "mp3"


class SynthesizeData(CamelModel):
    audio: AudioPayload
    #: 목 제공자가 만든 소리라는 표시. 앱이 브라우저 TTS 로 대신 읽어줄지 판단한다.
    #: 실제 음성이면 아예 내려가지 않는다(None 은 직렬화에서 빠진다).
    mock: bool | None = None
