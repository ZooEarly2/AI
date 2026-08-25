from __future__ import annotations

from typing import Protocol, TypedDict


class WordTimingDict(TypedDict):
    word: str
    start: float
    end: float


class SegmentDict(TypedDict):
    start: float
    end: float
    text: str
    words: list[WordTimingDict]


class TranscriptionResult(TypedDict):
    #: 못 알아들었으면 ``None``. 에러가 아니다 — 앱은 그대로 다음 화면으로 간다
    text: str | None
    confidence: float | None
    language: str
    duration_sec: float
    segments: list[SegmentDict]


class SynthesisResult(TypedDict):
    """오디오 바이트와 컨테이너 형식.

    형식을 함께 돌려주는 이유: 실제 제공자는 mp3 를 만들지만 목 제공자는 표준
    라이브러리로 만들 수 있는 wav 를 준다. 앱이 ``data:audio/{format};base64`` 로
    재생하므로 형식이 틀리면 소리가 안 난다.
    """

    audio: bytes
    format: str


class WordScoreDict(TypedDict):
    word: str
    z: float | None
    warn: bool
    worst_phone: str | None


class PronunciationScoreResult(TypedDict):
    sentence: str
    off_script: bool
    words: list[WordScoreDict]


class ExpressionFeedbackResult(TypedDict):
    reaction: str
    comment: str
    natural_sentence: str
    natural_hint: str
    highlight_words: list[str]


class StorySceneResult(TypedDict):
    category: str
    subtitle: str
    opening: str
    quote: str | None
    narration: str


class StoryResult(TypedDict):
    title: str
    scenes: list[StorySceneResult]


class ChatResult(TypedDict):
    user_text: str | None
    reply_text: str


class InferenceProvider(Protocol):
    """제공자(mock/real)가 지켜야 할 계약.

    라우트·서비스는 이 인터페이스만 보므로 app.state 뒤에 무엇이 있는지 알 필요가 없다.
    """

    #: 목 제공자인가. 응답의 ``mock`` 플래그로 나가, 앱이 브라우저 TTS 로 대신
    #: 읽어줄지 판단하는 근거가 된다.
    is_mock: bool

    def warm_up_scoring(self) -> None:
        """채점 서비스를 미리 깨운다. 곧바로 돌아와야 한다.

        아이가 연습 화면에 들어올 때 부른다 — 마이크를 누른 **뒤에** 콜드 스타트를
        겪게 하지 않으려는 것이다. 실패는 조용히 넘긴다.
        """

    def transcribe(self, audio_path: str, language_code: str) -> TranscriptionResult: ...

    def synthesize(
        self, text: str, language_code: str, voice: str | None, speed: float
    ) -> SynthesisResult: ...

    def translate(self, text: str, source_language: str, target_language: str) -> str: ...

    def score_pronunciation(self, audio_path: str, text: str) -> PronunciationScoreResult: ...

    def expression_feedback(
        self,
        target_sentence: str,
        recognized_text: str | None,
        scenario: str | None,
        nickname: str,
    ) -> ExpressionFeedbackResult: ...

    def generate_story(self, child_name: str, scenes: list[dict]) -> StoryResult: ...

    def chat(
        self,
        audio_path: str,
        scenario: str,
        history: list[dict],
        nickname: str,
        native_language: str | None,
    ) -> ChatResult: ...
