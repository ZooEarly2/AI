"""채점 결과의 어절이 **맞춤법 표기**로 나가는지 본다.

채점 서비스(wav2vec)는 소리 나는 대로 적은 어절을 돌려준다 — "같이" 를 "가치" 로.
그대로 통과시키면 빈칸 퀴즈의 정답이 "가치" 로 떠서, 글자를 배우는 중인 아이에게
틀린 철자를 가르치게 된다. 실제 서비스 응답으로 확인한 동작이라 회귀로 남긴다.
"""

from app.core.sentences import SENTENCES, SentenceId
from app.services.feedback_service import _pick_weakest_word, _to_spelling


def _result(sentence: str, words: list[tuple[str, float]]):
    return {
        "sentence": sentence,
        "off_script": False,
        "words": [
            {"word": w, "z": z, "warn": z < -1.5, "worst_phone": None} for w, z in words
        ],
    }


def test_g2p_words_are_restored_to_spelling():
    canonical = SENTENCES[SentenceId.ARRIVAL_2]  # "안녕! 우리 같이 놀자!"
    # 채점 서비스가 실제로 돌려준 모양 — 문장부호가 빠지고 "같이" 가 "가치" 로 온다
    result = _result(
        "안녕 우리 같이 놀자",
        [("안녕", -0.44), ("우리", 0.07), ("가치", -2.10), ("놀자", 0.27)],
    )

    sentence, words = _to_spelling(canonical, result)

    # 아이가 화면에서 본 문장 그대로여야 한다 — 문장부호까지
    assert sentence == canonical
    assert [w["word"] for w in words] == ["안녕!", "우리", "같이", "놀자!"]
    # 점수는 채점 서비스 것을 그대로 쓴다. 바뀌는 것은 표기뿐이다
    assert [w["z"] for w in words] == [-0.44, 0.07, -2.10, 0.27]


def test_falls_back_when_word_counts_differ():
    """어절 수가 다르면 자리가 어긋난다 — 그때는 채점 서비스 표기를 그대로 둔다.

    표기가 아쉬운 편이 엉뚱한 낱말을 짚는 것보다 낫다.
    """
    canonical = SENTENCES[SentenceId.ARRIVAL_2]
    result = _result("안녕 우리", [("안녕", -0.4), ("우리", 0.1)])

    sentence, words = _to_spelling(canonical, result)

    assert sentence == "안녕 우리"
    assert [w["word"] for w in words] == ["안녕", "우리"]


def _w(word: str, z: float):
    return {"word": word, "z": z, "warn": z < -1.5, "worstPhone": None}


def test_one_syllable_word_is_never_the_target():
    """한 글자짜리 어절은 짚지 않는다.

    채점기가 그 길이를 신뢰성 있게 재지 못한다. 합성음으로 만든 **완벽한 발음**을
    넣어도 "개" 가 -3.7 ~ -5.1 로 나왔다(여러 글자 어절은 같은 발화에서 0 언저리).
    짧아서 앞뒤 소리에 묻히는 탓이지 잘못 읽어서가 아니다.

    그대로 두면 수학 문장은 반드시 "개" 를 물고 있으므로, 아이가 아무리 잘 읽어도
    칭찬 화면에 갈 수 없고 빈칸은 늘 배울 것 없는 자리에 뚫린다.
    """
    words = [_w("사과가", -0.84), _w("다섯", -0.60), _w("개", -3.67), _w("있어요", 0.08)]
    # 제일 낮은 것은 "개" 지만 짚지 않는다 — 나머지가 기준을 넘었으니 잘 읽은 것이다
    assert _pick_weakest_word(words) is None


def test_one_syllable_word_does_not_shadow_a_real_weak_word():
    """한 글자를 건너뛰되, 진짜 약한 어절은 그대로 짚는다."""
    words = [_w("사과가", -2.9), _w("다섯", -0.60), _w("개", -5.0), _w("있어요", 0.08)]
    picked = _pick_weakest_word(words)
    assert picked is not None
    assert picked[1]["word"] == "사과가"
    assert picked[0] == 0


def test_punctuation_does_not_count_as_a_syllable():
    """"계세요!" 는 세 글자다. 문장부호 때문에 길이를 잘못 세면 안 된다."""
    words = [_w("선생님,", -0.15), _w("안녕히", -0.96), _w("계세요!", -2.21)]
    picked = _pick_weakest_word(words)
    assert picked is not None and picked[1]["word"] == "계세요!"
