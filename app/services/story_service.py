"""동화 생성 서비스.

게이트웨이가 이미 구조를 검증해 400 으로 끊지만, 여기서도 막는다 — 게이트웨이를
거치지 않는 직접 호출이 있을 수 있고, 잘못된 입력이 LLM 호출까지 가면 60초를 기다린
끝에 이상한 동화가 나온다.
"""

from __future__ import annotations

import re

from app.core.exceptions import InvalidRequest, UpstreamUnavailable
from app.core.korean import josa
from app.core.logging import get_logger
from app.providers.base import InferenceProvider
from app.schemas.story import (
    DIALOGUE_CATEGORIES,
    STORY_ORDER,
    SceneInput,
    SceneOutput,
    StoryData,
    StoryRequest,
)

log = get_logger(__name__)

_MAX_CHILD_NAME = 20


def generate_story(provider: InferenceProvider, request: StoryRequest) -> StoryData:
    child_name = request.child_name.strip()
    if not child_name or len(child_name) > _MAX_CHILD_NAME:
        raise InvalidRequest("아이 이름이 올바르지 않습니다.", field="childName")

    _validate_scenes(request.scenes)

    # by_alias=False / mode="json" 을 명시한다. 스키마 기본값이 camelCase 직렬화라
    # 그냥 model_dump() 하면 제공자가 읽는 snake_case 키가 사라지고(partner_line →
    # partnerLine), category 도 enum 객체 그대로 남아 조회 키가 어긋난다.
    scenes = [scene.model_dump(by_alias=False, mode="json") for scene in request.scenes]
    try:
        result = provider.generate_story(child_name, scenes)
    except Exception as exc:
        log.warning("동화 생성 실패: %s", exc)
        raise UpstreamUnavailable("동화 생성 서비스에 연결할 수 없습니다.") from exc

    return StoryData(
        title=str(result.get("title") or f"{child_name}의 오늘 학교 이야기"),
        scenes=_normalise_scenes(request.scenes, result.get("scenes") or []),
    )


def _validate_scenes(scenes: list[SceneInput]) -> None:
    if len(scenes) != len(STORY_ORDER):
        raise InvalidRequest(
            "scenes는 반드시 4개(등교/수업/급식/하교)여야 합니다.", field="scenes"
        )
    for index, (scene, expected) in enumerate(zip(scenes, STORY_ORDER)):
        field = f"scenes[{index}]"
        if scene.category != expected:
            raise InvalidRequest(
                "scenes의 카테고리 또는 순서가 올바르지 않습니다. "
                "(등교→수업→급식→하교 순서 필요)",
                field=f"{field}.category",
            )
        if scene.category in DIALOGUE_CATEGORIES:
            # 상대방 대사가 없으면 LLM 이 지어내야 한다. 실제 기록만으로 쓰는 것이
            # 이 기능의 전제라, 지어내게 두느니 요청을 끊는다.
            if not (scene.partner_line or "").strip():
                raise InvalidRequest(
                    "상대방 대사가 비어 있는 장면이 있습니다.", field=f"{field}.partnerLine"
                )
        elif not (scene.poem_text or "").strip():
            raise InvalidRequest(
                "읽은 동시가 비어 있는 장면이 있습니다.", field=f"{field}.poemText"
            )


#: 문장이 끝났다고 볼 수 있는 부호.
_SENTENCE_END = (".", "!", "?", "…", ".", "!", "?", "~")


def _closed(text: str) -> str:
    """문장을 끝맺어 돌려준다.

    화면은 ``{opening} {narration}`` 으로 둘을 한 줄에 이어 붙인다. opening 이
    "급식실이에요" 처럼 부호 없이 끝나면 "급식실이에요 급식 선생님께서…" 가 되어
    한 문장처럼 읽힌다. 부호를 LLM 에게 맡기면 들쭉날쭉해서 여기서 못 박는다.
    """
    text = text.strip()
    if not text or text.endswith(_SENTENCE_END):
        return text
    # 따옴표로 닫힌 경우(…했어요") 는 그 안쪽을 보고 판단한다
    if text[-1] in "\"'”’」』" and len(text) > 1 and text[-2] in _SENTENCE_END:
        return text
    return text + "."


#: 일본어 가나. 한국어 동화에 한 글자도 있어서는 안 된다.
_KANA = re.compile(r"[぀-ヿ]")


