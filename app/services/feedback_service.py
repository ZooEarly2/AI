"""발음 채점 · 표현 교정."""

from __future__ import annotations

import os

from fastapi import UploadFile

from app.core.audio_storage import save_temp_audio
from app.core.config import settings
from app.core.exceptions import InvalidRequest, OffScript, UpstreamUnavailable
from app.core.languages import to_code, to_enum
from app.core.logging import get_logger
from app.core.sentences import SENTENCES, SentenceId
from app.providers.base import InferenceProvider, PronunciationScoreResult, WordScoreDict
from app.providers.clients.scoring_client import ScoringServiceBadRequest, ScoringServiceUnavailable
from app.schemas.feedback import (
    ExpressionFeedbackData,
    ExpressionFeedbackRequest,
    SpeakingFeedbackData,
)

log = get_logger(__name__)

# 어절 z-score 가 이 값보다 낮아야 "발음이 부족하다"고 본다.
# -1.5 이상이면 발음이 좋은 것으로 보고 피드백 퀴즈를 띄우지 않는다.
_Z_WEAK_THRESHOLD = -1.5


def _pick_weakest_word(words: list[WordScoreDict]) -> tuple[int, WordScoreDict] | None:
    """z < 임계값인 어절 중 가장 낮은 것 1개. 해당하는 어절이 없으면 ``None``.

    warn 이 여러 개 켜져도 하나만 고른다 — 화면의 빈칸이 하나뿐이고, 아이에게 한 번에
    여러 개를 짚어주면 무엇을 고쳐야 할지 알 수 없다.
    """
    weak = [(i, w) for i, w in enumerate(words) if w["z"] is not None and w["z"] < _Z_WEAK_THRESHOLD]
    if not weak:
        return None
    return min(weak, key=lambda iw: iw[1]["z"])


def score_speaking(
    provider: InferenceProvider, audio_file: UploadFile, sentence_id: SentenceId
) -> SpeakingFeedbackData:
    text = SENTENCES[sentence_id]

    with save_temp_audio(audio_file) as audio_path:
        raw_size_mb = os.path.getsize(audio_path) / 1e6
        if raw_size_mb == 0:
            raise InvalidRequest("녹음 파일이 비어 있습니다.", field="audio")
        if raw_size_mb > settings.scoring_max_upload_mb:
            raise InvalidRequest(
                f"오디오 파일이 너무 큽니다: {raw_size_mb:.1f}MB > "
                f"{settings.scoring_max_upload_mb}MB",
                field="audio",
            )

        try:
            result: PronunciationScoreResult = provider.score_pronunciation(audio_path, text)
        except ScoringServiceUnavailable as exc:
            log.warning("채점 서비스 연결 실패 (%s): %s", type(exc.__cause__).__name__, exc)
            raise UpstreamUnavailable("발음 채점 서비스에 연결할 수 없습니다.") from exc
        except ScoringServiceBadRequest as exc:
            raise InvalidRequest(exc.message, field="audio") from exc

    if result["off_script"]:
        # 다시 말하면 되는 일이라 INVALID_PARAMETER 와 갈라 둔다 — 앱이 이 코드를
        # 보고 녹음 화면으로 되돌린다. 예전에는 둘이 같은 코드라, 앱이 구분하지
        # 못하고 전혀 다른 말을 한 아이에게도 칭찬을 띄웠다.
        raise OffScript("읽은 음성이 고른 문장과 다릅니다.", field="audio")

    if not any(w["z"] is not None for w in result["words"]):
        raise InvalidRequest("발음을 채점할 수 있는 어절이 없습니다.", field="audio")

    sentence, words = _to_spelling(text, result)

    weakest = _pick_weakest_word(words)
    if weakest is None:
        # 모든 어절이 기준을 넘겼다 — 퀴즈 없이 칭찬 화면으로 간다. 에러가 아니다.
        return SpeakingFeedbackData(
            sentence_id=sentence_id,
            sentence=sentence,
            target_word=None,
            target_index=None,
            target_z=None,
            words=words,
        )

    target_index, target = weakest
    return SpeakingFeedbackData(
        sentence_id=sentence_id,
        sentence=sentence,
        target_word=target["word"],
        target_index=target_index,
        target_z=target["z"],
        words=words,
    )


