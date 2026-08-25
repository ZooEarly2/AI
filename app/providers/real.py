"""실제 모델·API 를 InferenceProvider 계약에 연결한다.

클라이언트 인스턴스는 main.py 의 lifespan 에서 한 번 만들어 app.state 에 둔다.
요청마다 새로 만들면 연결을 매번 새로 여는 낭비가 된다.

**whisper 만 예외로 늦게 올린다.** 모델 파일이 수백 MB 라 기동할 때 올리면 서버가
그만큼 늦게 뜨고, 지금 앱 화면은 STT 를 부르지 않는다(표현 고르기 한 갈래만 쓴다).
처음 /speech/transcribe 가 들어올 때 올려서 app.state 에 담아 두고 그 뒤로는 재사용한다.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import (
    ChatResult,
    ExpressionFeedbackResult,
    PronunciationScoreResult,
    StoryResult,
    SynthesisResult,
    TranscriptionResult,
)
from app.providers.clients import (
    chat_client,
    clova_client,
    expression_client,
    scoring_client,
    story_client,
    translate_client,
    tts_client,
    whisper_client,
)

log = get_logger(__name__)


class RealProvider:
    is_mock = False

    def __init__(self, state: Any):
        #: FastAPI app.state — 늦게 올리는 whisper 를 여기에 담아 둔다
        self._state = state
        self._openai: OpenAI = state.openai_client
        self._scoring = state.scoring_client
        self._clova = state.clova_client

    def warm_up_scoring(self) -> None:
        scoring_client.warm_up(self._scoring)

    # ── STT ────────────────────────────────────────

    def _whisper(self):
        """처음 부를 때 한 번만 모델을 올린다."""
        model = getattr(self._state, "whisper_model", None)
        if model is None:
            log.info("faster-whisper 모델 로딩 (%s)...", settings.whisper_model_size)
            model = whisper_client.load_whisper_model(
                model_size=settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            self._state.whisper_model = model
            log.info("모델 로딩 완료.")
        return model

    def transcribe(self, audio_path: str, language_code: str) -> TranscriptionResult:
        return whisper_client.transcribe(self._whisper(), audio_path, language_code)

    # ── TTS ────────────────────────────────────────

    def synthesize(
        self, text: str, language_code: str, voice: str | None, speed: float
    ) -> SynthesisResult:
        """한국어는 CLOVA, 나머지 언어는 OpenAI.

        CLOVA Voice 는 한국어 억양이 자연스러워 아이가 따라 말할 문장에 맞지만
        **베트남어를 지원하지 않는다.** 모국어를 읽어주는 것이 이 앱의 핵심이라
        그쪽은 여러 언어를 다루는 OpenAI 로 넘긴다.

        CLOVA 가 실패해도 소리는 나야 한다 — 그때도 OpenAI 로 넘어간다.
        아이 입장에서는 "눌렀는데 아무 소리도 안 난다"가 가장 나쁜 실패다.
        """
        if language_code == "ko" and settings.clova_client_id:
            # 앱은 "누가 말하는가"(선생님/친구)만 고른다. 실제 목소리는 서버가 정한다.
            friend = (voice or "").upper() == "FRIEND" and settings.clova_tts_voice_friend
            try:
                audio = clova_client.synthesize(
                    self._clova,
                    text=text,
                    voice=friend or settings.clova_tts_voice,
                    speed=speed,
                )
                return {"audio": audio, "format": "mp3"}
            except clova_client.ClovaTtsError as exc:
                log.warning("CLOVA TTS 실패, OpenAI 로 대체합니다: %s", exc)

        audio = tts_client.synthesize(self._openai, text=text, voice=voice, speed=speed)
        return {"audio": audio, "format": "mp3"}

    # ── 그 밖 ──────────────────────────────────────

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        return translate_client.translate(
            self._openai,
            text=text,
            source_language=source_language,
            target_language=target_language,
        )

    def score_pronunciation(self, audio_path: str, text: str) -> PronunciationScoreResult:
        result = scoring_client.score_word(self._scoring, audio_path=audio_path, text=text)
        return {
            "sentence": result.get("clean_text") or result.get("text") or text,
            "off_script": bool(result.get("off_script")),
            "words": [
                {
                    "word": w["word"],
                    "z": w.get("z"),
                    "warn": bool(w.get("warn")),
                    "worst_phone": w.get("worst_phone"),
                }
                for w in result.get("words", [])
            ],
        }

    def expression_feedback(
        self,
        target_sentence: str,
        recognized_text: str | None,
        scenario: str | None,
        nickname: str,
    ) -> ExpressionFeedbackResult:
        return expression_client.expression_feedback(
            self._openai,
            target_sentence=target_sentence,
            recognized_text=recognized_text,
            scenario=scenario,
            nickname=nickname,
        )

    def generate_story(self, child_name: str, scenes: list[dict]) -> StoryResult:
        return story_client.generate_story(self._openai, child_name, scenes)

    def chat(
        self,
        audio_path: str,
        scenario: str,
        history: list[dict],
        nickname: str,
        native_language: str | None,
    ) -> ChatResult:
        # 아이 말을 못 알아들어도 대화를 끊지 않는다 — user_text 를 None 으로 두고
        # LLM 이 "다시 말해줄래?" 로 이어가게 한다(연동 규약 §5).
        transcription = whisper_client.transcribe(self._whisper(), audio_path, "ko")
        user_text = transcription["text"]
        reply = chat_client.reply(
            self._openai,
            user_text=user_text,
            scenario=scenario,
            history=history,
            nickname=nickname,
        )
        return {"user_text": user_text, "reply_text": reply}
