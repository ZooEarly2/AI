"""목 제공자 — 키 없이 전 구간을 돌리기 위한 고정 응답.

로컬 시연과 Spring 연동 테스트가 이 위에서 돈다. 그래서 "형식만 맞는 더미"가 아니라
**화면에 그대로 띄워도 어색하지 않은 한국어**를 만든다. 아이가 보는 문구가 깨져 있으면
연동이 안 된 건지 화면이 잘못된 건지 구분할 수 없다.
"""

from __future__ import annotations

from app.core.audio_tone import chime_wav
from app.core.korean import josa, vocative
from app.core.sentences import translations_of
from app.providers.base import (
    ChatResult,
    ExpressionFeedbackResult,
    PronunciationScoreResult,
    StoryResult,
    StorySceneResult,
    SynthesisResult,
    TranscriptionResult,
)

#: 추천 문장 10개의 모국어 번역. "이 말의 뜻이에요!" 화면이 이 값을 그대로 쓴다.

#: 장면별 동화 문구 틀. 실제 기록(상대 대사·아이가 고른 말)만 넣고 새 사건은 만들지 않는다.
_SCENE_TEMPLATES: dict[str, dict[str, str]] = {
    "school_arrival": {"subtitle": "반가운 아침 인사", "opening": "교문 앞이었어요"},
    "class": {"subtitle": "동시를 읽은 시간", "opening": "교실 문을 열자"},
    "lunch": {"subtitle": "맛있는 점심시간", "opening": "고소한 냄새가 났어요"},
    "school_departure": {"subtitle": "다정한 하굣길", "opening": "가방을 메고 나서니"},
}


class MockProvider:
    """PROVIDER=mock 일 때 쓰는 제공자. 모델도 API 키도 필요 없다."""

    is_mock = True

    def warm_up_scoring(self) -> None:
        """깨울 것이 없다. 목은 곧바로 답한다."""

    # ── 음성 ───────────────────────────────────────────────

    def transcribe(self, audio_path: str, language_code: str) -> TranscriptionResult:
        return {
            "text": "안녕 나도 반가워",
            "confidence": 0.92,
            "language": language_code,
            "duration_sec": 2.3,
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.3,
                    "text": "안녕 나도 반가워",
                    "words": [
                        {"word": "안녕", "start": 0.0, "end": 1.1},
                        {"word": "나도", "start": 1.1, "end": 1.7},
                        {"word": "반가워", "start": 1.7, "end": 2.3},
                    ],
                }
            ],
        }

    def synthesize(
        self, text: str, language_code: str, voice: str | None, speed: float
    ) -> SynthesisResult:
        # 실제로 들리는 차임을 준다 — 재생까지 되는지 귀로 확인할 수 있어야 한다.
        return {"audio": chime_wav(text), "format": "wav"}

    # ── 번역 ───────────────────────────────────────────────

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if target_language == source_language:
            return text
        table = translations_of(text)
        if target_language in table:
            return table[target_language]
        # 사전에 없는 문장은 원문을 돌려준다 — 지어낸 번역을 아이에게 보여주지 않는다.
        return text

    # ── 발음 채점 ──────────────────────────────────────────

    def score_pronunciation(self, audio_path: str, text: str) -> PronunciationScoreResult:
        # 어절이 뒤로 갈수록 z를 낮춰 고정한다 — 어떤 문장을 넣어도 "마지막 어절이
        # 가장 취약하다"가 예측 가능해서, 통합 테스트가 안정적으로 돈다.
        tokens = text.split() or [text]
        words = []
        for i, token in enumerate(tokens):
            z = round(-0.6 * i, 2)
            warn = z < -1.5
            words.append(
                {"word": token, "z": z, "warn": warn, "worst_phone": "ㄹ" if warn else None}
            )
        return {"sentence": text, "off_script": False, "words": words}

    # ── 표현 교정 ──────────────────────────────────────────

    def expression_feedback(
        self,
        target_sentence: str,
        recognized_text: str | None,
        scenario: str | None,
        nickname: str,
    ) -> ExpressionFeedbackResult:
        if recognized_text and recognized_text.strip():
            reaction = "잘했어!\n무슨 말인지 이해했어."
        else:
            # 못 알아들은 것은 실패가 아니다. 아이를 탓하지 않고 그대로 다음으로 보낸다.
            reaction = "괜찮아!\n다시 한 번 해볼까?"
        return {
            "reaction": reaction,
            "comment": f"{vocative(nickname)}, 잘 대답했어요!\n다음에는 이렇게 말해볼까요?",
            "natural_sentence": target_sentence,
            "natural_hint": _hint_for(target_sentence),
            "highlight_words": _missing_words(target_sentence, recognized_text),
        }

    # ── 동화 ───────────────────────────────────────────────

    def generate_story(self, child_name: str, scenes: list[dict]) -> StoryResult:
        return {
            "title": f"{josa(child_name, '이', '')}의 오늘 학교 이야기",
            "scenes": [_mock_scene(child_name, scene) for scene in scenes],
        }

    # ── 자유 대화 ──────────────────────────────────────────

    def chat(
        self,
        audio_path: str,
        scenario: str,
        history: list[dict],
        nickname: str,
        native_language: str | None,
    ) -> ChatResult:
        replies = {
            "ARRIVAL": "안녕! 오늘도 만나서 반가워.",
            "CLASS": "좋아요, 같이 천천히 읽어볼까요?",
            "LUNCH": "알았어, 맛있게 먹으렴.",
            "DISMISSAL": "오늘도 수고했어, 내일 봐!",
        }
        return {
            "user_text": "안녕 나도 반가워",
            "reply_text": replies.get(scenario, f"{vocative(nickname)}, 잘 말했어!"),
        }


