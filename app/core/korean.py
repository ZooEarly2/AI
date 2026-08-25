"""한국어 조사 처리.

아이 이름을 내레이션에 그대로 넣기 때문에 "지우가 / 지훈이가"를 틀리면 바로 어색해진다.
이름은 요청마다 달라 문장에 박아둘 수 없으므로 받침을 보고 고른다.
"""

from __future__ import annotations

_HANGUL_START, _HANGUL_END = 0xAC00, 0xD7A3


def has_final_consonant(word: str) -> bool:
    """마지막 글자에 받침이 있는가. 한글이 아니면 없는 것으로 본다."""
    if not word:
        return False
    code = ord(word[-1])
    if _HANGUL_START <= code <= _HANGUL_END:
        return (code - _HANGUL_START) % 28 != 0
    return False


def josa(word: str, with_final: str, without_final: str) -> str:
    """``josa("지훈", "이가", "가")`` → ``"지훈이가"``."""
    return word + (with_final if has_final_consonant(word) else without_final)


def vocative(name: str) -> str:
    """호격 — "민수야" / "지훈아"."""
    return josa(name, "아", "야")
