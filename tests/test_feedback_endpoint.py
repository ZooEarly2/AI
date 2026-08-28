"""발음 채점 · 문장 목록 · 표현 교정.

여기 테스트가 지키는 것은 두 가지다.
1. 응답이 `{success, data}` + camelCase 인가 — 게이트웨이가 body 를 가공하지 않으므로
   이게 곧 앱이 받는 JSON 이다.
2. 게이트웨이가 실제로 보내는 파트 이름(`audio`, `sentenceId`)으로 붙는가 —
   2026-08-24 실측에서 여기가 전부 422 였다.
"""

from app.core.sentences import SENTENCES
from tests.conftest import data_of


def test_list_sentences_is_enveloped_and_camel_case(client):
    response = client.get("/internal/v1/feedback/sentences")
    assert response.status_code == 200
    data = data_of(response)
    # 개수를 숫자로 못박지 않는다 — 문장이 늘 때마다 여기가 같이 깨지는데, 그건
    # 목록이 봉투에 담겨 camelCase 로 나가는지와 아무 상관이 없다. 대신 카탈로그와
    # 같은 것을 주는지를 본다(둘이 어긋나는 것이 진짜 사고다).
    assert len(data) == len(SENTENCES)
    assert {item["sentenceId"] for item in data} == {sid.value for sid in SENTENCES}
    assert {"sentenceId", "category", "text", "translations"} <= data[0].keys()
    assert {item["category"] for item in data} == {
        "arrival",
        "lunch",
        "departure",
        "study",
        "math",
    }


def test_every_sentence_carries_mother_tongue_translations(client):
    """열 문장 모두 베트남어·중국어 뜻을 달고 나가야 한다.

    앱의 힌트 전구가 이 값 하나만 본다. 번역을 부르는 요청이 따로 없으므로,
    여기서 비면 아이가 전구를 눌러도 **아무 일도 일어나지 않는다** — 화면에는
    오류도 안 뜨고 버튼만 먹통이라 아이도 어른도 무엇이 잘못됐는지 모른다.
    문장을 새로 추가할 때 번역을 빠뜨리는 것이 유일하게 있을 법한 사고라
    목록 전체를 훑는다.
    """
    data = data_of(client.get("/internal/v1/feedback/sentences"))
    for item in data:
        assert item["translations"].get("vi"), item["sentenceId"]
        assert item["translations"].get("zh"), item["sentenceId"]


def test_translation_parts_point_at_real_tokens(client):
    """빈칸 자리를 짚어주는 대응표가 실제 어절을 가리키는가.

    조각을 이으면 번역문과 같은지는 `sentences.py` 가 수입 시점에 검산한다.
    여기서 보는 것은 **앱이 받는 모양**이다 — camelCase 로 나가는지, k 가 그 문장의
    어절 범위 안인지. k 가 범위를 넘으면 앱은 아무것도 짚지 못하고 조용히 넘어가서,
    전구를 눌러도 빈칸이 어디인지 안 보이는 상태가 된다.

    빈칸 퀴즈를 내는 카테고리에만 대응표가 있다. 동시(study)와 수학(math)에는 없다 —
    시는 통째로 읽고, 수학은 고른 문장을 그대로 읽는다. 둘 다 비울 어절이 없다.
    """
    data = data_of(client.get("/internal/v1/feedback/sentences"))
    checked = 0
    for item in data:
        parts = item["translationParts"]
        if item["category"] in {"study", "math"}:
            assert parts == {}, item["sentenceId"]
            continue
        assert set(parts) == {"vi", "zh"}, item["sentenceId"]
        last = len(item["text"].split()) - 1
        for lang, chunks in parts.items():
            covered = {k for chunk in chunks for k in chunk["k"]}
            assert covered <= set(range(last + 1)), f'{item["sentenceId"]}/{lang}'
            assert covered, f'{item["sentenceId"]}/{lang} 은 아무 어절도 안 가리킨다'
            checked += 1
    assert checked == 36, checked  # 18문장 x 2언어


def test_math_sentences_are_scorable(client, wav_bytes):
    """수학 문장 15개가 실제로 채점을 통과하는가.

    수업시간의 수학 차례는 아이가 개수를 고른 뒤 그 문장을 소리 내어 읽는다.
    예전에는 이 문장이 목록에 없어서 채점 자체가 불가능했고, 그래서 앱이
    ``/stt`` 로 받아쓴 글자에서 숫자만 뽑아 맞춰 보는 우회로를 썼다 —
    "다섯" 한 마디만 해도 문장을 다 읽은 것으로 쳤다.

    id 를 앱이 만들어 보내므로(과일과 개수로 고른다) **15개가 하나도 빠짐없이**
    살아 있어야 한다. 하나만 없어도 그 과일·그 개수가 나온 아이만 채점을 못 받는데,
    회차마다 무작위라 재현이 어렵다.
    """
    ids = [sid for sid in SENTENCES if sid.value.startswith("math_")]
    assert len(ids) == 15, len(ids)  # 과일 3종 x 개수 1~5

    for sid in ids:
        response = client.post(
            "/internal/v1/feedback/speaking",
            files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
            data={"sentenceId": sid.value},
        )
        assert response.status_code == 200, (sid.value, response.text)
        assert data_of(response)["sentence"] == SENTENCES[sid]


def test_unknown_sentence_id_is_invalid_parameter_not_off_script(client, wav_bytes):
    """목록에 없는 id 는 OFF_SCRIPT 가 아니라 INVALID_PARAMETER 다.

    둘 다 422 라 앱이 상태 코드만 보면 구분하지 못한다. 그런데 뜻이 정반대다 —
    OFF_SCRIPT 는 "다시 말하면 되는 일"이고, INVALID_PARAMETER 는 아이가 아무리
    잘 읽어도 통과할 수 없는 일이다. 앱이 뒤쪽을 "다시 말해볼래?" 로 다루면
    아이는 영영 못 나가는 화면에 갇힌다.

    서버가 아직 이 문장을 모를 때 앱이 옛 방식으로 물러설 수 있어야 해서,
    코드로 갈리는 것이 계약의 일부다.
    """
    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "math_99"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


def test_off_script_has_its_own_error_code(client, wav_bytes, monkeypatch):
    """전혀 다른 말을 했을 때는 INVALID_PARAMETER 가 아니라 OFF_SCRIPT 다.

    두 코드가 같으면 앱이 구분을 못 한다. 실제로 그랬다 — 앱은 채점이 실패한
    모든 경우를 칭찬 화면으로 흘려보내서, 아이가 문장과 전혀 다른 말을 해도
    "잘했어!" 가 떴다. 서버는 off_script 로 알고 있었고 앱이 그 신호를 버렸다.

    상태 코드가 422 인 것도 함께 지킨다. 게이트웨이는 422 만 본문째 통과시키므로
    (연동 규약 §1.3) 여기서 코드가 바뀌면 이 구분이 앱까지 닿지 못한다.
    """
    from app.providers.mock import MockProvider

    def off_script(self, audio_path: str, text: str):
        return {"sentence": text, "off_script": True, "words": []}

    monkeypatch.setattr(MockProvider, "score_pronunciation", off_script)

    response = client.post(
        "/internal/v1/feedback/speaking",
        files={"audio": ("speech.m4a", wav_bytes, "audio/mp4")},
        data={"sentenceId": "arrival_2"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "OFF_SCRIPT"


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