# ── 내부 헬퍼 ─────────────────────────────────────────────


def _hint_for(sentence: str) -> str:
    """문장 끝맺음을 보고 한 줄 설명을 고른다. 화면의 작은 안내 문구다."""
    stripped = sentence.strip().rstrip("!?.")
    if stripped.endswith(("주세요", "가세요", "습니다", "합니다", "뵙겠습니다")):
        return "어른께는 끝을 '-요', '-습니다'로 맺으면 더 공손해요."
    if stripped.endswith(("놀자", "가자", "들어가자")):
        return "친구에게는 이렇게 편하게 말해도 좋아요."
    return "또박또박 끝까지 말하면 더 잘 전해져요."


def _missing_words(target: str, recognized: str | None) -> list[str]:
    """권하는 문장에는 있는데 아이가 말하지 않은 어절.

    화면이 이 어절만 색으로 짚어준다. 인식이 실패했으면(``None``) 짚을 근거가
    없으므로 빈 목록이다 — 아무 말도 못 알아들은 상태에서 문장 전체를 칠하면
    아이에게는 "다 틀렸다"로 읽힌다.
    """
    if not recognized or not recognized.strip():
        return []
    said = {word.strip(" !?.,~") for word in recognized.split()}
    return [word for word in target.split() if word.strip(" !?.,~") not in said]


def _mock_scene(child_name: str, scene: dict) -> StorySceneResult:
    category = scene.get("category", "school_arrival")
    template = _SCENE_TEMPLATES.get(category, _SCENE_TEMPLATES["school_arrival"])
    subject = josa(child_name, "이가", "가")
    partner_line = (scene.get("partner_line") or "").strip()
    child_said = (scene.get("child_said") or "").strip() or None
    poem_text = (scene.get("poem_text") or "").strip()
    practiced = (scene.get("practiced_word") or "").strip()

    if category == "class":
        first_line = poem_text.split(".")[0].strip() or "동시"
        narration = (
            f"{subject} 국어책을 펴고 동시를 읽었어요. "
            f"「{first_line}」 하고 또박또박 읽었지요."
        )
        if practiced:
            narration += f" '{practiced}' 소리를 천천히 다시 읽어 보니 훨씬 또렷해졌어요."
        quote = poem_text or None
    else:
        narration = f"{subject} 가만히 귀를 기울였어요. 「{partner_line}」 하는 말이 들렸지요."
        if child_said:
            narration += f" {subject} 용기를 내어 「{child_said}」 하고 대답했어요."
        else:
            narration += f" {subject} 마음속으로 인사를 연습했어요."
        if practiced:
            narration += f" '{practiced}'도 한 번 더 또박또박 말해 보았답니다."
        quote = child_said

    return {
        "category": category,
        "subtitle": template["subtitle"],
        "opening": template["opening"],
        "quote": quote,
        "narration": narration,
    }
