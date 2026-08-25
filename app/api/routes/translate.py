from fastapi import APIRouter, Depends

from app.api.deps import get_provider
from app.core.envelope import success
from app.providers.base import InferenceProvider
from app.schemas.translate import TranslateRequest
from app.services import translate_service

router = APIRouter(prefix="/text", tags=["translate"])


@router.post("/translate")
def translate(
    body: TranslateRequest,
    provider: InferenceProvider = Depends(get_provider),
):
    """번역 — "이 말의 뜻이에요!" 화면.

    표현 교정(``/feedback/expression``) 응답에 번역이 이미 들어 있어 정상 경로에서는
    부르지 않아도 된다. 모국어 문장을 따로 읽어줘야 할 때를 위해 남겨둔다.
    """
    data = translate_service.translate_text(provider, body)
    return success(data.model_dump(by_alias=True))
