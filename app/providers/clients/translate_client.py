from openai import OpenAI

from app.core.config import settings
from app.providers.clients.openai_client import reasoning
from app.core.languages import language_name


# 직역이 아닌, 아이가 실제로 말할 법한 자연스럽고 구어체인 문장으로 옮기게 지시한다.
_SYSTEM_PROMPT_TEMPLATE = (
    "You are a translator for a children's language-learning app. "
    "Translate the given {source} text into natural, colloquial {target} "
    "the way a native child speaker would say it. "
    "Reply with only the translated text — no explanations, no quotes."
)


def translate(client: OpenAI, text: str, source_language: str, target_language: str) -> str:
    source_name = language_name(source_language)
    target_name = language_name(target_language)

    response = client.chat.completions.create(
        model=settings.openai_llm_model,
        messages=[
            {
                "role": "system",
                "content": _SYSTEM_PROMPT_TEMPLATE.format(source=source_name, target=target_name),
            },
            {"role": "user", "content": text},
        ],
        # 한 문장을 옮기는 일이다. 추론에 시간을 쓸수록 화면이 늦게 뜬다
        **reasoning("minimal"),
    )
    return response.choices[0].message.content.strip()
