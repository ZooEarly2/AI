"""CLOVA Voice Premium — 한국어 음성 합성.

한국어는 CLOVA 로 만든다. OpenAI TTS 보다 한국어 억양이 자연스럽고, 아이가 따라
말할 문장을 또박또박 읽어준다. 다만 CLOVA Voice 는 **베트남어를 지원하지 않는다** —
그쪽은 OpenAI TTS 로 넘긴다(real.py 참고).

인증은 헤더 두 개다. 네이버 클라우드 콘솔의 Application 에서 발급한 값을 쓴다.
    X-NCP-APIGW-API-KEY-ID  : CLOVA_CLIENT_ID
    X-NCP-APIGW-API-KEY     : CLOVA_CLIENT_SECRET
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"


class ClovaTtsError(Exception):
    """CLOVA 호출 실패. 부르는 쪽이 다른 엔진으로 넘어갈 수 있게 따로 둔다."""


def load_clova_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "X-NCP-APIGW-API-KEY-ID": settings.clova_client_id,
            "X-NCP-APIGW-API-KEY": settings.clova_client_secret,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=settings.clova_timeout_sec,
    )


def to_clova_speed(multiplier: float) -> int:
    """앱의 속도 배수(0.5~1.5)를 CLOVA 의 speed 눈금(-5~5)으로 옮긴다.

    두 눈금은 방향이 반대다 — 앱은 **클수록 빠르고**, CLOVA 는 **클수록 느리다**.
    그대로 넘기면 느리게 읽어달라는 요청이 빠르게 읽히므로 뒤집어서 보낸다.

        0.5(가장 느리게) → +5 · 1.0(보통) → 0 · 1.5(가장 빠르게) → -5
    """
    return max(-5, min(5, round((1.0 - multiplier) * 10)))


def synthesize(client: httpx.Client, text: str, voice: str, speed: float) -> bytes:
    data = {
        "speaker": voice,
        "text": text,
        "speed": str(to_clova_speed(speed)),
        "format": "mp3",
        # 아이에게 읽어주는 문장이라 조금 밝고 높게. 값이 커질수록 낮아진다.
        "pitch": "-1",
        "volume": "0",
    }
    try:
        response = client.post(TTS_URL, data=data)
    except httpx.RequestError as exc:
        raise ClovaTtsError(f"CLOVA 연결 실패: {exc}") from exc

    if response.status_code >= 400:
        # 본문에 원인이 들어 있다(잘못된 speaker, 사용량 초과 등). 로그에만 남긴다.
        raise ClovaTtsError(f"CLOVA {response.status_code}: {response.text[:200]}")

    if not response.content:
        raise ClovaTtsError("CLOVA 가 빈 응답을 돌려줬습니다.")
    return response.content
