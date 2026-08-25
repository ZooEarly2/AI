"""목(mock) 제공자용 재생 가능한 소리.

목 응답으로 ``b"MOCK_AUDIO_BYTES"`` 를 주면 앱에서 재생이 실패해, 화면이 잘못된 건지
음성이 없는 건지 구분이 안 된다. 실제로 들리는 짧은 차임을 만들어 주면 "TTS 왕복이
성공했다"를 귀로 확인할 수 있다.

mp3 인코더는 표준 라이브러리에 없으므로 WAV 로 만든다. 응답의 ``format`` 이 ``wav``
라 앱은 ``data:audio/wav;base64,...`` 로 그대로 재생한다.
"""

from __future__ import annotations

import io
import math
import struct
import wave

SAMPLE_RATE = 22050


def chime_wav(text: str = "") -> bytes:
    """텍스트 길이에 따라 음이 하나 늘어나는 부드러운 차임.

    문장이 길면 조금 더 길게 울려, 어떤 문장을 읽었는지가 어렴풋이 구분된다.
    """
    notes = [523.25, 659.25, 783.99]  # 도-미-솔
    if len(text) > 12:
        notes.append(1046.50)
    note_sec = 0.18

    frames = bytearray()
    for index, freq in enumerate(notes):
        count = int(SAMPLE_RATE * note_sec)
        for i in range(count):
            t = i / SAMPLE_RATE
            # 어린이용이라 날카롭지 않게 — 사인파에 부드러운 감쇠 포락선을 씌운다
            envelope = math.sin(math.pi * i / count) ** 1.5
            value = 0.28 * envelope * math.sin(2 * math.pi * freq * t)
            # 배음을 아주 조금 섞어 종소리에 가깝게
            value += 0.06 * envelope * math.sin(4 * math.pi * freq * t)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))
        if index < len(notes) - 1:
            frames += b"\x00\x00" * int(SAMPLE_RATE * 0.02)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(frames))
    return buffer.getvalue()
