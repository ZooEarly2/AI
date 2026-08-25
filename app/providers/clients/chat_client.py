"""자유 대화 — 아이 발화에 대한 상대 캐릭터의 답을 만든다.

STT 결과와 지금까지의 대화를 받아 한 마디를 돌려준다. 음성 합성은 여기서 하지 않는다 —
speech 파이프라인이 따로 있고, 대사를 만드는 일과 소리로 바꾸는 일은 실패하는 지점이
다르기 때문이다(LLM 장애와 TTS 장애를 따로 다뤄야 한다).
"""

from __future__ import annotations

from openai import OpenAI

from app.core.config import settings
from app.providers.clients.openai_client import reasoning

_SCENARIO_ROLES = {
    "ARRIVAL": "교문 앞에서 만난 또래 친구",
    "CLASS": "국어 수업을 이끄는 다정한 선생님",
    "LUNCH": "급식을 나눠 주는 급식 선생님",
    "DISMISSAL": "하교하는 아이를 배웅하는 담임 선생님",
}

_SYSTEM_PROMPT = """\
너는 한국 초등학교에서 이주배경 아동을 만나는 {role}이다.
아이는 한국어를 배우는 중이라 문장이 짧고 서툴 수 있다.

반드시 지킬 것:
1. 한 번에 한 문장, 20자 안팎으로만 말한다.
2. 쉬운 낱말만 쓴다. 아이가 못 알아들을 말은 피한다.
3. 문법을 고쳐 주지 않는다. 알아들은 대로 자연스럽게 대화를 잇는다.
4. 아이 말을 못 알아들었으면 다시 물어보되, 탓하지 않는다.
5. 아이를 '{nickname}'라고 부른다.
출력은 대사 한 줄뿐이다. 따옴표·설명·이름표를 붙이지 않는다."""

#: 최근 10턴만 보낸다 — 더 보내도 대화가 좋아지지 않고 지연만 늘어난다.
MAX_HISTORY_TURNS = 10


def reply(
    client: OpenAI,
    user_text: str | None,
    scenario: str,
    history: list[dict],
    nickname: str,
) -> str:
    role = _SCENARIO_ROLES.get(scenario, "다정한 선생님")
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT.format(role=role, nickname=nickname)}
    ]
    for turn in history[-MAX_HISTORY_TURNS:]:
        turn_role = turn.get("role")
        content = turn.get("content")
        if turn_role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": turn_role, "content": content})
    # 못 알아들은 경우에도 대화를 끊지 않는다 — 다시 물어보게 한다.
    messages.append({"role": "user", "content": user_text or "(아이 말을 알아듣지 못했다)"})

    response = client.chat.completions.create(
        model=settings.openai_llm_model,
        messages=messages,
        # 대화는 기다림이 곧 손해다. 한 마디를 돌려주는 데 추론이 필요하지 않다
        **reasoning("minimal"),
    )
    return (response.choices[0].message.content or "").strip()
