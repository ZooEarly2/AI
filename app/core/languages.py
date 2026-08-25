"""언어 코드 변환.

세 가지 표기가 한 요청 안에서 섞여 들어온다.

* 앱 계약(enum)      : ``KOREAN`` / ``CHINESE`` / ``VIETNAMESE``  — /tts, /story, /feedback
* BCP-47(자유 문자열): ``ko-KR`` / ``zh-CN`` / ``vi-VN``          — /stt 의 ``language``
* 모델 코드          : ``ko`` / ``zh`` / ``vi``                    — whisper·OpenAI 가 받는 값

들어올 때는 셋 다 받아 모델 코드로 낮추고, 나갈 때는 반드시 enum 으로 올려 보낸다.
게이트웨이가 응답을 가공하지 않으므로 여기서 올려주지 않으면 앱이 그대로 못 읽는다.
"""

from __future__ import annotations

# 앱 계약 enum ↔ 모델 코드
ENUM_TO_CODE: dict[str, str] = {
    "KOREAN": "ko",
    "CHINESE": "zh",
    "VIETNAMESE": "vi",
}
CODE_TO_ENUM: dict[str, str] = {code: name for name, code in ENUM_TO_CODE.items()}

DEFAULT_LANGUAGE_CODE = "ko"
DEFAULT_BCP47 = "ko-KR"

# OpenAI 프롬프트에 쓰는 사람이 읽는 이름
LANGUAGE_NAMES: dict[str, str] = {
    "ko": "Korean",
    "vi": "Vietnamese",
    "zh": "Chinese",
}


def to_code(value: str | None, default: str = DEFAULT_LANGUAGE_CODE) -> str | None:
    """어떤 표기로 와도 모델 코드(ko/vi/zh)로 낮춘다. 모르는 값이면 ``None``.

    ``None``(파트 자체가 안 온 경우)은 오류가 아니라 기본값이다 — 게이트웨이는
    선택 필드를 빈 값이 아니라 아예 빼고 보낸다(연동 규약 §2-②).
    """
    if value is None:
        return default
    raw = value.strip()
    if not raw:
        return default
    upper = raw.upper()
    if upper in ENUM_TO_CODE:
        return ENUM_TO_CODE[upper]
    # ko-KR / zh-Hans-CN 처럼 하위 태그가 붙어 와도 앞부분만 본다
    primary = raw.replace("_", "-").split("-", 1)[0].lower()
    return primary if primary in CODE_TO_ENUM else None


def to_enum(code: str | None) -> str:
    """모델 코드를 앱 계약 enum 으로 올린다. 응답에 싣는 값은 반드시 이쪽이다."""
    return CODE_TO_ENUM.get((code or "").lower(), "KOREAN")


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)
