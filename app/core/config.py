from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "local"
    provider: str = "mock"          # mock | real
    log_level: str = "INFO"

    openai_api_key: str = ""
    openai_llm_model: str = "gpt-5-mini"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "coral"  # 어린이 대상 콘텐츠에 어울리는 밝고 따뜻한 기본 목소리
    # OpenAI SDK 기본값은 요청당 600초 · 재시도 2회다. 그대로 두면 게이트웨이가
    # 60초에 끊고 아이는 실패를 본 뒤에도 서버가 유료 호출을 최대 30분 붙들고 있다.
    # 가장 오래 걸리는 호출(동화 4장면, 실측 14~17초)에 여유를 준 값이다.
    openai_timeout_sec: float = 40.0
    # 재시도는 게이트웨이 예산 안에서만 뜻이 있다. 한 번 더까지가 한계다.
    openai_max_retries: int = 1

    # --- CLOVA Voice Premium (한국어 TTS) ---
    # 한국어는 CLOVA 로 만든다. OpenAI TTS 보다 억양이 자연스럽다.
    # CLOVA 는 베트남어를 지원하지 않아, 모국어 음성은 OpenAI 로 넘어간다.
    clova_client_id: str = ""
    clova_client_secret: str = ""
    clova_tts_voice: str = "nara"
    #: 또래 친구(voice=FRIEND) 목소리. 비어 있으면 위 목소리를 함께 쓴다 —
    #: 계정에 없는 목소리를 넣으면 CLOVA 가 400 을 주고 매번 OpenAI 로 새기 때문이다.
    clova_tts_voice_friend: str = ""
    clova_timeout_sec: float = 15.0

    # 앱이 보내는 속도 "배수"의 기본값(0.5~1.5). 클수록 빠르다.
    # CLOVA 는 눈금이 반대(-5~5, 클수록 느리다)라 clova_client 가 뒤집어 보낸다.
    tts_default_speed: float = 0.9  # 만 5~8세 아동 기준 청취 속도

    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    supported_languages: str = "ko,vi,zh"

    temp_audio_dir: str = "/tmp/juelri-audio"
    max_audio_duration_sec: int = 30

    # 로컬 프론트(Vite 5173) / Expo web(8081) / 게이트웨이 Swagger 를 기본 허용한다.
    # 게이트웨이를 거치는 정상 경로는 서버 대 서버라 CORS 와 무관하지만, FastAPI 를
    # 직접 열어 확인할 때(=/docs, 프론트 디버깅) 이 값이 없으면 브라우저가 막는다.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8081,http://localhost:3000"

    # 게이트웨이가 X-API-Key 헤더로 인증한다. 비워두면 인증을 하지 않는다 —
    # 로컬 개발·목 서버가 헤더 없이 그대로 붙기 위한 것이고, 배포에서는 반드시 채운다.
    api_key: str = ""

    # --- 발음 채점 (wav2vec-base-finetuning, Azure 배포) ---
    scoring_api_base_url: str = ""
    scoring_api_key: str = ""
    scoring_timeout_sec: float = 30.0  # Azure Container Apps 콜드 스타트(모델 재로드 포함) 여유분
    scoring_max_upload_mb: float = 20.0

    @property
    def supported_language_list(self) -> list[str]:
        return [lang.strip() for lang in self.supported_languages.split(",")]


settings = Settings()
