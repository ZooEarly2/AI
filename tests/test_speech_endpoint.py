"""STT / TTS.

게이트웨이가 실제로 보내는 형태로 붙는지를 본다 — 파트 이름은 `audio`/`language`,
`language` 는 BCP-47 자유 문자열이고 **생략되면 파트 자체가 오지 않는다**.
"""

import base64

from tests.conftest import data_of, make_silence_wav


def test_transcribe_with_gateway_part_names(client, wav_bytes):
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"language": "ko-KR"},  # BCP-47. enum 이 아니다
    )
    assert response.status_code == 200
    data = data_of(response)
    assert data["text"]
    # 응답의 언어는 앱 계약 enum 으로 올려 보낸다 (ko 가 아니라 KOREAN)
    assert data["language"] == "KOREAN"
    assert "durationSec" in data and "segments" in data


def test_transcribe_without_language_part(client, wav_bytes):
    """게이트웨이는 선택 필드를 빈 값이 아니라 파트째로 뺀다 (연동 규약 §2-②).

    여기서 가장 많이 터진다 — Form(...) 로 필수 선언하면 이 요청이 통째로 422 다.
    """
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
    )
    assert response.status_code == 200
    assert data_of(response)["language"] == "KOREAN"


def test_transcribe_still_accepts_legacy_part_names(client, wav_bytes):
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio_file": ("sample.wav", wav_bytes, "audio/wav")},
        data={"language_code": "ko"},
    )
    assert response.status_code == 200


def test_transcribe_unknown_language_falls_back_to_korean(client, wav_bytes):
    """모르는 언어 코드로 녹음을 통째로 버리지 않는다.

    아이가 말을 마친 뒤 언어 코드 때문에 실패시키는 것이 이 앱에서 가장 나쁜 실패다.
    """
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"language": "fr-FR"},
    )
    assert response.status_code == 200
    assert data_of(response)["language"] == "KOREAN"


def test_transcribe_audio_too_long(client):
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio": ("speech.wav", make_silence_wav(duration_sec=35), "audio/wav")},
        data={"language": "ko-KR"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["field"] == "audio"


def test_transcribe_empty_audio(client):
    response = client.post(
        "/internal/v1/speech/transcribe",
        files={"audio": ("speech.m4a", b"", "audio/mp4")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


def test_synthesize_returns_base64_json_not_binary(client):
    """바이너리로 내면 게이트웨이(body 를 String 으로 받는다)에서 깨진다."""
    response = client.post(
        "/internal/v1/speech/synthesize",
        json={"text": "안녕! 나도 만나서 반가워!", "language": "KOREAN", "voice": "TEACHER"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = data_of(response)
    audio = data["audio"]
    assert audio["format"] in ("mp3", "wav")
    # 실제로 디코딩되는 base64 여야 한다 — 앱이 data: URL 로 그대로 재생한다
    assert len(base64.b64decode(audio["data"])) > 0
    # 목이 만든 소리라는 표시. 앱이 브라우저 TTS 로 대신 읽어줄지 판단한다.
    assert data["mock"] is True


def test_synthesize_accepts_legacy_language_code(client):
    response = client.post(
        "/internal/v1/speech/synthesize",
        json={"text": "안녕!", "language_code": "ko"},
    )
    assert response.status_code == 200


def test_synthesize_empty_text(client):
    response = client.post(
        "/internal/v1/speech/synthesize",
        json={"text": "   ", "language": "KOREAN"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "text"


def test_synthesize_unsupported_language(client):
    response = client.post(
        "/internal/v1/speech/synthesize",
        json={"text": "hello", "language": "FRENCH"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "language"
