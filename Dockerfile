# 쥬얼리 추론 서버 — Azure Container Apps 용 이미지.
#
# 빌드를 두 단계로 나눈다. 휠을 미리 받아 두면 소스만 고친 재배포에서 의존성
# 다운로드를 통째로 건너뛴다 — faster-whisper 가 끌고 오는 ctranslate2/av 가
# 무거워서 이 차이가 크다.

# ── 1단계: 의존성 휠 빌드 ──────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# 패키지 자체가 아니라 의존성만 먼저 설치한다. 소스는 아직 복사하지 않았으므로
# 이 레이어는 pyproject.toml 이 바뀔 때만 다시 돈다.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      "fastapi>=0.115" "uvicorn[standard]>=0.32" "python-multipart>=0.0.9" \
      "pydantic>=2.9" "pydantic-settings>=2.5" "python-dotenv>=1.0" \
      "faster-whisper>=1.0" "openai>=1.50" "httpx>=0.27"

# ── 2단계: 실행 ────────────────────────────────────────
FROM python:3.12-slim

# faster-whisper 는 PyAV 로 오디오를 디코딩한다. 휠에 코덱이 들어 있지만
# ffmpeg 라이브러리가 없는 이미지에서는 m4a/webm 이 열리지 않는다.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# root 로 돌리지 않는다 — 컨테이너가 뚫렸을 때 피해 범위를 줄인다.
RUN useradd --create-home --shell /bin/false app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY app ./app

# 업로드된 녹음을 잠깐 두는 자리. 요청이 끝나면 지우지만 디렉터리는 있어야 한다.
ENV TEMP_AUDIO_DIR=/tmp/juelri-audio
RUN mkdir -p /tmp/juelri-audio && chown -R app:app /tmp/juelri-audio /app

USER app
EXPOSE 8000

# 워커를 1로 둔다. whisper 모델이 워커마다 통째로 메모리에 올라가서, 늘리면
# 컨테이너 메모리를 배수로 먹는다. 동시 처리량은 replica 로 늘린다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
