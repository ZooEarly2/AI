"""채점 결과의 어절이 **맞춤법 표기**로 나가는지 본다.

채점 서비스(wav2vec)는 소리 나는 대로 적은 어절을 돌려준다 — "같이" 를 "가치" 로.
그대로 통과시키면 빈칸 퀴즈의 정답이 "가치" 로 떠서, 글자를 배우는 중인 아이에게
틀린 철자를 가르치게 된다. 실제 서비스 응답으로 확인한 동작이라 회귀로 남긴다.
"""

from app.core.sentences import SENTENCES, SentenceId
from app.services.feedback_service import _to_spelling


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
