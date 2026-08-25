"""표현 교정 — OpenAI 호출.

발음 채점(``feedback/speaking``)과 다르다.

| | 표현 교정 | 발음 채점 |
|---|---|---|
| 무엇을 보나 | 어떤 **낱말**을 골랐나 | 어떻게 **소리** 냈나 |
| 입력 | STT 텍스트 | 오디오 |
| 예 | "주세**여**" → "주세**요**" | 낱말은 맞지만 ㅈ 발음이 약함 |

아이에게 "틀렸다"고 말하지 않는 것이 이 기능의 핵심 제약이다. 화면에 그대로 실리는
문구라, 지적하는 말투가 나오면 그게 곧 제품 결함이다.
"""

from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import settings
from app.providers.clients.openai_client import reasoning
from app.core.logging import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """\
너는 한국어를 배우는 이주배경 어린이(만 5~8세)를 돕는 다정한 선생님이다.
아이가 말한 문장과, 그 상황에서 권하는 문장을 받아 짧은 피드백을 만든다.

반드시 지킬 것:
1. 절대 "틀렸다"고 하지 않는다. 먼저 알아들었다고 반겨주고, 그다음에 권한다.
2. 점수·등급·정답 여부를 말하지 않는다.
3. 문장은 짧고 쉬운 낱말로 쓴다. 한 줄은 20자 안팎이다.
4. naturalSentence 는 주어진 권장 문장을 그대로 쓴다. 새로 지어내지 않는다.
5. highlightWords 는 naturalSentence 안에 실제로 있는 어절만 고른다.
   아이가 이미 말한 어절은 넣지 않는다. 없으면 빈 배열이다.
6. 아이가 아무 말도 못 했으면(recognizedText 가 null) 탓하지 않고 함께 해보자고 한다.

출력은 아래 JSON 하나뿐이다. 설명·마크다운을 붙이지 않는다.
{"reaction": "...", "comment": "...", "naturalSentence": "...",
 "naturalHint": "...", "highlightWords": ["..."]}
reaction 과 comment 는 두 줄이며 줄바꿈은 \\n 하나로 표시한다."""


def expression_feedback(
    client: OpenAI,
    target_sentence: str,
    recognized_text: str | None,
    scenario: str | None,
    nickname: str,
) -> dict:
    payload = {
        "아이_호칭": nickname,
        "상황": scenario,
        "권장_문장": target_sentence,
        "아이가_말한_것": recognized_text,
    }
    response = client.chat.completions.create(
        model=settings.openai_llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        # 아이가 말한 것과 권장 문장을 견줘야 해서 판단이 조금 필요하다
        **reasoning("low"),
    )
    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("expression JSON 파싱 실패: %s", raw[:300])
        raise ValueError("피드백 응답을 해석할 수 없습니다.") from exc

    # LLM 이 권장 문장을 고쳐 오면 화면의 따라 말하기 문장과 어긋난다 —
    # 그 문장은 앱이 캐시해 TTS 로도 쓰므로 여기서 원본으로 되돌린다.
    natural = str(data.get("naturalSentence") or "").strip() or target_sentence
    words = set(natural.split())
    return {
        "reaction": str(data.get("reaction") or "잘했어!\n무슨 말인지 이해했어."),
        "comment": str(data.get("comment") or "다음에는 이렇게 말해볼까요?"),
        "natural_sentence": natural,
        "natural_hint": str(data.get("naturalHint") or ""),
        # 문장에 없는 어절이 오면 화면이 짚을 자리를 못 찾는다. 있는 것만 남긴다.
        "highlight_words": [w for w in (data.get("highlightWords") or []) if w in words],
    }
