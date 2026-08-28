"""동화 장면이 **제공자가 만든 문장**으로 채워지는지 본다.

story_service 가 제공자에게 넘기는 dict 의 키 표기가 어긋나면(camelCase ↔ snake_case)
제공자는 상대 대사도 시도 낱말도 못 읽어 빈손으로 돌아오고, 서비스는 조용히 대체
문구("오늘의 한 장면")로 채운다. 200 이 그대로 나가서 눈으로는 안 잡힌다.
"""

from tests.conftest import data_of
from tests.test_story_endpoint import VALID_BODY


def test_scenes_use_provider_copy_not_the_fallback(client):
    data = data_of(client.post("/internal/v1/story/generate", json=VALID_BODY))
    subtitles = [scene["subtitle"] for scene in data["scenes"]]
    assert subtitles == ["반가운 아침 인사", "동시를 읽은 시간", "맛있는 점심시간", "다정한 하굣길"]
    assert all(scene["opening"] != "그때였어요" for scene in data["scenes"])


def test_narration_reads_the_partner_line(client):
    data = data_of(client.post("/internal/v1/story/generate", json=VALID_BODY))
    arrival = data["scenes"][0]["narration"]
    assert "안녕! 오늘도 만나서 반가워" in arrival
    assert "지우가" in arrival  # 받침 없는 이름 → "지우가"


def test_opening_always_ends_a_sentence(client):
    """여는 말은 반드시 끝맺어야 한다.

    화면이 ``{opening} {narration}`` 으로 한 줄에 이어 붙이므로, opening 이
    "급식실이에요" 처럼 부호 없이 끝나면 "급식실이에요 급식 선생님께서…" 가 되어
    두 문장이 한 문장처럼 읽힌다. 실제로 그렇게 나왔다.
    """
    from app.services.story_service import _closed

    assert _closed("급식실이에요") == "급식실이에요."
    assert _closed("해가 기울어요.") == "해가 기울어요."      # 이미 끝났으면 그대로
    assert _closed("정말?") == "정말?"
    assert _closed("와!") == "와!"
    assert _closed(' "다녀왔습니다."') == '"다녀왔습니다."'    # 따옴표 안쪽을 본다
    assert _closed("  ") == ""

    data = data_of(client.post("/internal/v1/story/generate", json=VALID_BODY))
    for scene in data["scenes"]:
        assert scene["opening"], "여는 말이 비면 안 된다"
        assert scene["opening"][-1] in '.!?…。！？~"\'”’」』', scene["opening"]


def test_japanese_particles_are_thrown_away():
    """가나가 섞인 문장은 통째로 버리고 기록으로 다시 쓴다.

    실제로 나왔다 — "「파도」を 읽었어요"(6번 중 2번). 한 글자라 눈으로는 잘 안
    잡히는데, 한국어를 배우는 아이가 읽는 글에 일본어 조사가 남으면 안 된다.
    """
    from app.schemas.story import SceneInput
    from app.services.story_service import _is_korean, _normalise_scenes

    assert _is_korean("「파도」를 읽었어요.")
    assert not _is_korean("「파도」を 읽었어요.")
    assert not _is_korean("これ")

    scene = SceneInput(
        category="class", poem_text="파도가 와요", poem_title="파도",
        class_subject="KOREAN", practiced_word="만져요",
    )
    out = _normalise_scenes(
        [scene],
        [{"category": "class", "subtitle": "시 읽기",
          "opening": "교실이에요", "narration": "「파도」を 읽었어요."}],
    )[0]
    assert "を" not in out.narration
    assert "파도" in out.narration          # 무슨 시였는지는 남는다
    assert "만져요" in out.narration        # 연습한 낱말도 남는다
    assert "파도가 와요" not in out.narration  # 그러나 시 본문은 안 옮긴다
