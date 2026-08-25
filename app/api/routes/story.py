from fastapi import APIRouter, Depends

from app.api.deps import get_provider
from app.core.envelope import success
from app.providers.base import InferenceProvider
from app.schemas.story import StoryRequest
from app.services import story_service

router = APIRouter(prefix="/story", tags=["story"])


@router.post("/generate")
def generate(
    body: StoryRequest,
    provider: InferenceProvider = Depends(get_provider),
):
    """동화 생성 — 하루치 4장면을 한 번에 받아 이야기로 엮는다.

    다른 엔드포인트와 달리 "방금 한 행동"이 아니라 "오늘 한 일 전부"가 온다.
    서버는 아무것도 저장하지 않으므로(무상태) 기록을 모아두는 것은 앱 몫이다.

    다른 엔드포인트보다 오래 걸린다 — 게이트웨이 타임아웃이 60초로 따로 잡혀 있다.
    """
    data = story_service.generate_story(provider, body)
    return success(data.model_dump(by_alias=True))
