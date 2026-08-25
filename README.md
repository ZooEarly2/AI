# ZooEarly-AI — 쥬얼리 추론 서버

Spring 게이트웨이가 부르는 내부 API. **앱이 직접 부르지 않는다.**

| 항목 | 값 |
|---|---|
| Base Path | `/internal/v1` |
| 문서 | <http://localhost:8000/docs> |
| 헬스체크 | `GET /health` (인증 밖) |

## 왜 응답 모양이 이런가

게이트웨이는 응답 body 를 **파싱하지 않고 String 으로 통과시킨다.** 그래서 이 서버의
응답이 곧 앱이 받는 JSON 이고, 앱 계약(`{success, data}` 봉투 · camelCase)을 여기서
직접 만들어야 한다. 봉투가 없으면 앱은 응답을 통째로 못 읽는다.

```json
{ "success": true,  "data": { ... } }
{ "success": false, "error": { "code": "...", "message": "...", "field": null } }
```

에러는 **422 와 429 만** body 가 앱까지 간다. 나머지 4xx/5xx 는 게이트웨이가
`502 AI_SERVER_ERROR` 로 감싸며 body 를 버린다 — 앱에 뜻을 전하려면 422/429 를 써야 한다.

## 엔드포인트

| Method | Path | 하는 일 |
|---|---|---|
| POST | `/internal/v1/speech/transcribe` | 음성 → 텍스트 (STT) |
| POST | `/internal/v1/speech/synthesize` | 텍스트 → 음성 (base64 JSON) |
| POST | `/internal/v1/text/translate` | 번역 |
| POST | `/internal/v1/feedback/speaking` | 발음 채점 (오디오 → 약한 어절) |
| POST | `/internal/v1/feedback/expression` | 표현 교정 + 모국어 번역 |
| GET | `/internal/v1/feedback/sentences` | 연습 문장 10개 |
| POST | `/internal/v1/story/generate` | 하루치 4장면 → 동화 |
| POST | `/internal/v1/chat` | 자유 대화 (현재 앱에 화면 없음) |

요청 필드는 **camelCase 와 snake_case 를 둘 다 받는다.** 게이트웨이는 앱 계약대로
`audio`·`sentenceId`·`childName` 로 보내고, 초기 명세대로 붙여 둔 곳은
`audio_file`·`sentence_id`·`child_name` 을 쓴다. 한쪽만 받으면 다른 쪽이 전부 422 가 된다.

선택 필드는 **빈 값이 아니라 아예 오지 않는다.** 게이트웨이가 파트를 통째로 뺀다 —
`Form(...)` 로 필수 선언하면 그 요청이 422 로 죽는다.

### 발음 채점 vs 표현 교정 — 다른 기능이다

| | 표현 교정 `/feedback/expression` | 발음 채점 `/feedback/speaking` |
|---|---|---|
| 무엇을 보나 | 어떤 **낱말**을 골랐나 | 어떻게 **소리** 냈나 |
| 입력 | STT 텍스트 | 오디오 |
| 예 | "주세**여**" → "주세**요**" | 낱말은 맞지만 ㅈ 발음이 약함 |

발음 채점은 STT 를 거치지 않는다. 발음은 텍스트로 알 수 없기 때문이다.

## PROVIDER — mock / real

```
PROVIDER=mock   # 모델도 API 키도 필요 없다
PROVIDER=real   # CLOVA + OpenAI + faster-whisper + 채점 서비스
```

### real 모드가 무엇을 부르나

| 기능 | 어디로 | 실측 |
|---|---|---|
| 한국어 TTS | **CLOVA Voice Premium** (`nara`) | ~1초 |
| 그 밖 언어 TTS | OpenAI (`gpt-4o-mini-tts`) | ~4초 |
| 번역 · 동화 · 표현 교정 | OpenAI (`gpt-5-mini`) | 번역 2초 / 동화 14초 |
| 발음 채점 | Azure `pron-scorer` | ~1초 |
| STT | faster-whisper `small` (로컬 CPU) | 3.5초 음성에 ~3초 |

**한국어를 CLOVA 로 만드는 이유** — 억양이 자연스러워 아이가 따라 말할 문장에 맞는다.
다만 CLOVA Voice 는 **베트남어를 지원하지 않는다.** 모국어를 읽어주는 것이 이 앱의
핵심이라 그 언어는 OpenAI 로 넘긴다. CLOVA 가 실패해도 OpenAI 로 넘어간다 —
아이 입장에서 "눌렀는데 아무 소리도 안 난다"가 가장 나쁜 실패다.

**목소리는 둘이다.** 앱은 `voice` 로 "누가 말하는가"만 고르고(`TEACHER` / `FRIEND`)
어떤 성우를 쓸지는 서버가 정한다.

| `voice` | 기본값 | 누가 쓰나 |
|---|---|---|
| `TEACHER` | `CLOVA_TTS_VOICE` = `nara` | 토끼 선생님 · 안내 부엉이 · 급식/코끼리 선생님 |
| `FRIEND` | `CLOVA_TTS_VOICE_FRIEND` = `ndain` (아동) | 호랑이 친구, 모국어 인사 |

