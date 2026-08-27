from enum import Enum


class SentenceId(str, Enum):
    """추천 문장의 고정 식별자. 클라이언트는 이 id만 보내면 되고, 실제 문장 텍스트는
    이 서버가 단일 소스로 갖는다.

    카테고리는 두 가지 성격이 섞여 있다:
    - 등교(arrival)/점심(lunch)/하교(departure): 여럿 중 1개를 "골라" 읽는 표현 선택형.
      개수는 카테고리마다 다르다(등교 9 · 급식 3 · 하교 6) — 앱은 그중 무작위로 3개만
      화면에 띄운다. 그래서 여기 문장은 **어느 셋이 함께 떠도 말이 되어야** 한다.
    - 학습(study): 동시(童詩) 한 편을 그대로 "같이" 읽는 동시 낭독형. 앞의 셋과 성격이
      다르다 — 아이가 고르는 것이 아니라 앱이 회차마다 세 편 중 하나를 뽑아 보여준다.
      그래서 한 항목이 문장 하나가 아니라 시 한 편 전체다(여러 줄이 이어져 있다).
    """

    ARRIVAL_1 = "arrival_1"
    ARRIVAL_2 = "arrival_2"
    ARRIVAL_3 = "arrival_3"
    ARRIVAL_4 = "arrival_4"
    ARRIVAL_5 = "arrival_5"
    ARRIVAL_6 = "arrival_6"
    ARRIVAL_7 = "arrival_7"
    ARRIVAL_8 = "arrival_8"
    ARRIVAL_9 = "arrival_9"
    STUDY_1 = "study_1"
    STUDY_2 = "study_2"
    STUDY_3 = "study_3"
    STUDY_4 = "study_4"
    LUNCH_1 = "lunch_1"
    LUNCH_2 = "lunch_2"
    LUNCH_3 = "lunch_3"
    DEPARTURE_1 = "departure_1"
    DEPARTURE_2 = "departure_2"
    DEPARTURE_3 = "departure_3"
    DEPARTURE_4 = "departure_4"
    DEPARTURE_5 = "departure_5"
    DEPARTURE_6 = "departure_6"


