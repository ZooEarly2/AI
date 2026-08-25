from tests.conftest import data_of


def test_chat_without_optional_native_language_part(client, wav_bytes):
    """nativeLanguage 는 선택이라 파트 자체가 오지 않는다 (연동 규약 §2-②)."""
    response = client.post(
        "/internal/v1/chat",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"scenario": "LUNCH", "history": "[]", "nickname": "민수"},
    )
    assert response.status_code == 200
    data = data_of(response)
    assert data["replyText"]
    assert data["userText"] == "안녕 나도 반가워"
    assert data["audio"]["data"]


def test_chat_carries_history_forward(client, wav_bytes):
    response = client.post(
        "/internal/v1/chat",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={
            "scenario": "ARRIVAL",
            # history 는 파싱된 배열이 아니라 JSON "문자열"로 온다
            "history": '[{"role":"assistant","content":"안녕!"}]',
            "nickname": "지우",
            "nativeLanguage": "VIETNAMESE",
        },
    )
    history = data_of(response)["history"]
    assert [turn["role"] for turn in history] == ["assistant", "user", "assistant"]


def test_chat_rejects_unknown_scenario(client, wav_bytes):
    response = client.post(
        "/internal/v1/chat",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"scenario": "RECESS", "history": "[]", "nickname": "지우"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "scenario"
