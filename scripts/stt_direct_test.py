"""faster-whisper STT를 서버 없이 직접 호출해보는 수동 테스트 스크립트.

사용법:
    python scripts/stt_direct_test.py sample_audio/hello.wav --lang ko
"""

import argparse

from app.core.config import settings
from app.providers.clients.whisper_client import load_whisper_model, transcribe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path")
    parser.add_argument("--lang", default="ko")
    args = parser.parse_args()

    model = load_whisper_model(
        settings.whisper_model_size, settings.whisper_device, settings.whisper_compute_type
    )
    result = transcribe(model, args.audio_path, args.lang)
    print(result)


if __name__ == "__main__":
    main()
