from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key
from app.api.routes import chat, feedback, health, speech, story, translate

api_router = APIRouter()
api_router.include_router(health.router)

# 게이트웨이만 부르는 내부 API. 앱은 /api/v1/ai/* 로 게이트웨이를 부르고,
# 게이트웨이가 이 경로로 미러링한다 — 접두어가 다른 것은 의도된 것이다.
#
# 인증은 라우터 단위로 건다. API_KEY 가 비어 있으면 검사하지 않으므로(deps.verify_api_key)
# 로컬·목 서버는 헤더 없이 그대로 붙고, /health 는 이 검사 밖에 있어 배포 후에도
# 헬스체크가 인증 없이 돈다.
v1_router = APIRouter(prefix="/internal/v1", dependencies=[Depends(verify_api_key)])
v1_router.include_router(speech.router)
v1_router.include_router(translate.router)
v1_router.include_router(feedback.router)
v1_router.include_router(story.router)
v1_router.include_router(chat.router)

api_router.include_router(v1_router)
