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


def test_partner_is_named_not_called_a_stranger(client):
    """말을 건 사람을 이름으로 부른다. "다른 사람" 으로 뭉뚱그리면 안 된다.

    프롬프트가 "기록에 없는 인물을 만들지 마라" 라고 못박아 두어서, 누가 말했는지를
    안 알려주면 LLM 은 뭉뚱그리는 수밖에 없다. 실제로 동화에 "급식 시간에 다른
    사람이 「불고기 많이 줄까?」라고 말했어요" 로 나갔다 — 아이가 오늘 만난 사람은
    급식 선생님이었는데.

    조사도 같이 본다. 받침에 따라 "급식 선생님이" 와 "호랑이 친구가" 로 갈린다.
    """
    body = copy.deepcopy(VALID_BODY)
    body["scenes"][2] = {
        "category": "lunch",
        "partnerName": "급식 선생님",
        "partnerLine": "불고기 많이 줄까?",
        "childSaid": "적당히 주세요.",
    }
    body["scenes"][0] = {
        "category": "school_arrival",
        "partnerName": "호랑이 친구",
        "partnerLine": "안녕! 만나서 반가워.",
        "childSaid": "안녕 나도 만나서 반가워 !",
    }
    response = client.post("/internal/v1/story/generate", json=body)
    assert response.status_code == 200
    scenes = {s["category"]: s["narration"] for s in data_of(response)["scenes"]}

    assert "다른 사람" not in scenes["lunch"], scenes["lunch"]
    assert "급식 선생님이" in scenes["lunch"], scenes["lunch"]
    # 받침이 없으면 "가" 다. "호랑이 친구이" 로 나가면 안 된다.
    assert "호랑이 친구가" in scenes["school_arrival"], scenes["school_arrival"]
    assert "호랑이 친구이" not in scenes["school_arrival"], scenes["school_arrival"]


def test_scene_without_partner_name_invents_nobody(client):
    """이름을 안 보내면 사람을 지어내지 않고 들린 말만 적는다.

    이미 배포된 앱은 partnerName 을 모른다. 그 앱들이 만드는 동화가 갑자기
    엉뚱한 인물을 데려오면 안 된다.
    """
    response = client.post("/internal/v1/story/generate", json=VALID_BODY)
    assert response.status_code == 200
    for scene in data_of(response)["scenes"]:
        assert "급식 선생님" not in scene["narration"], scene["narration"]


def test_math_scene_is_not_told_as_a_poem(client):
    """수학을 한 날의 동화가 "동시를 읽었다" 고 하면 안 된다.

    수업시간은 국어(동시 읽기)와 수학(과일 세기) 둘이다. 그런데 둘 다 같은
    필드(poemText)로 오고, 그 필드는 이름부터 "동시" 다. classSubject 를 안 보면
    과일을 센 아이의 기록이 "아이가_읽은_동시" 로 LLM 에 넘어가고, 대체 문구는
    "동시를 또박또박 읽었어요" 가 된다 — 아이는 그날 시를 읽지 않았다.

    동화는 아이가 실제로 한 일만 적는다는 것이 이 기능의 전제라, 여기서 막는다.
    """
    body = copy.deepcopy(VALID_BODY)
    body["scenes"][1] = {
        "category": "class",
        "classSubject": "MATH",
        "poemText": "사과 세 개를 세었어요.",
    }
    response = client.post("/internal/v1/story/generate", json=body)
    assert response.status_code == 200
    scene = next(s for s in data_of(response)["scenes"] if s["category"] == "class")
    assert "동시" not in scene["narration"], scene["narration"]
    assert "국어" not in scene["narration"], scene["narration"]


def test_class_scene_without_subject_is_still_a_poem(client):
    """classSubject 를 안 보내면 국어로 본다.

    이미 배포된 앱은 이 필드를 모른다. 없다고 거절하거나 수학으로 넘겨 버리면,
    그 앱들이 만드는 동화가 통째로 어긋난다.
    """
    response = client.post("/internal/v1/story/generate", json=VALID_BODY)
    assert response.status_code == 200
    scene = next(s for s in data_of(response)["scenes"] if s["category"] == "class")
    assert "동시" in scene["narration"], scene["narration"]


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
