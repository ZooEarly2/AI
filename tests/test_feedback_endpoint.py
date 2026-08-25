"""발음 채점 · 문장 목록 · 표현 교정.

여기 테스트가 지키는 것은 두 가지다.
1. 응답이 `{success, data}` + camelCase 인가 — 게이트웨이가 body 를 가공하지 않으므로
   이게 곧 앱이 받는 JSON 이다.
2. 게이트웨이가 실제로 보내는 파트 이름(`audio`, `sentenceId`)으로 붙는가 —
   2026-08-24 실측에서 여기가 전부 422 였다.
"""

from tests.conftest import data_of


def test_list_sentences_is_enveloped_and_camel_case(client):
    response = client.get("/internal/v1/feedback/sentences")
    assert response.status_code == 200
    data = data_of(response)
    assert len(data) == 10
    assert {"sentenceId", "category", "text"} <= data[0].keys()
    assert {item["category"] for item in data} == {"arrival", "lunch", "departure", "study"}


def test_speaking_accepts_gateway_part_names(client, wav_bytes):
    """게이트웨이는 `audio` / `sentenceId` 로 보낸다 (연동 규약 §3)."""
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "arrival_2"},
    )
    assert response.status_code == 200
    data = data_of(response)
    # MockProvider 는 어절이 뒤로 갈수록 z 를 -0.6씩 낮춘다(0, -0.6, -1.2, -1.8).
    # "안녕! 우리 같이 놀자!" 는 4어절이라 마지막(z=-1.8)만 -1.5 미만이다.
    assert data["sentenceId"] == "arrival_2"
    assert data["sentence"] == "안녕! 우리 같이 놀자!"
    assert data["targetWord"] == "놀자!"
    assert data["targetIndex"] == 3
    assert data["targetZ"] == -1.8
    assert len(data["words"]) == 4
    assert {"word", "z", "warn", "worstPhone"} <= data["words"][0].keys()


def test_speaking_still_accepts_legacy_part_names(client, wav_bytes):
    """초기 명세의 `audio_file` / `sentence_id` 로 부르던 호출도 살려둔다."""
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio_file": ("sample.wav", wav_bytes, "audio/wav")},
        data={"sentence_id": "arrival_2"},
    )
    assert response.status_code == 200
    assert data_of(response)["targetWord"] == "놀자!"


def test_speaking_study_poem(client, wav_bytes):
    """수업시간 시 읽기도 같은 경로를 그대로 쓴다 — 별도 낭독 엔드포인트가 없다."""
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "study_1"},
    )
    data = data_of(response)
    assert len(data["words"]) == 10
    assert data["targetWord"] == "웃어요."
    assert data["targetIndex"] == 9


def test_speaking_no_weak_word_is_success_not_error(client, wav_bytes):
    """전부 잘 발음했으면 targetWord 가 null 이다. 에러가 아니다."""
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "lunch_1"},  # "조금만 주세요." 2어절 → z 0, -0.6
    )
    assert response.status_code == 200
    data = data_of(response)
    assert data["targetWord"] is None
    assert data["targetIndex"] is None
    assert data["targetZ"] is None


def test_speaking_unknown_sentence_id_uses_error_envelope(client, wav_bytes):
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "not_a_real_id"},
    )
    # 422 는 게이트웨이가 body 를 그대로 앱까지 통과시키는 두 상태 중 하나다.
    # FastAPI 기본 형식({"detail": ...})으로 나가면 앱이 못 읽는다.
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_PARAMETER"
    assert body["error"]["field"] == "sentenceId"


def test_speaking_empty_audio(client):
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", b"", "audio/mp4")},
        data={"sentenceId": "departure_1"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


def test_expression_feedback_includes_translation(client):
    response = client.post(
        "/internal/v1/feedback/expression",
        json={
            "targetSentence": "조금만 주세요.",
            "recognizedText": "조금만 주세여",
            "scenario": "LUNCH",
            "nativeLanguage": "VIETNAMESE",
            "nickname": "민수",
        },
    )
    assert response.status_code == 200
    data = data_of(response)
    assert data["naturalSentence"] == "조금만 주세요."
    # 번역을 이 응답에 합쳐 내려보낸다 — 앱이 /translate 를 따로 부르지 않게 하려는 것이다.
    assert data["translation"] == "Cho con một chút thôi ạ."
    assert data["translationLanguage"] == "VIETNAMESE"
    # 아이가 말하지 않은 어절만 짚는다. "조금만"은 말했으므로 빠진다.
    assert data["highlightWords"] == ["주세요."]


def test_expression_feedback_without_native_language_has_no_translation(client):
    response = client.post(
        "/internal/v1/feedback/expression",
        json={
            "targetSentence": "많이 주세요.",
            "recognizedText": None,
            "nickname": "지우",
        },
    )
    data = data_of(response)
    assert data["translation"] is None
    # 아무 말도 못 알아들었으면 짚을 근거가 없다 — 문장 전체를 칠하지 않는다.
    assert data["highlightWords"] == []