또래를 어른 목소리로 읽으면 "친구가 말을 걸었다"로 들리지 않는다. 글자를 아직
못 읽는 아이는 **소리로 누가 말하는지 구분한다.** `CLOVA_TTS_VOICE_FRIEND` 를
비워두면 둘이 같은 목소리가 된다.

**gpt-5 계열은 `reasoning_effort` 를 반드시 지정한다.** 기본값이면 답하기 전에 추론
토큰을 수백 개 태운다. 실측으로 동화 4장면 생성이 게이트웨이 60초 제한을 넘겼고,
`low` 로 낮추자 14초가 됐다. 호출마다 필요한 만큼만 준다
(`openai_client.reasoning`: 번역·대화 `minimal` / 동화·표현 교정 `low`).
reasoning 모델이 아닌 값을 `OPENAI_LLM_MODEL` 에 넣으면 이 인자를 아예 보내지 않는다.

**whisper 는 첫 STT 요청에 올린다.** 모델이 수백 MB 라 기동할 때 올리면 서버가 그만큼
늦게 뜨는데, 지금 앱 화면은 STT 를 부르지 않는다(표현 고르기 한 갈래만 쓴다).
처음 부를 때 한 번 내려받아 `app.state` 에 담아 두고 그 뒤로는 재사용한다.

`mock` 은 형식만 맞는 더미가 아니라 **화면에 그대로 띄워도 어색하지 않은 한국어**를
만든다. TTS 도 실제로 들리는 차임(WAV)을 준다 — 연동이 됐는지 화면이 잘못됐는지
헷갈리지 않게 하려는 것이다. 응답의 `data.mock: true` 로 목이라는 것을 알린다.

`mock` 모드에서는 `faster-whisper` 를 **import 조차 하지 않는다.** 무거운 의존성을
로컬·CI 에 강요하지 않으려고 `deps.py` 와 `main.py` 에서 지연 import 한다.

## 로컬에서 돌리기

```bash
python -m venv .venv
.venv/Scripts/python -m pip install fastapi "uvicorn[standard]" python-multipart \
    pydantic pydantic-settings python-dotenv openai httpx pytest
cp .env.example .env

.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload
.venv/Scripts/python -m pytest -q
```

`real` 로 돌리려면 추가로:

```bash
.venv/Scripts/python -m pip install "faster-whisper>=1.0"
```

`.env` 에 `OPENAI_API_KEY` · `CLOVA_CLIENT_ID` · `CLOVA_CLIENT_SECRET` ·
`SCORING_API_KEY` 를 채우고 `PROVIDER=real` 로 둔다. `CORS_ORIGINS` 에 프론트 주소
(`http://localhost:5173`)가 들어 있어야 브라우저에서 직접 확인할 때 막히지 않는다.

> **테스트는 언제나 목으로 돈다.** `tests/conftest.py` 가 `PROVIDER=mock` 을 못박는다 —
> 그러지 않으면 `.env` 의 `real` 을 물고 유료 API 를 실제로 호출하고, STT 테스트가
> 수백 MB 짜리 모델을 내려받기 시작한다.

### 혼자 확인하기 (게이트웨이 없이)

```bash
curl http://localhost:8000/internal/v1/feedback/sentences

# 선택 필드 없이 — 게이트웨이가 실제로 보내는 가장 흔한 실패 케이스
curl -X POST http://localhost:8000/internal/v1/speech/transcribe -F "audio=@test.wav"

curl -X POST http://localhost:8000/internal/v1/feedback/speaking \
  -F "audio=@test.wav" -F "sentenceId=arrival_2"
```

## 구조

```
app/
├─ api/         라우터 · 의존성(제공자 선택, X-API-Key 검사)
├─ core/        설정 · 응답 봉투 · 에러 변환 · 언어 코드 · 조사 처리 · 오디오 유틸
├─ providers/   mock / real 과 그 클라이언트(whisper, openai, 채점 서비스)
├─ schemas/     요청·응답 모델 (camelCase 직렬화, snake_case 별칭 수용)
└─ services/    검증과 흐름 — 라우트는 얇게 두고 판단은 여기서 한다
```

## 배포

`Dockerfile` 로 Azure Container Apps 에 올린다.

| 환경변수 | 뜻 |
|---|---|
| `PROVIDER` | `real` |
| `OPENAI_API_KEY` | 번역·동화·표현 교정, 한국어 외 TTS |
| `CLOVA_CLIENT_ID` / `CLOVA_CLIENT_SECRET` | 한국어 TTS |
| `CLOVA_TTS_VOICE` / `CLOVA_TTS_VOICE_FRIEND` | 선생님·친구 목소리. 뒤쪽을 비우면 한 목소리를 함께 쓴다 |
| `SCORING_API_BASE_URL` / `SCORING_API_KEY` | 발음 채점 서비스 |
| `API_KEY` | 게이트웨이가 `X-API-Key` 로 보내는 값. 비우면 인증하지 않는다 |
| `CORS_ORIGINS` | 브라우저에서 직접 붙을 때만 필요 |

> 워커는 1개로 둔다. whisper 모델이 워커마다 통째로 메모리에 올라가 늘리면 컨테이너
> 메모리를 배수로 먹는다. 동시 처리량은 replica 로 늘린다.
