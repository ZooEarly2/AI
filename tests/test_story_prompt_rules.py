"""동화 프롬프트가 **꼭 지켜야 하는 세 가지**를 아직 담고 있는지 본다.

프롬프트에서 규칙 한 줄이 빠져도 서버는 200 을 그대로 내보낸다. 동화는 여전히
그럴듯하게 읽히고, 무너진 것은 다음 셋뿐이라 눈으로는 안 잡힌다. 실제로 셋 다
현장에서 나온 문제다 — 고치기 전 옛 프롬프트를 12번 돌려 센 값을 함께 적어 둔다.

1. **읽은 동시가 동화에 안 실린다** (12번 중 5번). "동시를 읽었어요" 로만 적고
   넘어가면, 동화책을 다시 펼친 아이는 그날 무슨 시를 읽었는지 알 수 없다.
   국어 시간 장면에서 그것 말고 적을 내용이 없다.
2. **하교 장면 opening 이 "수업이 끝났어요" 가 된다** (12번 중 6번). 화면은
   opening 과 narration 을 한 문단으로 이어 붙이므로(StoryBook.tsx 의
   ``{opening} {narration}``), "수업 끝나고 수업이 끝났어요" 처럼 읽힌다.
3. **기록에 없는 행동을 지어낸다** (12번 중 5번 — "가방을 메고", "정리했어요").
   기록에 있는 것은 들은 말과 한 말뿐이다. 지어내기 시작하면 이 동화가 아이의
   하루 기록이라는 전제가 무너진다.

규칙을 넣은 뒤 같은 조건으로 12번을 다시 돌린 결과는 12/12 · 0 · 0 이었다.
여기서 보는 것은 문구가 아니라 **그 규칙이 아직 프롬프트에 있는가** 다.
"""

from app.providers.clients.story_client import _SYSTEM_PROMPT, _scene_brief


def test_prompt_requires_quoting_the_poem():
    """읽은 동시를 그대로 옮기라고 시켜야 한다."""
    assert "아이가_읽은_동시" in _SYSTEM_PROMPT
    # "그대로 옮겨 적는다" 는 지시 자체를 본다. 「 」 만 세면 규칙 9 의 다른 문장에도
    # 그 기호가 있어서, 지시를 "언급한다" 로 흐려 놔도 통과해 버린다(실측).
    assert "그대로 옮겨 적는다" in _SYSTEM_PROMPT
    # "동시를 읽었어요" 로만 적고 넘어가지 말라는 금지가 있어야 한다.
    assert "동시를 읽었어요" in _SYSTEM_PROMPT


def test_prompt_warns_that_opening_and_narration_are_joined():
    """둘이 한 문단으로 붙는다는 사실을 알려야 되풀이를 피한다."""
    assert "한 문단" in _SYSTEM_PROMPT
    # 실제로 나왔던 나쁜 예가 들어 있어야 한다 — 추상적인 금지만으로는 안 고쳐졌다.
    assert "수업이 끝났어요" in _SYSTEM_PROMPT


def test_prompt_forbids_inventing_plausible_filler():
    """'하교니까 가방을 멨겠지' 를 막아야 한다."""
    assert "가방을" in _SYSTEM_PROMPT
    assert "짧게 끝낸다" in _SYSTEM_PROMPT


def test_class_scene_is_labelled_by_subject():
    """국어와 수학은 다른 이름으로 넘어가야 한다.

    같은 poem_text 자리에 수학이 오는데, 라벨을 안 갈면 과일을 센 아이에게
    "동시를 읽었다" 는 동화가 나간다.
    """
    korean = _scene_brief(
        {"category": "class", "poem_text": "파도가 와요", "class_subject": "KOREAN"}
    )
    maths = _scene_brief(
        {"category": "class", "poem_text": "사과를 세 개 세었어요", "class_subject": "MATH"}
    )
    assert "아이가_읽은_동시" in korean
    assert "아이가_센_것" in maths
    # 프롬프트가 두 이름을 모두 알고 있어야 규칙이 걸린다.
    assert "아이가_센_것" in _SYSTEM_PROMPT
