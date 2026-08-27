from enum import Enum


class SentenceId(str, Enum):
    """추천 문장의 고정 식별자. 클라이언트는 이 id만 보내면 되고, 실제 문장 텍스트는
    이 서버가 단일 소스로 갖는다.

    카테고리는 두 가지 성격이 섞여 있다:
    - 등교(arrival)/점심(lunch)/하교(departure): 3개 중 1개를 "골라" 읽는 표현 선택형, 카테고리당 3개.
    - 학습(study): 정해진 동시(童詩) 한 편을 그대로 "같이" 읽는 동시 낭독형. 선택지가 아니라
      카테고리 자체가 콘텐츠라 지금은 1개뿐이다.
    """

    ARRIVAL_1 = "arrival_1"
    ARRIVAL_2 = "arrival_2"
    ARRIVAL_3 = "arrival_3"
    STUDY_1 = "study_1"
    LUNCH_1 = "lunch_1"
    LUNCH_2 = "lunch_2"
    LUNCH_3 = "lunch_3"
    DEPARTURE_1 = "departure_1"
    DEPARTURE_2 = "departure_2"
    DEPARTURE_3 = "departure_3"


SENTENCES: dict[SentenceId, str] = {
    SentenceId.ARRIVAL_1: "안녕 나도 만나서 반가워 !",
    SentenceId.ARRIVAL_2: "안녕! 우리 같이 놀자!",
    SentenceId.ARRIVAL_3: "안녕! 같이 들어가자!",
    SentenceId.STUDY_1: "노란 꽃이 피었어요. 예쁜 꽃이 피었어요. 바람이 살랑살랑 꽃이 웃어요.",
    SentenceId.LUNCH_1: "조금만 주세요.",
    SentenceId.LUNCH_2: "적당히 주세요.",
    SentenceId.LUNCH_3: "많이 주세요.",
    SentenceId.DEPARTURE_1: "선생님, 안녕히 가세요!",
    SentenceId.DEPARTURE_2: "선생님, 감사합니다!",
    SentenceId.DEPARTURE_3: "내일 또 뵙겠습니다!",
}


#: 연습 문장의 모국어 번역.
#:
#: 표현 퀴즈의 힌트(전구)가 이 값을 그대로 띄운다. **문장이 고정 10개라 매번 LLM 에
#: 물어볼 이유가 없다** — 물어보면 아이가 전구를 누르고 몇 초를 기다려야 하고, 같은
#: 문장을 몇 번이고 다시 번역하며 돈을 쓴다.
#:
#: 사람이 다듬은 문장이라는 점이 중요하다. 아이가 "이 말이 무슨 뜻이지?" 하고 누르는
#: 자리라, 기계 번역의 어색한 문장보다 또박또박한 한 줄이 낫다.
#:
#: 문장을 고치면 **이 표도 같이 고쳐야 한다.** 같은 파일에 나란히 둔 이유다.
SENTENCE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "안녕 나도 만나서 반가워 !": {
        "vi": "Chào cậu! Mình cũng rất vui được gặp cậu!",
        "zh": "你好！我也很高兴见到你！",
    },
    "안녕! 우리 같이 놀자!": {
        "vi": "Chào cậu! Chúng mình cùng chơi nhé!",
        "zh": "你好！我们一起玩吧！",
    },
    "안녕! 같이 들어가자!": {
        "vi": "Chào cậu! Cùng vào lớp nào!",
        "zh": "你好！我们一起进去吧！",
    },
    "노란 꽃이 피었어요. 예쁜 꽃이 피었어요. 바람이 살랑살랑 꽃이 웃어요.": {
        "vi": "Hoa vàng đã nở. Hoa xinh đã nở. Gió thổi hiu hiu, hoa mỉm cười.",
        "zh": "黄色的花开了。漂亮的花开了。风儿轻轻吹，花儿笑了。",
    },
    "조금만 주세요.": {"vi": "Cho con một chút thôi ạ.", "zh": "请给我一点点。"},
    "적당히 주세요.": {"vi": "Cho con vừa đủ ạ.", "zh": "请给我适量。"},
    "많이 주세요.": {"vi": "Cho con nhiều một chút ạ.", "zh": "请给我多一点。"},
    "선생님, 안녕히 가세요!": {"vi": "Thưa cô, cô về ạ!", "zh": "老师，再见！"},
    "선생님, 감사합니다!": {"vi": "Em cảm ơn cô ạ!", "zh": "老师，谢谢您！"},
    "내일 또 뵙겠습니다!": {"vi": "Ngày mai em lại gặp cô ạ!", "zh": "明天见！"},
    # 상대 캐릭터 대사 — 대화 장면에서도 뜻을 물어볼 수 있다
    "안녕! 만나서 반가워.": {
        "vi": "Chào cậu! Rất vui được gặp cậu.",
        "zh": "你好！很高兴见到你。",
    },
    "불고기 많이 줄까?": {"vi": "Cho con nhiều thịt nướng nhé?", "zh": "要给你多一点烤肉吗？"},
    "이제 집에 갈 시간이에요 !": {"vi": "Đến giờ về nhà rồi!", "zh": "到回家的时间了！"},
}


def translations_of(text: str) -> dict[str, str]:
    """그 문장의 번역들. 없으면 빈 표 — 지어낸 번역을 아이에게 보여주지 않는다."""
    return SENTENCE_TRANSLATIONS.get(text.strip(), {})


def category_of(sentence_id: SentenceId) -> str:
    """id 접두어(arrival/lunch/departure)를 카테고리로 쓴다."""
    return sentence_id.value.rsplit("_", 1)[0]
