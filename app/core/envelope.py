"""응답 봉투 — 연동 규약 §5.

게이트웨이는 body 를 파싱하지 않고 String 으로 통과시킨다. 그래서 **FastAPI 응답이
곧 앱이 받는 JSON**이고, 봉투를 만드는 책임도 여기에 있다. 라우트가 dict 를 그냥
돌려주면 앱은 `success`/`data`가 없어서 통째로 못 읽는다.

    성공 : {"success": true,  "data": {...}}
    실패 : {"success": false, "error": {"code","message","field"}}

`field` 는 값이 ``None`` 이어도 키가 남아야 한다 — 앱이 `error.field` 로 바로
접근한다. 그래서 exclude_none 을 쓰지 않고 명시적으로 담는다.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def error_body(code: str, message: str, field: str | None = None) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message, "field": field}}


def error_response(
    status_code: int, code: str, message: str, field: str | None = None
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_body(code, message, field))
