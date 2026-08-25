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


def category_of(sentence_id: SentenceId) -> str:
    """id 접두어(arrival/lunch/departure)를 카테고리로 쓴다."""
    return sentence_id.value.rsplit("_", 1)[0]
