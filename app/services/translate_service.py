from __future__ import annotations

from app.core.exceptions import InvalidRequest, UpstreamUnavailable
from app.core.languages import to_code, to_enum
from app.core.logging import get_logger
from app.providers.base import InferenceProvider
from app.schemas.translate import TranslateData, TranslateRequest

log = get_logger(__name__)


def translate_text(provider: InferenceProvider, request: TranslateRequest) -> TranslateData:
    text = request.text.strip()
    if not text:
        raise InvalidRequest("번역할 문장이 비어 있습니다.", field="text")

    target = to_code(request.target_language, default=None)
    if target is None:
        raise InvalidRequest("지원하지 않는 언어입니다.", field="targetLanguage")
    source = to_code(request.source_language) or "ko"

    try:
        translated = provider.translate(
            text=text, source_language=source, target_language=target
        )
    except Exception as exc:
        log.warning("번역 실패: %s", exc)
        raise UpstreamUnavailable("번역 서비스에 연결할 수 없습니다.") from exc

    # 응답의 언어 코드는 앱 계약 enum 으로 올려 보낸다 — 게이트웨이가 가공하지 않으므로
    # 여기서 ko/vi/zh 로 내보내면 앱이 그대로 못 읽는다(연동 규약 §1-1 표 5번).
    return TranslateData(translation=translated, target_language=to_enum(target))
