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
   특히 장면 이름만 보고 "그럴 법한 일" 을 지어 넣지 않는다 — 하교라고 해서
   "수업을 마치고 정리했어요", "가방을 메고 교문을 나섰어요" 를 쓰면 안 된다.
   기록에 있는 것은 들은 말과 한 말뿐이고, 그 둘만으로 장면을 이룬다.
   쓸 말이 모자라면 문장을 늘리지 말고 2문장으로 짧게 끝낸다.
2. 아이 이름을 자연스러운 조사와 함께 쓴다 (지우가 / 지훈이가).
3. 한 장면의 narration 은 2~3문장, 모든 문장은 '-어요/-았어요/-지요/-답니다' 같은
   부드러운 종결어미로 끝낸다.
4. 쉬운 낱말만 쓴다. 한자어·추상어를 피하고, 한 문장은 25자 안팎으로 짧게 쓴다.
5. subtitle 은 4~10음절의 장면 소제목, opening 은 장면을 여는 짧은 전환구다.
   **opening 과 narration 은 화면에서 한 문단으로 이어 붙어 나온다.** 그러니 같은
   사실을 두 번 말하지 않는다. opening 이 "수업이 끝났어요" 인데 narration 을
   "수업을 마치고 정리했어요" 로 시작하면, 아이는 "수업이 끝났어요 수업을 마치고
   정리했어요" 를 읽게 된다. opening 은 때나 자리만 짧게 짚고(예: "해가 기울어요"),
   narration 은 그 말을 되풀이하지 말고 곧바로 그날 있었던 일로 들어간다.
6. quote 는 아이가 실제로 한 말을 그대로 옮긴다. 한 말이 없으면 null 이다.
   아이가 하지 않은 말을 quote 에 넣지 않는다.
7. 평가하거나 점수를 매기지 않는다. 잘못을 지적하지 않는다.
8. 상대가_누구인가 가 있으면 **그 이름을 그대로 부른다** — "급식 선생님이",
   "호랑이 친구가" 처럼. "다른 사람이" 나 "누군가" 로 뭉뚱그리지 않는다.
   어른(선생님·아주머니)에게는 높임을 쓴다: "선생님께서 ~라고 말씀하셨어요".
   또래 친구에게는 쓰지 않는다. 이름이 없으면 그 사람을 아예 언급하지 않고
   들린 말만 적는다 — 없는 인물을 지어내는 것보다 낫다.
9. 수업 장면은 **무엇을 했는지 짧게 짚는다. 시를 통째로 옮기지 않는다.**
   · 읽은_시_제목 이 있으면 그 제목을 「 」 안에 넣는다 — 「파도」를 읽었어요.
   · 연습한_낱말 이 있으면 그 낱말 하나만 따옴표로 덧붙인다 —
     '만져요' 를 또박또박 읽었어요.
   · 제목을 모르면 "동시를 읽었어요" 로 두고, 시 본문을 옮겨 적지 않는다.
   아이가_센_것 이 있으면 무엇을 몇 개 세었는지 한 문장으로 적는다.

10. **한글로만 쓴다.** 일본어 가나(を·の·は)나 한자를 한 글자도 섞지 않는다.
    조사는 한국어 조사다 — "「파도」를 읽었어요" 이지 "「파도」を 읽었어요" 가 아니다.

출력은 아래 JSON 스키마 하나뿐이다. 설명·마크다운을 덧붙이지 않는다.
{"title": "...", "scenes": [{"category": "...", "subtitle": "...", "opening": "...",
 "quote": "..." | null, "narration": "..."}]}
scenes 는 입력과 같은 개수·같은 순서·같은 category 여야 한다."""


def _scene_brief(scene: dict) -> dict:
    """LLM 에 넘길 장면 요약. 빈 값은 아예 빼서 "없다"를 분명히 한다."""
    category = scene.get("category")
    label = CATEGORY_LABELS.get(StoryCategory(category), category) if category else category
    brief: dict[str, str] = {"category": str(category), "장면": str(label)}
    if scene.get("partner_name"):
        brief["상대가_누구인가"] = scene["partner_name"]
    if scene.get("partner_line"):
        brief["상대가_한_말"] = scene["partner_line"]
    if scene.get("child_said"):
        brief["아이가_한_말"] = scene["child_said"]
    is_math = scene.get("class_subject") == "MATH"
    title = (scene.get("poem_title") or "").strip()
    if title and not is_math:
        # 제목을 알면 **본문은 아예 안 넘긴다.** 넘기면 동화가 시를 통째로 옮겨 적어
        # 네 줄짜리 시가 한 장을 다 먹는다. 안 주면 옮길 수가 없다 —
        # 프롬프트로 부탁하는 것보다 확실하다.
        brief["읽은_시_제목"] = title
    elif scene.get("poem_text"):
        # 이름이 poem_text 라고 늘 동시인 것이 아니다. 수학이면 센 것을 적어 보낸다 —
        # 라벨을 안 갈면 LLM 이 "동시를 읽었다" 는 전제로 문장을 짓는다.
        key = "아이가_센_것" if is_math else "아이가_읽은_동시"
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
