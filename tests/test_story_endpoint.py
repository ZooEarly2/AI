"""동화 생성.

게이트웨이는 앱이 보낸 body 를 **가공 없이** 통과시킨다. 그래서 여기 도착하는 필드명은
앱 계약대로 camelCase 다 — 2026-08-24 실측에서 snake_case 만 받아 422 였던 지점이다.
"""

import copy

from tests.conftest import data_of

VALID_BODY = {
    "childName": "지우",
    "scenes": [
        {
            "category": "school_arrival",
            "partnerLine": "안녕! 오늘도 만나서 반가워",
            "childSaid": "안녕 나도 만나서 반가워 !",
        },
        {
            "category": "class",
            "poemText": "노란 꽃이 피었어요. 예쁜 꽃이 피었어요. 바람이 살랑살랑 꽃이 웃어요.",
            "practicedWord": "살랑살랑",
        },
        {"category": "lunch", "partnerLine": "오늘 반찬 맛있게 먹어요", "childSaid": None},
        {
            "category": "school_departure",
            "partnerLine": "오늘도 수고했어, 내일 봐",
            "childSaid": "선생님, 안녕히 가세요!",
        },
    ],
}


def test_story_accepts_camel_case_body(client):
    response = client.post("/internal/v1/story/generate", json=VALID_BODY)
    assert response.status_code == 200
    data = data_of(response)
    assert data["title"]
    assert [scene["category"] for scene in data["scenes"]] == [
        "school_arrival",
        "class",
        "lunch",
        "school_departure",
    ]
    assert {"subtitle", "opening", "quote", "narration"} <= data["scenes"][0].keys()


def test_story_quotes_only_what_the_child_actually_said(client):
    """아이가 고르지 않고 넘어간 장면의 quote 는 null 이다.

    지어낸 대사가 동화에 실리면 하루를 되돌아보는 기록으로서의 뜻이 사라진다.
    """
    data = data_of(client.post("/internal/v1/story/generate", json=VALID_BODY))
    quotes = {scene["category"]: scene["quote"] for scene in data["scenes"]}
    assert quotes["lunch"] is None
    assert quotes["school_arrival"] == "안녕 나도 만나서 반가워 !"


def test_story_uses_practiced_word_in_narration(client):
    data = data_of(client.post("/internal/v1/story/generate", json=VALID_BODY))
    class_scene = next(s for s in data["scenes"] if s["category"] == "class")
    assert "살랑살랑" in class_scene["narration"]


def test_story_accepts_legacy_snake_case_body(client):
    body = {
        "child_name": "지우",
        "scenes": [
            {
                "category": "school_arrival",
                "partner_line": "안녕! 오늘도 만나서 반가워",
                "child_said": "안녕!",
            },
            {"category": "class", "poem_text": "노란 꽃이 피었어요.", "practiced_word": "노란"},
            {"category": "lunch", "partner_line": "맛있게 먹어요"},
            {"category": "school_departure", "partner_line": "내일 봐"},
        ],
    }
    assert client.post("/internal/v1/story/generate", json=body).status_code == 200


def test_story_rejects_wrong_scene_order(client):
    body = copy.deepcopy(VALID_BODY)
    body["scenes"][0], body["scenes"][1] = body["scenes"][1], body["scenes"][0]
    response = client.post("/internal/v1/story/generate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "scenes[0].category"


def test_story_rejects_missing_partner_line(client):
    body = copy.deepcopy(VALID_BODY)
    body["scenes"][2]["partnerLine"] = "   "
    response = client.post("/internal/v1/story/generate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "scenes[2].partnerLine"


def test_story_rejects_wrong_scene_count(client):
    body = copy.deepcopy(VALID_BODY)
    body["scenes"] = body["scenes"][:3]
    response = client.post("/internal/v1/story/generate", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "scenes"
