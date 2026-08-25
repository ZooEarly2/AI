"""자유 대화 스키마 — 연동 규약 §3 ``/chat``.

STT → LLM → TTS 를 한 번에 도는 파이프라인이다. 현재 앱에 이 화면이 없어 호출되지
않지만(화면 매핑 문서), 게이트웨이에 경로가 살아 있어 계약을 맞춰 둔다.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel
from app.schemas.speech import AudioPayload


class ChatTurn(CamelModel):
    role: str  # user | assistant
    content: str


class ChatData(CamelModel):
    #: 아이가 한 말. 못 알아들었으면 ``None`` — 에러가 아니다(연동 규약 §5)
    user_text: str | None
    #: 상대 캐릭터의 답
    reply_text: str
    audio: AudioPayload | None = None
    history: list[ChatTurn] = Field(default_factory=list)
    mock: bool | None = None
