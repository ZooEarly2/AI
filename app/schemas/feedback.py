from __future__ import annotations

from app.core.sentences import SentenceId
from pydantic import Field

from app.schemas.common import CamelModel, CamelRequest


class SentenceItem(CamelModel):
    sentence_id: SentenceId
    category: str
    text: str
    #: 모국어 번역 — 표현 퀴즈의 힌트(전구)가 이 값을 띄운다.
    #:
    #: 언어 코드를 키로 담아 **한 번에 다 준다**(`{"vi": "...", "zh": "..."}`).
    #: 아이 모국어는 앱에만 있고, 어차피 10문장뿐이라 골라 보내려고 요청을 나누는 것이
    #: 더 번거롭다. 앱은 화면 진입 때 받아 두었다가 전구를 누르는 즉시 띄운다 —
    #: 그 순간 서버를 부르면 아이는 버튼이 안 눌린 줄 알고 다시 누른다.
    translations: dict[str, str] = Field(default_factory=dict)
    #: 번역문의 어느 조각이 한국어 어느 어절인지 — 빈칸 자리를 짚어주는 데 쓴다.
    #:
    #: `{"vi": [{"t": "Cho con", "k": [1]}, {"t": "một chút thôi ạ.", "k": [0]}]}`
    #: 조각은 **번역문을 읽는 순서**대로다. 한국어 순서가 아니라서 k 가 뒤죽박죽인
    #: 것이 정상이다. 한 조각이 어절 여럿을 덮을 수 있고(굳은 인사), 대응하는
    #: 어절이 없으면 k 는 빈 목록이다.
    #:
    #: 동시(study)에는 없다 — 시는 빈칸 퀴즈를 내지 않는다. 그래서 앱은 이 값이
    #: 비어 있을 수 있다고 보고 짜야 한다(그때는 뜻만 통째로 보여준다).
    translation_parts: dict[str, list[dict[str, object]]] = Field(default_factory=dict)


class WordScore(CamelModel):
    word: str
    z: float | None
    warn: bool
    worst_phone: str | None


class SpeakingFeedbackData(CamelModel):
    """발음 채점 결과 — 연동 규약 §3 ``/feedback/speaking``.

    ``target_word`` 가 ``None`` 이면 어절이 전부 기준(z ≥ -1.5) 이상이라는 뜻이고
    에러가 아니다. 앱은 이 값만 보고 칭찬 화면 / 빈칸 퀴즈로 갈린다.

    ``quiz_sentence`` 는 일부러 없다 — 빈칸 문장은 앱이 ``sentence`` 를 공백으로
    나눠 ``target_index`` 번째를 비워 직접 만든다(2026-08-24 명세에서 제외).
    """

    sentence_id: SentenceId
    sentence: str
    target_word: str | None
    target_index: int | None
    target_z: float | None
    words: list[WordScore]


class ExpressionFeedbackRequest(CamelRequest):
    """표현 교정 요청 — 연동 규약 §3 ``/feedback/expression``.

    발음 채점과 다르다. 저쪽은 "어떻게 소리 냈나"를 오디오로 보고, 이쪽은
    "어떤 말을 골랐나"를 STT 텍스트로 본다.
    """

    target_sentence: str
    #: STT 가 못 알아들으면 ``None`` 이 온다. 키는 반드시 있다(연동 규약 §3).
    recognized_text: str | None = None
    scenario: str | None = None
    native_language: str | None = None
    nickname: str


class ExpressionFeedbackData(CamelModel):
    """③ 피드백 배너 · ④ 자연스러운 표현 화면이 그대로 그리는 값.

    번역을 여기 합쳐 내려보낸다 — 앱이 ``/translate`` 를 따로 부르면 화면이 두 번
    늦게 뜬다(연동 규약 §1-1).
    """

    #: 말풍선 — 알아들었다는 반응
    reaction: str
    #: 안내 카드 문구
    comment: str
    #: 권하는 한국어 문장
    natural_sentence: str
    #: 왜 그렇게 말하는지 한 줄 설명
    natural_hint: str
    #: ``natural_sentence`` 안에서 짚어줄 어절들
    highlight_words: list[str]
    #: 모국어 번역. ``native_language`` 가 KOREAN 이거나 없으면 ``None``
    translation: str | None = None
    translation_language: str | None = None