SENTENCES: dict[SentenceId, str] = {
    SentenceId.ARRIVAL_1: "안녕 나도 만나서 반가워 !",
    SentenceId.ARRIVAL_2: "안녕! 우리 같이 놀자!",
    SentenceId.ARRIVAL_3: "안녕! 같이 들어가자!",
    SentenceId.ARRIVAL_4: "안녕! 나도 반가워.",
    SentenceId.ARRIVAL_5: "안녕! 네 이름은 뭐야?",
    SentenceId.ARRIVAL_6: "안녕! 우리 친구 하자!",
    SentenceId.ARRIVAL_7: "안녕! 나 오늘 처음 왔어.",
    SentenceId.ARRIVAL_8: "안녕! 같이 가자!",
    SentenceId.ARRIVAL_9: "안녕! 만나서 나도 기뻐!",
    SentenceId.STUDY_1: "노란 꽃이 피었어요. 예쁜 꽃이 피었어요. 바람이 살랑살랑 꽃이 웃어요.",
    SentenceId.STUDY_2: "눈이 와요, 눈이 와요. 하얀 눈이 펑펑 와요. 우리 같이 눈사람 만들어요.",
    SentenceId.STUDY_3: "파도가 와요, 철썩. 내 발을 만져요. 내가 뒤로 가면 파도도 따라와요.",
    SentenceId.STUDY_4: (
        "내 몸에 불덩이가 들어왔다. 뜨끈뜨끈. "
        "불덩이를 따라 몹시 추운 사람도 들어왔다. 오들오들."
    ),
    SentenceId.LUNCH_1: "조금만 주세요.",
    SentenceId.LUNCH_2: "적당히 주세요.",
    SentenceId.LUNCH_3: "많이 주세요.",
    # 남아 계신 선생님께 아이가 하는 인사라 "가세요" 가 아니라 "계세요" 다.
    # 떠나는 쪽이 아이이므로 선생님이 "가시는" 게 아니다.
    SentenceId.DEPARTURE_1: "선생님, 안녕히 계세요!",
    SentenceId.DEPARTURE_2: "선생님, 감사합니다!",
    SentenceId.DEPARTURE_3: "내일 또 뵙겠습니다!",
    SentenceId.DEPARTURE_4: "오늘 정말 재미있었어요!",
    SentenceId.DEPARTURE_5: "내일 또 올게요!",
    SentenceId.DEPARTURE_6: "네, 조심해서 갈게요!",
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
    "안녕! 나도 반가워.": {"vi": "Chào cậu! Mình cũng vui lắm.", "zh": "你好！我也很高兴。"},
    "안녕! 네 이름은 뭐야?": {"vi": "Chào cậu! Cậu tên là gì?", "zh": "你好！你叫什么名字？"},
    "안녕! 우리 친구 하자!": {
        "vi": "Chào cậu! Chúng mình làm bạn nhé!",
        "zh": "你好！我们做朋友吧！",
    },
    "안녕! 나 오늘 처음 왔어.": {
        "vi": "Chào cậu! Hôm nay là ngày đầu tiên mình đến đây.",
        "zh": "你好！我今天第一次来。",
    },
    "안녕! 같이 가자!": {"vi": "Chào cậu! Cùng đi nào!", "zh": "你好！我们一起走吧！"},
    "안녕! 만나서 나도 기뻐!": {
        "vi": "Chào cậu! Mình cũng rất vui khi được gặp cậu!",
        "zh": "你好！我也很开心见到你！",
    },
    "노란 꽃이 피었어요. 예쁜 꽃이 피었어요. 바람이 살랑살랑 꽃이 웃어요.": {
        "vi": "Hoa vàng đã nở. Hoa xinh đã nở. Gió thổi hiu hiu, hoa mỉm cười.",
        "zh": "黄色的花开了。漂亮的花开了。风儿轻轻吹，花儿笑了。",
    },
    "눈이 와요, 눈이 와요. 하얀 눈이 펑펑 와요. 우리 같이 눈사람 만들어요.": {
        "vi": "Tuyết rơi rồi, tuyết rơi rồi. Tuyết trắng rơi lất phất. Chúng mình cùng nặn người tuyết nhé.",
        "zh": "下雪了，下雪了。白白的雪纷纷落下。我们一起堆雪人吧。",
    },
    "파도가 와요, 철썩. 내 발을 만져요. 내가 뒤로 가면 파도도 따라와요.": {
        "vi": "Sóng đến rồi, ào ào. Sóng chạm vào chân mình. Mình lùi lại thì sóng cũng theo sau.",
        "zh": "波浪来了，哗啦。它碰到我的脚。我往后退，波浪也跟过来。",
    },
    "내 몸에 불덩이가 들어왔다. 뜨끈뜨끈. 불덩이를 따라 몹시 추운 사람도 들어왔다. 오들오들.": {
        "vi": (
            "Trong người mình có một cục lửa. Nóng hổi nóng hổi. "
            "Theo cục lửa, một người rất lạnh cũng đi vào. Run rẩy run rẩy."
        ),
        "zh": "我身体里进来了一个火球。热乎乎的。跟着火球，一个很冷的人也进来了。冷得发抖。",
    },
    "조금만 주세요.": {"vi": "Cho con một chút thôi ạ.", "zh": "请给我一点点。"},
    "적당히 주세요.": {"vi": "Cho con vừa đủ ạ.", "zh": "请给我适量。"},
    "많이 주세요.": {"vi": "Cho con nhiều một chút ạ.", "zh": "请给我多一点。"},
    # 베트남어에서는 누가 가는지가 낱말로 드러난다. "계세요" 는 아이가 가고 선생님이
    # 남는 것이라 cô về(선생님이 가심)가 아니라 em về(제가 갑니다)여야 한다 —
    # 한국어를 계세요로 고치면서 여기를 안 고치면 뜻이 반대로 남는다.
    "선생님, 안녕히 계세요!": {"vi": "Thưa cô, em về ạ!", "zh": "老师，再见！"},
    "선생님, 감사합니다!": {"vi": "Em cảm ơn cô ạ!", "zh": "老师，谢谢您！"},
    "내일 또 뵙겠습니다!": {"vi": "Ngày mai em lại gặp cô ạ!", "zh": "明天见！"},
    "오늘 정말 재미있었어요!": {"vi": "Hôm nay vui thật ạ!", "zh": "今天真的很有意思！"},
    "내일 또 올게요!": {"vi": "Mai em lại đến ạ!", "zh": "我明天还会来！"},
    "네, 조심해서 갈게요!": {"vi": "Vâng, em sẽ đi cẩn thận ạ!", "zh": "好的，我会小心回家的！"},
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


#: 번역문의 어느 부분이 한국어 어느 어절인지.
#:
#: 표현 퀴즈는 한국어 문장에서 **어절 하나만 빈칸**으로 비운다. 그때 아이가 전구를
#: 누르면 모국어 뜻이 뜨는데, 뜻만 통째로 보여주면 "그래서 빈칸이 어느 말이냐" 가
#: 그대로 남는다. 그 자리를 짚어주려면 어절과 번역문 조각을 이어 둬야 한다.
#:
#: **조각은 번역문을 읽는 순서대로 늘어놓는다. 한국어 순서가 아니다.**
#: 어순이 다르면 인덱스가 뒤죽박죽이 되는 게 정상이다 —
#: "조금만(0) 주세요(1)" 는 베트남어로 "Cho con(1) một chút thôi ạ.(0)" 이다.
#:
#: 한 조각이 어절 **여럿**을 덮을 수 있다. "안녕히 계세요" 처럼 굳은 인사는
#: 베트남어에서 "em về ạ!" 한 덩어리라 억지로 쪼개면 뜻이 어긋난다.
#: 반대로 대응하는 어절이 없는 조각(순수 문법 요소)은 빈 목록이다.
#:
#: 동시(study)에는 없다 — 시는 고르는 것이 아니라 통째로 읽는 것이라 빈칸이 없다.
SENTENCE_TRANSLATION_PARTS: dict[SentenceId, dict[str, list[tuple[str, list[int]]]]] = {
    SentenceId.ARRIVAL_1: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Mình cũng", [1]),
            ("rất vui", [3]),
            ("được gặp cậu!", [2, 4]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我也", [1]),
            ("很高兴", [3]),
            ("见到你！", [2, 4]),
        ],
    },
    SentenceId.ARRIVAL_2: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Chúng mình", [1]),
            ("cùng", [2]),
            ("chơi nhé!", [3]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我们", [1]),
            ("一起", [2]),
            ("玩吧！", [3]),
        ],
    },
    SentenceId.ARRIVAL_3: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Cùng", [1]),
            ("vào lớp nào!", [2]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我们一起", [1]),
            ("进去吧！", [2]),
        ],
    },
    SentenceId.ARRIVAL_4: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Mình cũng", [1]),
            ("vui lắm.", [2]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我也", [1]),
            ("很高兴。", [2]),
        ],
    },
    SentenceId.ARRIVAL_5: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Cậu", [1]),
            ("tên", [2]),
            ("là gì?", [3]),
        ],
        "zh": [
            ("你好！", [0]),
            ("你", [1]),
            ("叫什么", [3]),
            ("名字？", [2]),
        ],
    },
    SentenceId.ARRIVAL_6: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Chúng mình", [1]),
            ("làm", [3]),
            ("bạn nhé!", [2]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我们", [1]),
            ("做", [3]),
            ("朋友吧！", [2]),
        ],
    },
    SentenceId.ARRIVAL_7: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Hôm nay", [2]),
            ("là ngày đầu tiên", [3]),
            ("mình", [1]),
            ("đến đây.", [4]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我", [1]),
            ("今天", [2]),
            ("第一次", [3]),
            ("来。", [4]),
        ],
    },
    SentenceId.ARRIVAL_8: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Cùng", [1]),
            ("đi nào!", [2]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我们一起", [1]),
            ("走吧！", [2]),
        ],
    },
    SentenceId.ARRIVAL_9: {
        "vi": [
            ("Chào cậu!", [0]),
            ("Mình cũng", [2]),
            ("rất vui", [3]),
            ("khi được gặp cậu!", [1]),
        ],
        "zh": [
            ("你好！", [0]),
            ("我也", [2]),
            ("很开心", [3]),
            ("见到你！", [1]),
        ],
    },
    SentenceId.LUNCH_1: {
        "vi": [
            ("Cho con", [1]),
            ("một chút thôi ạ.", [0]),
        ],
        "zh": [
            ("请给我", [1]),
            ("一点点。", [0]),
        ],
    },
    SentenceId.LUNCH_2: {
        "vi": [
            ("Cho con", [1]),
            ("vừa đủ ạ.", [0]),
        ],
        "zh": [
            ("请给我", [1]),
            ("适量。", [0]),
        ],
    },
    SentenceId.LUNCH_3: {
        "vi": [
            ("Cho con", [1]),
            ("nhiều một chút ạ.", [0]),
        ],
        "zh": [
            ("请给我", [1]),
            ("多一点。", [0]),
        ],
    },
    SentenceId.DEPARTURE_1: {
        "vi": [
            ("Thưa cô,", [0]),
            ("em về ạ!", [1, 2]),
        ],
        "zh": [
            ("老师，", [0]),
            ("再见！", [1, 2]),
        ],
    },
    SentenceId.DEPARTURE_2: {
        "vi": [
            ("Em cảm ơn", [1]),
            ("cô ạ!", [0]),
        ],
        "zh": [
            ("老师，", [0]),
            ("谢谢您！", [1]),
        ],
    },
    SentenceId.DEPARTURE_3: {
        "vi": [
            ("Ngày mai", [0]),
            ("em lại", [1]),
            ("gặp cô ạ!", [2]),
        ],
        "zh": [
            ("明天", [0]),
            ("见！", [1, 2]),
        ],
    },
    SentenceId.DEPARTURE_4: {
        "vi": [
            ("Hôm nay", [0]),
            ("vui", [2]),
            ("thật ạ!", [1]),
        ],
        "zh": [
            ("今天", [0]),
            ("真的", [1]),
            ("很有意思！", [2]),
        ],
    },
    SentenceId.DEPARTURE_5: {
        "vi": [
            ("Mai", [0]),
            ("em lại", [1]),
            ("đến ạ!", [2]),
        ],
        "zh": [
            ("我", []),
            ("明天", [0]),
            ("还", [1]),
            ("会来！", [2]),
        ],
    },
    SentenceId.DEPARTURE_6: {
        "vi": [
            ("Vâng,", [0]),
            ("em sẽ đi", [2]),
            ("cẩn thận ạ!", [1]),
        ],
        "zh": [
            ("好的，", [0]),
            ("我会", []),
            ("小心", [1]),
            ("回家的！", [2]),
        ],
    },
}

