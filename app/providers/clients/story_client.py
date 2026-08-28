"""동화 생성 — OpenAI 호출.

하루치 기록 4장면을 한 번에 넘겨 동화로 엮는다. 장면마다 따로 부르지 않는 이유는
이야기가 앞뒤로 이어져야 하기 때문이다 — 따로 만들면 같은 하루가 네 조각으로 흩어진다.

**새 사건·인물을 만들지 않는 것이 이 기능의 전제다.** 아이가 실제로 한 말과 들은 말만
가지고 쓴다. 지어낸 장면이 섞이면 아이가 "나는 그런 적 없는데"가 되고, 하루를 되돌아
보는 기록으로서의 뜻이 사라진다.
"""

from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import settings
from app.providers.clients.openai_client import reasoning
from app.core.logging import get_logger
from app.schemas.story import CATEGORY_LABELS, StoryCategory

log = get_logger(__name__)

_SYSTEM_PROMPT = """\
너는 만 5~8세 어린이를 위한 한국어 동화 작가다. 이주배경 아동이 오늘 학교에서
실제로 겪은 기록을 받아, 따뜻한 그림책 문체의 짧은 동화로 엮는다.

반드시 지킬 것:
1. 주어진 기록에 없는 사건·인물·장소를 만들지 않는다. 상상으로 채우지 않는다.
2. 아이 이름을 자연스러운 조사와 함께 쓴다 (지우가 / 지훈이가).
3. 한 장면의 narration 은 2~3문장, 모든 문장은 '-어요/-았어요/-지요/-답니다' 같은
   부드러운 종결어미로 끝낸다.
4. 쉬운 낱말만 쓴다. 한자어·추상어를 피하고, 한 문장은 25자 안팎으로 짧게 쓴다.
5. subtitle 은 4~10음절의 장면 소제목, opening 은 장면을 여는 짧은 전환구다.
6. quote 는 아이가 실제로 한 말을 그대로 옮긴다. 한 말이 없으면 null 이다.
   아이가 하지 않은 말을 quote 에 넣지 않는다.
7. 평가하거나 점수를 매기지 않는다. 잘못을 지적하지 않는다.

출력은 아래 JSON 스키마 하나뿐이다. 설명·마크다운을 덧붙이지 않는다.
{"title": "...", "scenes": [{"category": "...", "subtitle": "...", "opening": "...",
 "quote": "..." | null, "narration": "..."}]}
scenes 는 입력과 같은 개수·같은 순서·같은 category 여야 한다."""


def _scene_brief(scene: dict) -> dict:
    """LLM 에 넘길 장면 요약. 빈 값은 아예 빼서 "없다"를 분명히 한다."""
    category = scene.get("category")
    label = CATEGORY_LABELS.get(StoryCategory(category), category) if category else category
    brief: dict[str, str] = {"category": str(category), "장면": str(label)}
    if scene.get("partner_line"):
        brief["상대가_한_말"] = scene["partner_line"]
    if scene.get("child_said"):
        brief["아이가_한_말"] = scene["child_said"]
    if scene.get("poem_text"):
        # 이름이 poem_text 라고 늘 동시인 것이 아니다. 수학이면 센 것을 적어 보낸다 —
        # 라벨을 안 갈면 LLM 이 "동시를 읽었다" 는 전제로 문장을 짓는다.
        key = "아이가_센_것" if scene.get("class_subject") == "MATH" else "아이가_읽은_동시"
        brief[key] = scene["poem_text"]
    if scene.get("practiced_word"):
        brief["연습한_낱말"] = scene["practiced_word"]
    return brief


def generate_story(client: OpenAI, child_name: str, scenes: list[dict]) -> dict:
    payload = {
        "아이_이름": child_name,
        "장면들": [_scene_brief(scene) for scene in scenes],
    }
    response = client.chat.completions.create(
        model=settings.openai_llm_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        # 4장면을 한 번에 만든다. 기본 추론 강도로는 게이트웨이의 60초 제한을 넘겼다.
        # low 는 "기록에 없는 것을 쓰지 않는다" 는 제약을 지킬 만큼은 남긴다.
        **reasoning("low"),
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # response_format 이 json_object 라 정상 경로에서는 오지 않는다.
        # 그래도 앱에 깨진 화면을 보내느니 502 로 끊는 편이 낫다.
        log.warning("story JSON 파싱 실패: %s", raw[:300])
        raise ValueError("동화 응답을 해석할 수 없습니다.") from exc
