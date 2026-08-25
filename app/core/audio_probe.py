"""업로드된 오디오의 길이를 잰다.

faster-whisper 가 깔려 있으면 그 디코더(PyAV)로 재는데, 이유가 있다: 실제 STT 가
쓰는 것과 **같은 디코더**로 재야 m4a/webm 포맷 차이로 인한 오탐이 없다. 확장자만
보고 판정하면 컨테이너와 실제 코덱이 다른 파일에서 틀린다.

PROVIDER=mock 으로 도는 로컬·CI 에는 faster-whisper 가 없다. 그때는 표준 wave 모듈로
WAV 만 재고, 나머지 포맷은 "잴 수 없음"(None)으로 둔다 — 길이 제한을 못 지키는 것이
아니라, 목 모드에서 길이 검사만 건너뛰는 것이다. 용량 상한(게이트웨이 10MB)은 그대로다.
"""

from __future__ import annotations

import contextlib
import wave

_DECODE_SAMPLE_RATE = 16000  # faster_whisper.audio.decode_audio() 의 리샘플링 레이트


class UndecodableAudio(Exception):
    """오디오로 열 수 없는 파일. 잘못된 업로드다."""


def probe_duration_sec(path: str) -> float | None:
    """길이(초). 잴 수 없으면 ``None``.

    파일이 오디오가 아니면 :class:`UndecodableAudio` 를 던진다 — 길이를 모르는 것과
    파일이 깨진 것은 다르게 다뤄야 한다.
    """
    try:
        from faster_whisper.audio import decode_audio
    except ImportError:
        return _wav_duration(path)

    try:
        samples = decode_audio(path)
    except Exception as exc:  # PyAV 는 포맷별로 다른 예외를 던진다
        raise UndecodableAudio(str(exc)) from exc
    return len(samples) / _DECODE_SAMPLE_RATE


def _wav_duration(path: str) -> float | None:
    with contextlib.suppress(Exception):
        with wave.open(path, "rb") as wav_file:
            rate = wav_file.getframerate()
            if rate:
                return wav_file.getnframes() / rate
    return None
