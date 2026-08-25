import math

from faster_whisper import WhisperModel

from app.providers.base import TranscriptionResult


def load_whisper_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(model: WhisperModel, audio_path: str, language_code: str) -> TranscriptionResult:
    segments, info = model.transcribe(
        audio_path,
        language=language_code,
        word_timestamps=True,
    )
    segments = list(segments)
    text = "".join(seg.text for seg in segments).strip()

    return {
        # 아이가 우물거려 아무것도 안 잡히면 빈 문자열이 아니라 None 이다.
        # 앱은 이 둘을 다르게 다룬다 — None 은 "못 알아들었다"(정상 진행),
        # 빈 문자열은 "빈 말을 했다"로 읽혀 화면이 어색해진다(연동 규약 §5).
        "text": text or None,
        "confidence": _confidence(segments),
        "language": info.language,
        "duration_sec": info.duration,
        "segments": [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "words": [
                    {"word": w.word.strip(), "start": w.start, "end": w.end}
                    for w in (seg.words or [])
                ],
            }
            for seg in segments
        ],
    }


def _confidence(segments: list) -> float | None:
    """세그먼트 평균 로그확률을 0~1 로 되돌린다.

    화면에는 절대 띄우지 않는 값이다(명세 §3 — 아이에게 점수를 보여주지 않는다).
    로그·품질 점검용으로만 쓴다.
    """
    scores = [seg.avg_logprob for seg in segments if seg.avg_logprob is not None]
    if not scores:
        return None
    return round(math.exp(sum(scores) / len(scores)), 3)
