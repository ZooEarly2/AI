from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_provider
from app.core.envelope import success
from app.core.exceptions import InvalidRequest
from app.core.sentences import SENTENCES, SentenceId, category_of
from app.providers.base import InferenceProvider
from app.schemas.feedback import ExpressionFeedbackRequest, SentenceItem
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/sentences")
def list_sentences(provider: InferenceProvider = Depends(get_provider)):
    """추천 문장 10개(등교/급식/하교 각 3개 + 수업 동시 1개).

    이 서버가 sentenceId ↔ 문장 텍스트의 **단일 소스**다. 앱은 id 만 들고 다니다가
    채점 때 그대로 돌려보낸다 — 자유 텍스트를 주고받으면 화면에 보인 문장과 채점한
    문장이 어긋날 수 있다.

    이 요청이 오면 **채점 서비스를 미리 깨운다.** 앱은 연습 화면에 들어오면서 이
    목록부터 받아가는데, 그 사이 아이는 문장을 읽고 고른다. 그동안 컨테이너가 뜨면
    마이크를 누른 뒤의 기다림이 사라진다 — 콜드 스타트 실측이 38초다.
    """
    provider.warm_up_scoring()
    items = [
        SentenceItem(sentence_id=sid, category=category_of(sid), text=text)
        for sid, text in SENTENCES.items()
    ]
    return success([item.model_dump(by_alias=True) for item in items])


@router.post("/speaking")
def speaking_feedback(
    audio: UploadFile | None = File(default=None),
    audio_file: UploadFile | None = File(default=None),
    sentenceId: str | None = Form(default=None),  # noqa: N803 - 앱 계약이 camelCase다
    sentence_id: str | None = Form(default=None),
    provider: InferenceProvider = Depends(get_provider),
):
    """발음 채점 — 녹음을 고른 문장과 비교해 가장 약한 어절 1개를 짚는다.

    STT 를 거치지 않는다. 발음은 텍스트로 알 수 없기 때문에 녹음을 그대로 본다.

    파트 이름을 두 벌 받는 이유는 ``/speech/transcribe`` 와 같다 — 게이트웨이는
    ``audio``/``sentenceId``, 초기 명세는 ``audio_file``/``sentence_id`` 다.
    """
    upload = audio or audio_file
    if upload is None:
        raise InvalidRequest("녹음 파일이 필요합니다.", field="audio")

    raw_id = sentenceId or sentence_id
    if not raw_id:
        raise InvalidRequest("문장을 고르지 않았습니다.", field="sentenceId")
    try:
        parsed_id = SentenceId(raw_id)
    except ValueError as exc:
        # 목록에 없는 id 다. 게이트웨이는 이 값을 검증하지 않으므로(연동 규약 §3)
        # 어느 값이 잘못됐는지 여기서 알려줘야 앱이 고칠 수 있다.
        raise InvalidRequest("알 수 없는 문장 id 입니다.", field="sentenceId") from exc

    data = feedback_service.score_speaking(provider, upload, parsed_id)
    return success(data.model_dump(by_alias=True))


@router.post("/expression")
def expression_feedback(
    body: ExpressionFeedbackRequest,
    provider: InferenceProvider = Depends(get_provider),
):
    """표현 교정 — "이렇게 말하면 더 자연스러워요" 화면.

    발음 채점과 다르다. 저쪽은 오디오로 "어떻게 소리 냈나"를 보고, 이쪽은 STT 텍스트로
    "어떤 말을 골랐나"를 본다. 모국어 번역도 이 응답에 함께 담는다 — 앱이 번역을 따로
    부르면 같은 화면을 두 번 기다리게 된다(연동 규약 §1-1).
    """
    data = feedback_service.expression_feedback(provider, body)
    return success(data.model_dump(by_alias=True))
