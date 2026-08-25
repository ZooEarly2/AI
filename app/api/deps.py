from fastapi import Header, Request

from app.core.config import settings
from app.core.exceptions import InferenceServerError
from app.providers.base import InferenceProvider
from app.providers.mock import MockProvider


class Unauthorized(InferenceServerError):
    """X-API-Key 불일치. 게이트웨이가 502 로 감싸므로 앱에는 상세가 가지 않는다."""

    status_code = 401
    error_code = "UNAUTHORIZED"


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """게이트웨이가 실어 보내는 ``X-API-Key`` 검사.

    ``API_KEY`` 가 비어 있으면 검사하지 않는다 — 로컬 개발과 목 서버가 헤더 없이
    그대로 붙기 위한 것이다. 배포 환경에서는 반드시 값을 채워야 한다.
    """
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise Unauthorized("인증에 실패했습니다.")


def get_provider(request: Request) -> InferenceProvider:
    """PROVIDER 환경변수로 MockProvider / RealProvider 를 고른다.

    RealProvider 를 모듈 최상단에서 import 하지 않는 이유: faster-whisper 를 끌고 오는데,
    PROVIDER=mock 으로 도는 로컬·CI 에서는 필요 없는 무거운 의존성이다. 최상단 import 로
    두면 mock 모드에서도 설치가 강제된다.
    """
    if settings.provider == "mock":
        return MockProvider()

    from app.providers.real import RealProvider

    # app.state 를 통째로 넘긴다 — whisper 를 첫 요청에 올려 여기에 담아 두기 때문이다.
    return RealProvider(request.app.state)
