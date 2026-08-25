import io
import os
import wave

import pytest

# 이 테스트들은 **목 제공자의 계약**을 검증한다. 실제 모델을 부르는 것이 목적이 아니다.
#
# .env 에 PROVIDER=real 이 들어 있으면 그대로 실제 경로로 붙어버린다 — STT 테스트가
# 수백 MB 짜리 whisper 모델을 내려받기 시작하고, TTS·동화 테스트가 유료 API 를 실제로
# 호출한다. 환경변수는 .env 보다 우선하므로 여기서 못박는다.
# **app.main 을 import 하기 전에** 설정해야 한다 — settings 가 그때 만들어진다.
os.environ["PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def wav_bytes() -> bytes:
    return make_silence_wav()


def make_silence_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """길이 검사를 통과하는 최소한의 진짜 WAV.

    빈 바이트를 올리면 "파일이 비었다"(400)로 먼저 걸려 그 뒤 로직을 못 본다.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * int(sample_rate * duration_sec))
    return buffer.getvalue()


def data_of(response) -> dict:
    """성공 봉투를 벗겨 ``data`` 만 돌려준다.

    테스트마다 `body["data"]` 를 쓰면 봉투가 빠졌을 때 KeyError 로만 드러난다.
    여기서 `success` 까지 함께 확인해 "봉투가 없다"를 곧바로 짚는다.
    """
    body = response.json()
    assert body.get("success") is True, body
    return body["data"]