def _to_spelling(
    canonical: str, result: PronunciationScoreResult
) -> tuple[str, list[WordScoreDict]]:
    """채점 결과의 어절을 **맞춤법 표기**로 되돌린다.

    채점 서비스는 소리 나는 대로 적은 어절을 돌려준다 — "같이" 를 "가치" 로.
    채점에는 그게 맞지만 화면에 그대로 내보내면 안 된다. 빈칸 퀴즈의 정답이
    "가치" 로 뜨면, 글자를 배우는 중인 아이에게 틀린 철자를 가르치는 셈이다.

    어절 수가 같을 때만 바꿔 끼운다. 다르면 자리가 어긋나 엉뚱한 낱말을 짚게 되므로
    채점 서비스가 준 것을 그대로 쓴다 — 표기가 아쉬운 편이 자리가 틀린 것보다 낫다.
    """
    tokens = canonical.split()
    words = result["words"]
    if len(tokens) != len(words):
        log.info(
            "어절 수가 달라 채점 표기를 그대로 쓴다 (문장 %d / 채점 %d)", len(tokens), len(words)
        )
        return result["sentence"], words

    # 아이가 화면에서 본 문장 그대로 돌려준다 — 문장부호까지 같아야 같은 문장으로 읽힌다
    return canonical, [{**word, "word": tokens[i]} for i, word in enumerate(words)]


def expression_feedback(
    provider: InferenceProvider, request: ExpressionFeedbackRequest
) -> ExpressionFeedbackData:
    """표현 교정 + 모국어 번역.

    번역을 여기 합쳐 내려보낸다 — 앱이 ``/translate`` 를 따로 부르면 같은 화면을
    두 번 기다리게 된다(연동 규약 §1-1).
    """
    target = request.target_sentence.strip()
    if not target:
        raise InvalidRequest("권장 문장이 비어 있습니다.", field="targetSentence")
    nickname = (request.nickname or "").strip()
    if not nickname:
        raise InvalidRequest("아이 호칭이 필요합니다.", field="nickname")

    try:
        feedback = provider.expression_feedback(
            target_sentence=target,
            recognized_text=request.recognized_text,
            scenario=request.scenario,
            nickname=nickname,
        )
    except Exception as exc:
        log.warning("표현 교정 실패: %s", exc)
        raise UpstreamUnavailable("피드백 서비스에 연결할 수 없습니다.") from exc

    translation, translation_language = _translate_for(provider, feedback["natural_sentence"], request.native_language)

    return ExpressionFeedbackData(
        reaction=feedback["reaction"],
        comment=feedback["comment"],
        natural_sentence=feedback["natural_sentence"],
        natural_hint=feedback["natural_hint"],
        highlight_words=feedback["highlight_words"],
        translation=translation,
        translation_language=translation_language,
    )


def _translate_for(
    provider: InferenceProvider, sentence: str, native_language: str | None
) -> tuple[str | None, str | None]:
    """모국어 번역. 모국어가 없거나 한국어면 번역하지 않는다.

    번역이 실패해도 피드백 전체를 실패시키지 않는다 — "이 말의 뜻이에요" 칸만 비고,
    아이는 그대로 따라 말하기로 넘어갈 수 있다.
    """
    target = to_code(native_language, default=None)
    if target is None or target == "ko":
        return None, None
    try:
        return provider.translate(sentence, "ko", target), to_enum(target)
    except Exception as exc:
        log.info("번역 생략(실패): %s", exc)
        return None, None
