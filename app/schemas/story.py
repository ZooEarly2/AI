"""동화 생성 스키마 — 연동 규약 §3 ``/story/generate``.

하루치 플레이 기록 4장면을 받아 동화로 엮는다. 서버는 아무것도 저장하지 않으므로
(무상태) 기록을 모아두는 것은 앱 몫이고, 여기로는 한 번에 도착한다.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

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
    #: 그 말을 한 사람("급식 선생님" · "코끼리 선생님" · "호랑이 친구").
    #:
    #: **없으면 동화가 "다른 사람이" 라고 쓴다.** 프롬프트가 "기록에 없는 인물을
    #: 만들지 마라" 라고 못박아 두어서, 누구인지 안 알려주면 LLM 은 뭉뚱그리는
    #: 수밖에 없다. 옛 앱은 이 값을 안 보내므로 없으면 예전처럼 동작한다.
    partner_name: str | None = None
    #: 아이가 고른 문장. 고르지 않고 넘어갔으면 ``None``
    child_said: str | None = None
    #: class 장면 필수 — 아이가 수업시간에 한 일.
    #:
    #: 이름이 poem_text 인 것은 처음에 수업시간이 동시 읽기 하나뿐이었기 때문이다.
    #: 지금은 수학(과일 세기)도 있어서 **이름만으로는 무엇인지 알 수 없다** —
    #: 어느 쪽인지는 아래 class_subject 가 말한다. 이름을 바꾸지 않는 이유는
    #: 이미 배포된 앱이 poemText 로 보내고 있어서다. 그쪽을 깨뜨릴 수 없다.
    poem_text: str | None = None
    #: 읽은 시의 제목("꽃"·"눈"·"파도"·"감기"). 국어 시간에만 있다.
    #:
    #: **이게 있으면 시 본문은 LLM 에 안 넘긴다.** 본문을 주면 동화가 시를 통째로
    #: 옮겨 적어, 네 줄짜리 시가 동화 한 장을 다 먹는다. 아이에게 필요한 것은
    #: "무슨 시를 읽었나" 이지 그 시를 다시 읽는 것이 아니다.
    #: 옛 앱은 이 값을 안 보낸다 — 없으면 예전처럼 본문으로 쓴다.
    poem_title: str | None = None
    #: 수업시간의 과목. 없으면 국어(동시)로 본다 — 옛 앱은 이 값을 안 보낸다.
    #:
    #: **이게 없으면 동화가 거짓말을 한다.** 실제로 그랬다: 과일을 센 아이의
    #: 기록이 "아이가_읽은_동시" 라는 이름으로 LLM 에 넘어가고, 대체 문구는
    #: "동시를 또박또박 읽었어요" 였다. 아이는 그날 시를 읽지 않았다.
    class_subject: Literal["KOREAN", "MATH"] | None = None
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
    #: 수업시간의 과목. 요청에 담겨 온 값을 그대로 돌려준다.
    #:
    #: **앱이 삽화를 이 값으로 고른다.** 그림에 "국어시간 · 동시 읽어보기" 가 글자로
    #: 그려져 있어서, 과목을 모르면 과일을 센 아이에게 국어 그림이 나간다.
    #: 앨범은 서버가 돌려준 장면을 그대로 저장하므로, 여기 실어 보내지 않으면
    #: **나중에 다시 꺼내 볼 때도 영영 알 수 없다** — 그래서 되돌려 준다.
    class_subject: Literal["KOREAN", "MATH"] | None = None


class StoryData(CamelModel):
    title: str
    scenes: list[SceneOutput]
