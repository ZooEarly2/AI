"""동화 생성 스키마 — 연동 규약 §3 ``/story/generate``.

하루치 플레이 기록 4장면을 받아 동화로 엮는다. 서버는 아무것도 저장하지 않으므로
(무상태) 기록을 모아두는 것은 앱 몫이고, 여기로는 한 번에 도착한다.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.schemas.common import CamelModel, CamelRequest


class StoryCategory(str, Enum):
    """장면 종류.

    ⚠️ 문장 목록(``/feedback/sentences``)의 category 와 값이 다르다 —
    저쪽은 ``arrival``/``study``/``lunch``/``departure``, 이쪽은 아래 4개다.
    섞어 쓰면 422 다.
    """

    SCHOOL_ARRIVAL = "school_arrival"
    CLASS = "class"
    LUNCH = "lunch"
    SCHOOL_DEPARTURE = "school_departure"


#: 하루를 시간순으로 잇는 것이라 순서 자체가 의미다. 어긋나면 422.
STORY_ORDER: list[StoryCategory] = [
    StoryCategory.SCHOOL_ARRIVAL,
    StoryCategory.CLASS,
    StoryCategory.LUNCH,
    StoryCategory.SCHOOL_DEPARTURE,
]

#: 상대방 대사가 있어야 이야기가 성립하는 장면. class(시 읽기)만 예외다.
DIALOGUE_CATEGORIES = {
    StoryCategory.SCHOOL_ARRIVAL,
    StoryCategory.LUNCH,
    StoryCategory.SCHOOL_DEPARTURE,
}

CATEGORY_LABELS: dict[StoryCategory, str] = {
    StoryCategory.SCHOOL_ARRIVAL: "등교",
    StoryCategory.CLASS: "수업",
    StoryCategory.LUNCH: "급식",
    StoryCategory.SCHOOL_DEPARTURE: "하교",
}


class SceneInput(CamelRequest):
    category: StoryCategory
    #: 대화 장면 필수 — 상대방이 아이에게 한 말
    partner_line: str | None = None
    #: 아이가 고른 문장. 고르지 않고 넘어갔으면 ``None``
    child_said: str | None = None
    #: class 장면 필수 — 아이가 읽은 동시 전문
    poem_text: str | None = None
    #: 발음이 약해 연습한 낱말(``/feedback/speaking`` 의 targetWord). 없으면 ``None``
    practiced_word: str | None = None


class StoryRequest(CamelRequest):
    child_name: str
    scenes: list[SceneInput] = Field(min_length=1)


class SceneOutput(CamelModel):
    category: StoryCategory
    #: 장면 소제목 (4~10음절)
    subtitle: str
    #: 장면을 여는 전환구
    opening: str
    #: 아이가 한 말을 그대로 인용. 없으면 ``None``
    quote: str | None
    #: 동화 문장 2~3개. 실제 기록만 기반으로 쓰고 새 사건·인물을 만들지 않는다
    narration: str


class StoryData(CamelModel):
    title: str
    scenes: list[SceneOutput]
