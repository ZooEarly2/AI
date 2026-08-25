from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PROVIDER=mock 이면 모델을 아예 올리지 않는다. 로컬 기동이 빨라지는 것도 있지만,
    # 더 중요한 건 faster-whisper/OpenAI 를 import 조차 하지 않는다는 것이다 —
    # 목 모드로 도는 개발 PC·CI 에 무거운 의존성 설치를 강요하지 않기 위해서다.
    if settings.provider == "real":
        from app.providers.clients.clova_client import load_clova_client
        from app.providers.clients.openai_client import load_openai_client
        from app.providers.clients.scoring_client import load_scoring_client

        app.state.openai_client = load_openai_client()
        app.state.scoring_client = load_scoring_client()
        app.state.clova_client = load_clova_client()
        # whisper 는 여기서 올리지 않는다. 모델이 수백 MB 라 기동이 그만큼 늦어지는데,
        # 지금 앱 화면은 STT 를 부르지 않는다. 첫 요청이 올 때 RealProvider 가 올린다.
        app.state.whisper_model = None
        logger.info(
            "PROVIDER=real / OpenAI=%s / CLOVA=%s / scoring ready. whisper loads on first STT.",
            settings.openai_llm_model,
            settings.clova_tts_voice if settings.clova_client_id else "미설정",
        )
    else:
        logger.info("PROVIDER=mock — 모델을 올리지 않는다.")
    yield
    if settings.provider == "real":
        app.state.scoring_client.close()
        app.state.clova_client.close()


app = FastAPI(
    title="쥬얼리(ZooEarly) 추론 서버",
    description=(
        "Spring 게이트웨이가 부르는 내부 API. 앱이 직접 부르지 않는다.\n\n"
        "모든 응답은 `{success, data}` 봉투에 camelCase 로 담긴다 — 게이트웨이가 body 를 "
        "가공하지 않고 통과시키므로, 이 서버의 응답이 곧 앱이 받는 JSON 이다."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# 정상 경로(게이트웨이 → FastAPI)는 서버 대 서버라 CORS 와 무관하다.
# 이 설정은 브라우저에서 /docs 를 열거나 프론트를 FastAPI 에 직접 붙여 볼 때를 위한 것이다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)
