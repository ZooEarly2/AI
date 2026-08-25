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
