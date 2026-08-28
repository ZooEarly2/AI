"""동화 생성 서비스.

게이트웨이가 이미 구조를 검증해 400 으로 끊지만, 여기서도 막는다 — 게이트웨이를
거치지 않는 직접 호출이 있을 수 있고, 잘못된 입력이 LLM 호출까지 가면 60초를 기다린
끝에 이상한 동화가 나온다.
"""

from __future__ import annotations

from app.core.exceptions import InvalidRequest, UpstreamUnavailable
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
        if not narration:
            narration = _fallback_narration(scene_input)
        scenes.append(
            SceneOutput(
                category=scene_input.category,
                subtitle=str(raw.get("subtitle") or "오늘의 한 장면").strip(),
                opening=str(raw.get("opening") or "그때였어요").strip(),
                # 인용은 아이가 실제로 한 말만 쓴다. LLM 이 다른 말을 넣어도 무시한다 —
                # 아이가 하지 않은 말이 동화에 실리면 안 된다.
                quote=(scene_input.child_said or "").strip() or None,
                narration=narration,
            )
        )
    return scenes


def _fallback_narration(scene: SceneInput) -> str:
    if (scene.poem_text or "").strip():
        text = scene.poem_text.strip()
        if scene.class_subject == "MATH":
            return f"수학책을 펴고 과일을 세었어요. 「{text}」"
        return f"동시를 또박또박 읽었어요. 「{text}」"
    partner = (scene.partner_line or "").strip()
    said = (scene.child_said or "").strip()
    if said:
        return f"「{partner}」 하는 말에 「{said}」 하고 대답했어요."
    return f"「{partner}」 하는 말을 가만히 들었어요."
