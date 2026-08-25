from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_provider
from app.core.envelope import success
from app.core.exceptions import InvalidRequest
from app.providers.base import InferenceProvider
from app.services import chat_service

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    audio: UploadFile | None = File(default=None),
    audio_file: UploadFile | None = File(default=None),
    scenario: str = Form(...),
    history: str | None = Form(default=None),
    nickname: str = Form(...),
    nativeLanguage: str | None = Form(default=None),  # noqa: N803 - 앱 계약이 camelCase다
    native_language: str | None = Form(default=None),
    provider: InferenceProvider = Depends(get_provider),
):
    """자유 대화 — STT + LLM + TTS 한 번에.

    현재 이 화면이 앱에 없어 호출되지 않지만, 게이트웨이에 경로가 살아 있어 계약을
    맞춰 둔다. ``nativeLanguage`` 는 선택이라 파트가 아예 안 올 수 있다.
    """
    upload = audio or audio_file
    if upload is None:
        raise InvalidRequest("녹음 파일이 필요합니다.", field="audio")

    data = chat_service.chat(
        provider,
        audio_file=upload,
        scenario=scenario,
        history_raw=history,
        nickname=nickname,
        native_language=nativeLanguage or native_language,
    )
    return success(data.model_dump(by_alias=True, exclude_none=True))