#: 조각을 잇는 문자. 중국어는 띄어쓰기가 없다.
_JOINER = {"vi": " ", "zh": ""}


def translation_parts_of(sentence_id: SentenceId) -> dict[str, list[dict[str, object]]]:
    """이 문장의 번역 조각. 대응표가 없으면 빈 dict."""
    parts = SENTENCE_TRANSLATION_PARTS.get(sentence_id)
    if not parts:
        return {}
    return {lang: [{"t": t, "k": list(ks)} for t, ks in items] for lang, items in parts.items()}


def _assert_parts_join_to_translations() -> None:
    """조각을 이으면 번역문과 **글자 하나까지** 같아야 한다.

    두 표를 따로 들고 있으니 한쪽만 고치는 사고가 난다. 그때 화면에는 뜻이 조금씩
    다른 두 문장이 상황에 따라 번갈아 뜨는데, 눈으로는 좀처럼 안 잡힌다.
    수입 시점에 터뜨려 배포 전에 잡는다.
    """
    for sentence_id, langs in SENTENCE_TRANSLATION_PARTS.items():
        text = SENTENCES[sentence_id]
        tokens = text.split()
        whole = SENTENCE_TRANSLATIONS.get(text, {})
        for lang, items in langs.items():
            joined = _JOINER[lang].join(t for t, _ in items)
            if joined != whole.get(lang):
                raise AssertionError(
                    f"{sentence_id.value}/{lang}: 조각을 이은 것과 번역문이 다르다\n"
                    f"  이은 것: {joined!r}\n  번역문  : {whole.get(lang)!r}"
                )
            covered = {i for _, ks in items for i in ks}
            if covered - set(range(len(tokens))):
                raise AssertionError(f"{sentence_id.value}/{lang}: 없는 어절을 가리킨다")


_assert_parts_join_to_translations()


def category_of(sentence_id: SentenceId) -> str:
    """id 접두어(arrival/lunch/departure)를 카테고리로 쓴다."""
    return sentence_id.value.rsplit("_", 1)[0]
