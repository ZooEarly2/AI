import threading
import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# 예열은 "깨어 있나?" 를 묻는 것뿐이다. 오래 붙들 이유가 없다.
_WARM_TIMEOUT_SEC = 5.0

# Azure Container Apps는 트래픽이 없으면 스케일이 0으로 내려가고, 다음 요청이 오면
# 그제서야 컨테이너를 깨워 모델을 재로드한다. 그 콜드 스타트가 타임아웃보다 길면
# 첫 요청이 실패하는데, 그 사이 컨테이너는 계속 깨어나는 중이라 잠깐 쉬었다 한 번
# 더 시도하면 대부분 바로 성공한다.
_MAX_ATTEMPTS = 2
_RETRY_DELAY_SEC = 2


class ScoringServiceError(Exception):
    """Base class for failures talking to the Azure-hosted word_scorer_v0.1/serve API."""


class ScoringServiceUnavailable(ScoringServiceError):
    """Network/timeout failure reaching the scoring service."""


class ScoringServiceBadRequest(ScoringServiceError):
    """Scoring service rejected the request (bad audio, off-script guard, etc.)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def load_scoring_client() -> httpx.Client:
    headers = {"X-API-Key": settings.scoring_api_key} if settings.scoring_api_key else {}
    return httpx.Client(
        base_url=settings.scoring_api_base_url,
        headers=headers,
        timeout=settings.scoring_timeout_sec,
    )


def score_word(client: httpx.Client, audio_path: str, text: str) -> dict:
    """Calls POST /score on word_scorer_v0.1/serve/app.py and returns its
    JSON body (text, clean_text, g2p_text, off_script, words[...], ...) as-is."""
    response = None
    last_exc: httpx.RequestError | None = None
    for attempt in range(_MAX_ATTEMPTS):
        if attempt > 0:
            time.sleep(_RETRY_DELAY_SEC)
        with open(audio_path, "rb") as audio_file:
            files = {"audio": (audio_path, audio_file, "application/octet-stream")}
            data = {"text": text}
            try:
                response = client.post("/score", files=files, data=data)
                break
            except httpx.RequestError as exc:
                last_exc = exc

    if response is None:
        raise ScoringServiceUnavailable(
            f"채점 서비스 연결 실패({_MAX_ATTEMPTS}회 시도): {last_exc}"
        ) from last_exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ScoringServiceBadRequest(str(detail))

    return response.json()


# ── 미리 깨우기 ──────────────────────────────────────
#
# 채점 서비스는 min-replicas 가 0이라 유휴 뒤 첫 요청이 컨테이너를 깨우며 30초 넘게
# 걸린다. 그 기다림을 **아이가 마이크를 누른 뒤**에 겪게 하면 안 된다.
#
# 앱은 연습 화면에 들어오면서 문장 목록을 먼저 받아간다. 그때 채점 서비스를 함께
# 깨워두면, 아이가 문장을 고르고 마이크를 누를 때쯤엔 이미 예열돼 있다.
# 실패해도 아무 일도 하지 않는다 — 이건 준비 운동이지 요청이 아니다.

_WARM_INTERVAL_SEC = 90.0
_last_warm = 0.0
_warm_lock = threading.Lock()


def warm_up(client: httpx.Client) -> None:
    """채점 서비스를 미리 깨운다. 곧바로 돌아오고, 실패는 삼킨다."""
    global _last_warm

    with _warm_lock:
        now = time.monotonic()
        # 화면을 오갈 때마다 두드리지 않는다. 한 번 깨우면 한동안 깨어 있다.
        if now - _last_warm < _WARM_INTERVAL_SEC:
            return
        _last_warm = now

    def knock() -> None:
        try:
            client.get("/health", timeout=_WARM_TIMEOUT_SEC)
        except Exception as exc:  # noqa: BLE001 - 준비 운동이라 어떤 실패도 조용히 넘긴다
            log.debug("채점 서비스 예열 실패(무시): %s", exc)

    threading.Thread(target=knock, name="scoring-warmup", daemon=True).start()
