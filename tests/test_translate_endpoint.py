from tests.conftest import data_of


def test_translate_success(client):
    response = client.post(
        "/internal/v1/text/translate",
        json={
            "text": "안녕 나도 만나서 반가워 !",
            "sourceLanguage": "KOREAN",
            "targetLanguage": "VIETNAMESE",
        },
    )
    assert response.status_code == 200
    data = data_of(response)
    # 필드명이 translated_text 가 아니라 translation 이다 — 앱이 읽는 이름
    assert data["translation"] == "Chào cậu! Mình cũng rất vui được gặp cậu!"
    assert data["targetLanguage"] == "VIETNAMESE"


def test_translate_accepts_legacy_snake_case_and_short_codes(client):
    response = client.post(
        "/internal/v1/text/translate",
        json={"text": "많이 주세요.", "source_language": "ko", "target_language": "zh"},
    )
    data = data_of(response)
    assert data["translation"] == "请给我多一点。"
    assert data["targetLanguage"] == "CHINESE"


def test_translate_empty_text(client):
    response = client.post(
        "/internal/v1/text/translate",
        json={"text": "   ", "targetLanguage": "VIETNAMESE"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "text"


def test_translate_unsupported_target_language(client):
    response = client.post(
        "/internal/v1/text/translate",
        json={"text": "안녕!", "targetLanguage": "FRENCH"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "targetLanguage"
