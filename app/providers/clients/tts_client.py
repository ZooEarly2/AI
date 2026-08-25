from openai import OpenAI

from app.core.config import settings

# gpt-4o-mini-tts 전용 파라미터: 목소리 자체(coral)뿐 아니라 말투까지 지시해
# 동화 구연가 같은 밝고 다정한 톤으로 유도한다.
_CHILD_FRIENDLY_INSTRUCTIONS = (
    "밝고 사랑스러운 목소리로, 동화를 들려주는 선생님처럼 다정하고 또박또박하게 말해주세요."
)

# 앱 계약의 voice enum → OpenAI 음성.
# 앱은 "누가 말하는가"(선생님/친구)만 고르고, 어떤 음성인지는 서버가 정한다 —
# OpenAI 가 음성 목록을 바꿔도 앱을 고칠 일이 없게 하려는 것이다.
_VOICE_BY_ROLE = {
    "TEACHER": "coral",   # 안내·선생님 토끼 — 따뜻하고 차분하다
    "FRIEND": "nova",     # 또래 친구 — 밝고 가볍다
}


def resolve_voice(voice: str | None) -> str:
    """TEACHER/FRIEND 를 실제 음성 이름으로 바꾼다.

    OpenAI 음성 이름(``coral`` 등)이 그대로 오면 그대로 쓴다 — 로컬에서 다른 목소리를
    바로 시험해 볼 수 있게 열어둔다.
    """
    if not voice:
        return settings.openai_tts_voice
    return _VOICE_BY_ROLE.get(voice.upper(), voice)


def synthesize(client: OpenAI, text: str, voice: str | None, speed: float) -> bytes:
    response = client.audio.speech.create(
        model=settings.openai_tts_model,
        voice=resolve_voice(voice),
        input=text,
        speed=speed,
        response_format="mp3",
        instructions=_CHILD_FRIENDLY_INSTRUCTIONS,
    )
    return response.content