def _is_korean(text: str) -> bool:
    """한국어 문장인가.

    LLM 이 드물게 조사를 일본어로 낸다 — "「파도」を 읽었어요"(6번 중 2번 실측).
    한 글자 차이라 눈으로는 잘 안 잡히는데, 이 글은 한국어를 배우는 아이가 읽는
    글이라 틀린 조사가 섞이면 안 된다. 프롬프트로도 막지만 여기서 한 번 더 본다.
    """
    return not _KANA.search(text or "")


def _normalise_scenes(inputs: list[SceneInput], raw_scenes: list) -> list[SceneOutput]:
    """LLM 응답을 요청과 같은 개수·순서·카테고리로 맞춘다.

    장면이 모자라거나 순서가 섞여 오면 앱이 어느 그림을 얹을지 정할 수 없다.
    요청 순서를 기준으로 자리를 맞추고, 빠진 자리는 기록으로 채운다 — 화면에 빈
    장면을 보여주느니 담백한 문장이라도 채우는 편이 낫다.
    """
    by_category: dict[str, dict] = {}
    for raw in raw_scenes:
        if isinstance(raw, dict) and raw.get("category"):
            by_category.setdefault(str(raw["category"]), raw)

    scenes: list[SceneOutput] = []
    for scene_input in inputs:
        raw = by_category.get(scene_input.category.value, {})
        narration = str(raw.get("narration") or "").strip()
        if not narration or not _is_korean(narration):
            # 가나가 섞인 문장은 통째로 버린다. 그 글자만 지우면 조사가 사라져
            # "「파도」 읽었어요" 같은 비문이 남는다 — 기록으로 다시 쓰는 편이 낫다.
            if narration:
                log.warning("동화 문장에 한글이 아닌 글자가 섞여 되돌린다: %s", narration[:80])
            narration = _fallback_narration(scene_input)
        scenes.append(
            SceneOutput(
                category=scene_input.category,
                subtitle=str(raw.get("subtitle") or "오늘의 한 장면").strip(),
                # 소제목은 부호를 안 붙인다 — 제목이라 마침표가 없는 편이 맞다.
                # 여는 말은 뒤에 narration 이 바로 이어 붙으므로 반드시 끝맺는다.
                opening=_closed(
                    str(raw.get("opening") or "그때였어요")
                    if _is_korean(str(raw.get("opening") or ""))
                    else "그때였어요"
                ),
                # 인용은 아이가 실제로 한 말만 쓴다. LLM 이 다른 말을 넣어도 무시한다 —
                # 아이가 하지 않은 말이 동화에 실리면 안 된다.
                quote=(scene_input.child_said or "").strip() or None,
                narration=narration,
                # 앱이 삽화를 고를 때 쓴다. LLM 이 정하는 값이 아니라 요청에 담겨
                # 온 사실이므로 입력에서 그대로 옮긴다.
                class_subject=scene_input.class_subject,
            )
        )
    return scenes


def _fallback_narration(scene: SceneInput) -> str:
    if (scene.poem_text or "").strip() or (scene.poem_title or "").strip():
        if scene.class_subject == "MATH":
            return f"수학책을 펴고 과일을 세었어요. 「{scene.poem_text.strip()}」"
        # 제목을 알면 제목만 부른다. 시 전문을 옮기면 한 장이 시로만 가득 찬다.
        title = (scene.poem_title or "").strip()
        word = (scene.practiced_word or "").strip()
        if title:
            said = f" 「{word}」 를 또박또박 읽었어요." if word else ""
            return f"「{title}」 라는 동시를 읽었어요.{said}"
        return f"동시를 또박또박 읽었어요. 「{scene.poem_text.strip()}」"
    partner = (scene.partner_line or "").strip()
    said = (scene.child_said or "").strip()
    # 누가 한 말인지 알면 이름을 부른다. 모르면 사람을 지어내지 않고 말만 적는다.
    # 받침에 따라 조사가 갈린다 — "급식 선생님이" 지만 "호랑이 친구가" 다
    who = (scene.partner_name or "").strip()
    lead = (
        f"{josa(who, '이', '가')} 「{partner}」 하고 말했어요."
        if who
        else f"「{partner}」 하는 말이 들렸어요."
    )
    if said:
        return f"{lead} 그래서 「{said}」 하고 대답했어요."
    return f"{lead} 가만히 귀를 기울였어요."
