"""요청·응답 모델의 공통 규칙.

앱 계약이 camelCase 다(연동 규약 §1-1 표 4번). 게이트웨이가 body 를 가공하지 않으니
FastAPI 가 camelCase 로 내보내야 앱이 읽는다. 반대로 요청은 camelCase 로 도착하는데,
기존 snake_case 호출(초기 명세·직접 curl)도 그대로 살려두려고 별칭을 함께 받는다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(field: str) -> str:
    head, *rest = field.split("_")
    return head + "".join(word.capitalize() for word in rest)


class CamelModel(BaseModel):
    """응답 모델 기반.

    ``serialization_alias`` 로 camelCase 를 내보내되 ``populate_by_name`` 을 켜 둬서
    코드에서는 snake_case 필드명 그대로 만들 수 있다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CamelRequest(CamelModel):
    """요청 모델 기반.

    camelCase(앱·게이트웨이)와 snake_case(초기 FastAPI 명세) 를 둘 다 받는다.
    ``populate_by_name=True`` 가 필드명(snake_case) 입력을 허용하고, alias 가
    camelCase 를 받는다. 모르는 키는 무시한다 — 앱이 필드를 더 붙여 보내도
    추론 서버가 422 로 끊지 않게 한다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="ignore",
    )
