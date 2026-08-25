from openai import OpenAI

from app.core.config import settings


def load_openai_client() -> OpenAI:
    """타임아웃과 재시도를 **반드시** 지정한다.

    SDK 기본값은 요청당 600초에 재시도 2회이고 타임아웃도 재시도 대상이라, 한 번의
    호출이 30분 가까이 살아 있을 수 있다. 게이트웨이는 가장 긴 동화조차 60초에
    끊으므로, 아이는 이미 실패 화면을 본 뒤인데 서버만 유료 호출을 붙들고 있게 된다.
    """
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_sec,
        max_retries=settings.openai_max_retries,
    )


#: reasoning_effort 를 받는 모델. 그 밖의 모델에 보내면 400 이 난다.
_REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def supports_reasoning_effort(model: str) -> bool:
    return model.lower().startswith(_REASONING_MODEL_PREFIXES)


def reasoning(effort: str) -> dict:
    """추론 강도를 담은 호출 인자.

    gpt-5 계열은 답을 내기 전에 **추론 토큰**을 쓴다. 기본값이면 한 줄짜리 답에도
    수백 토큰을 태워, 동화 4장면을 한 번에 만들 때 게이트웨이의 60초 제한을 넘겼다
    (실측: 기본 60초 초과 / minimal 로는 몇 초).

    그래서 호출마다 필요한 만큼만 준다.
      minimal — 번역·대화처럼 판단할 것이 없는 호출. 기다림이 곧 손해다
      low     — 동화·표현 교정처럼 "기록에 있는 것만 쓴다" 같은 제약을 지켜야 하는 호출

    reasoning 모델이 아니면 아무것도 넣지 않는다 — 그 모델에 보내면 400 이다.
    """
    if not supports_reasoning_effort(settings.openai_llm_model):
        return {}
    return {"reasoning_effort": effort}
