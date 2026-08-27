"""에러 → 연동 규약 §5 봉투 변환.

게이트웨이는 **422 와 429 의 body 만** 앱까지 그대로 통과시키고, 나머지 4xx/5xx 는
body 를 버리고 ``502 AI_SERVER_ERROR`` 로 감싼다. 즉 앱이 읽을 수 있는 에러를 만들
기회는 이 두 상태 코드뿐이다.

FastAPI 기본 에러(``{"detail": ...}``)와 pydantic 검증 실패(``{"detail":[...]}``)를
그대로 두면 422 가 그 모양 그대로 앱까지 도착해 파싱이 깨진다. 그래서 세 종류를
전부 여기서 가로채 봉투로 바꾼다.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.envelope import error_response
from app.core.logging import get_logger

log = get_logger(__name__)


class InferenceServerError(Exception):
    """추론 서버가 직접 만드는 에러의 기반 클래스.

    ``status_code`` 를 422/429 로 두면 body 가 앱까지 간다. 그 밖의 값은 게이트웨이가
    502 로 감싸므로, 앱에 뜻을 전하고 싶으면 422/429 를 써야 한다.
    """

    status_code = 500
    error_code = "AI_SERVER_ERROR"

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class InvalidRequest(InferenceServerError):
    """요청 값이 계약과 다르다. 게이트웨이가 먼저 걸러주지만 직접 호출도 막는다."""

    status_code = 422
    error_code = "INVALID_PARAMETER"


class OffScript(InferenceServerError):
    """아이가 고른 문장이 아니라 **아주 다른 말**을 했다.

    ``INVALID_PARAMETER`` 와 갈라 놓은 이유가 있다. 저쪽은 "요청이 잘못됐다"라서
    아이가 할 수 있는 일이 없지만, 이쪽은 **다시 말하면 되는 일**이다. 앱이 두
    경우를 구분하지 못하면 둘 다 같은 처리를 하게 되는데, 실제로 그랬다 —
    앱은 채점이 실패한 모든 경우를 칭찬 화면으로 흘려보내서, 아이가 전혀 다른
    말을 해도 "잘했어!" 가 떴다. 서버는 알고 있었고 앱이 그 신호를 버렸다.

    상태 코드는 422 그대로다. 게이트웨이가 422 만 본문째 통과시키기 때문에
    (§1.3) 다른 코드로 바꾸면 이 구분이 앱까지 닿지 못한다.
    """

    status_code = 422
    error_code = "OFF_SCRIPT"


class SttFailed(InferenceServerError):
    """STT 엔진 자체가 실패했다.

    아이가 우물거려 못 알아들은 것은 여기 해당하지 않는다 — 그건 ``text: null`` 로
    200 을 준다(연동 규약 §5). 422 는 "엔진이 죽었다"는 뜻으로만 쓴다.
    """

    status_code = 422
    error_code = "STT_FAILED"


class UpstreamUnavailable(InferenceServerError):
    """OpenAI·채점 서비스 등 바깥 의존성 실패. 앱에는 502 로만 도착한다."""

    status_code = 502
    error_code = "AI_SERVER_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InferenceServerError)
    async def _handle_inference_error(request: Request, exc: InferenceServerError):
        if exc.status_code >= 500:
            log.warning("%s: %s", exc.error_code, exc.message)
        return error_response(exc.status_code, exc.error_code, exc.message, exc.field)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError):
        # pydantic 기본 형식은 {"detail":[{...}]} 이라 앱이 못 읽는다.
        # 어느 입력이 문제인지는 앱이 고쳐야 할 값이므로 field 로 옮겨 담는다.
        field = None
        errors = exc.errors()
        if errors:
            location = [part for part in errors[0].get("loc", ()) if part not in ("body", "query")]
            field = ".".join(str(part) for part in location) or None
        return error_response(
            422, "INVALID_PARAMETER", "요청 값이 올바르지 않습니다.", field
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없습니다."
        code = "INVALID_PARAMETER" if exc.status_code < 500 else "AI_SERVER_ERROR"
        return error_response(exc.status_code, code, detail)

    @app.exception_handler(Exception)
    async def _handle_unknown(request: Request, exc: Exception):
        log.exception("unhandled inference error")
        return error_response(500, "AI_SERVER_ERROR", "추론 서버 내부 오류입니다.")
