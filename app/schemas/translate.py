from __future__ import annotations

from app.schemas.common import CamelModel, CamelRequest


class TranslateRequest(CamelRequest):
    text: str
    source_language: str = "KOREAN"
    target_language: str


class TranslateData(CamelModel):
    """번역 결과.

    필드명이 ``translated_text`` 가 아니라 ``translation`` 이다 — 앱이 읽는 이름
    (연동 규약 §1-1 표 4번). ``target_language`` 는 enum 으로 올려 보낸다.
    """

    translation: str
    target_language: str
