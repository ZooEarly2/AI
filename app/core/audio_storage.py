import os
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


@contextmanager
def save_temp_audio(upload_file: UploadFile):
    """Persist an uploaded audio file to disk for the duration of a request,
    then delete it — faster-whisper needs a file path, not a stream, and
    /tmp must never accumulate leftovers between requests."""
    Path(settings.temp_audio_dir).mkdir(parents=True, exist_ok=True)
    suffix = Path(upload_file.filename or "").suffix or ".wav"
    temp_path = os.path.join(settings.temp_audio_dir, f"{uuid.uuid4().hex}{suffix}")

    try:
        with open(temp_path, "wb") as f:
            f.write(upload_file.file.read())
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
