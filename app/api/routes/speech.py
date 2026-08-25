from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_provider
from app.core.envelope import success
from app.core.exceptions import InvalidRequest
from app.providers.base import InferenceProvider
from app.schemas.speech import SynthesizeRequest
from app.services import speech_service

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post("/transcribe")
def transcribe(
    audio: UploadFile | None = File(default=None),
    audio_file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    language_code: str | None = Form(default=None),
    provider: InferenceProvider = Depends(get_provider),
):
    """음성 → 텍스트.

    파트 이름을 두 벌 받는다. 게이트웨이는 앱 계약대로 ``audio``/``language`` 로 보내고
    (연동 규약 §3), 초기 FastAPI 명세와 기존 테스트·curl 은 ``audio_file``/``language_code``
    를 쓴다. 한쪽만 받으면 다른 쪽이 전부 422 가 되므로 둘 다 받아 흡수한다.

    ``language`` 는 선택이다 — 게이트웨이는 생략된 필드를 빈 값이 아니라 **파트째로
    빼고** 보내므로 ``Form(...)`` 로 필수 선언하면 그 요청이 통째로 422 가 된다.
    """
    upload = audio or audio_file
    if upload is None:
        raise InvalidRequest("녹음 파일이 필요합니다.", field="audio")

    data = speech_service.transcribe_audio(provider, upload, language or language_code)
    return success(data.model_dump(by_alias=True))


@router.post("/synthesize")
def synthesize(
    body: SynthesizeRequest,
    provider: InferenceProvider = Depends(get_provider),
):
    """텍스트 → 음성 (base64 JSON).

    바이너리(audio/mpeg)로 돌려주지 않는 이유는 게이트웨이가 body 를 String 으로 받아
    그대로 통과시키기 때문이다 — 바이너리는 도중에 깨진다(연동 규약 §1-1 표 1번).
    """
    data = speech_service.synthesize_speech(provider, body)
    return success(data.model_dump(by_alias=True, exclude_none=True))
