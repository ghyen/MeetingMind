# MeetingMind TODO

---

## [DONE] 18. 실시간 녹음 중 진행 상황 UX 개선

**문제**: 오디오 청크 처리 시 UI에 진행 상황이 표시되지 않아 버그인지 정상 동작인지 알 수 없었음.

**구현 내용**:

### 서버 (`api/websocket.py`)
- 매 청크 처리 후 `{"type": "status"}` 메시지를 클라이언트에 push:
  - `state: "buffering"` — 음성 감지됨, 오디오 버퍼 축적 중 (`buffer_sec` 포함)
  - `state: "analyzing"` — STT 완료, 파이프라인 분석 진행 중
  - `state: "done"` — 분석 완료, 다시 대기 상태
  - `chunks` — 서버가 수신한 총 청크 수 (연결 생존 증명)

### 클라이언트 (`static/index.html`)
- live-bar에 3단계 상태 표시:
  - **Listening...** (회색 dot) — 대기 중
  - **Recording speech... Xs** (녹색 dot, 펄스) — 음성 감지, 버퍼 축적
  - **Analyzing...** (주황 dot, 펄스) — 파이프라인 분석 중
- **chunk counter** — "N chunks" 표시로 서버와 데이터 흐르고 있음을 시각적 확인

**관련 파일**: `api/websocket.py`, `static/index.html`

---

## [DONE] 19. 웹검색/alert가 녹음 중단 후에만 표시되는 이슈 수정

**문제**: 실시간 녹음 중 웹검색 결과와 개입 알림이 UI에 표시되지 않고, 녹음을 중단해야 `refreshState()`로 한번에 보였음.

**원인**: `/ws/audio`의 `_bg_analysis`가 `analysis` 메시지에 `topics`와 `interventions`만 포함하고 `issues`와 `references`를 누락. 클라이언트도 `analysis` 메시지에서 이 두 필드를 렌더하지 않았음.

**수정**:
- 서버: `_bg_analysis`의 `analysis` 메시지에 `issues`와 `references[-5:]` 추가
- 클라이언트: `analysis` 메시지 핸들러에서 `renderIssues(data.issues)`, `renderReferences(data.references)` 호출 추가

**관련 파일**: `api/websocket.py`, `static/index.html`

---

## [DONE] 20. 청크 사이즈 증가 시 화자 분리 가능 여부 조사

**결론**: 청크 사이즈를 늘릴 필요 없음.

**조사 결과**:
- 현재 구조에서 실시간 경로는 이미 0.5초 청크를 버퍼에 축적 후 침묵 1.2초 감지 시 한번에 whisper로 전달. 실제 whisper가 처리하는 단위는 수 초 분량의 축적된 오디오.
- **핵심 문제는 청크 사이즈가 아니라 실시간 경로의 화자 식별 방식**:
  - 파일 업로드(`transcribe_file`): whisper 세그먼트별로 오디오 구간을 잘라 각각 화자 식별 → 문장별 다른 화자 가능
  - 실시간(`_process_utterance`): 축적된 전체 오디오로 화자 1번 식별 → 전체가 같은 화자로 처리됨
- **개선 방향**: `_process_utterance()`를 `transcribe_file()` 방식으로 리팩토링하면 실시간에서도 세그먼트별 화자 분리 가능

**관련 파일**: `stt/whisper_stt.py`

---

## [DONE] 21. 쟁점 구조화 LLM 호출 빈도 줄이기 (배치 사이즈 증가)

**문제**: `IssueStructurer`가 발화 5개(`_BATCH_SIZE=5`)마다 LLM을 호출하여 비용과 지연이 큼.

**수정**:
- `_BATCH_SIZE = 5` 하드코딩 제거
- `config.py`에 `issue_batch_size: int = 10` 설정 추가
- `issues.py`에서 `settings.issue_batch_size` 참조하도록 변경
- `.env`에서 `MM_ISSUE_BATCH_SIZE=15` 등으로 조절 가능

**관련 파일**: `config.py`, `analysis/issues.py`

---

## [DONE] 22. 서버 로그 실시간 표시 패널

**구현 내용**:

### 서버 (`main.py`)
- `_WSLogHandler` 커스텀 로깅 핸들러 추가
- MeetingMind 모듈(pipeline, analysis, stt, search, db, api)의 INFO+ 로그를 WebSocket `manager.broadcast()`로 전달
- `call_soon_threadsafe` 패턴으로 worker 스레드(whisper `to_thread` 등)에서도 안전하게 전송

### 클라이언트 (`static/index.html`)
- 화면 하단에 접이식 **Server Logs** 패널 추가 (기본 접힘 32px → 펼침 220px)
- 로그 레벨별 색상: info=회색, warning=주황, error=빨강
- 모노스페이스 폰트, 자동 스크롤, 최대 300개 유지
- 패널 닫힘 시 새 로그 도착하면 파란 dot 깜빡임으로 알림
- `/ws/updates` WebSocket 상시 연결 (자동 재연결 3초) — 로그 수신용

**관련 파일**: `main.py`, `static/index.html`

---

## 15. 토픽 감지 묵음 체크 Dead Code 수정

**현재 문제**: `topic.py`의 stage 1에서 묵음(3초+)을 토픽 전환 후보로 판단하는 로직이 있으나, `_last_silence_ms`가 **항상 0**이라 실제로 작동하지 않음. 파이프라인에서 묵음 시간을 `TopicDetector`에 전달하는 경로가 없음.

```python
# topic.py — stage 1 (현재 dead code)
if self._last_silence_ms >= settings.topic_silence_threshold_sec * 1000:
    # 이 조건은 절대 True가 되지 않음 (_last_silence_ms = 0 고정)
```

**수정 방향**:
- `pipeline.py`에서 `WhisperSTT`의 묵음 시간을 `TopicDetector`에 전달하는 경로 추가
- 또는 `VADFilter.get_silence_duration_ms()`를 활용하여 묵음 추적
- `_last_silence_ms` 업데이트 로직 구현

**관련 파일**: `analysis/topic.py`, `pipeline.py`, `stt/whisper_stt.py`

---

## 16. 루프 감지 오탐 개선 — 도메인 용어 반복 필터링

**현재 문제**: `triggers.py`의 `_check_loop()`가 최근 10개 발화에서 동일 단어 3회 이상 반복을 루프로 판정하는데, **도메인 핵심 용어의 정상적 반복을 루프로 오탐**할 수 있음.

- 예: 금융 회의에서 "결제", "수수료", "이율" 반복 → 정상 논의인데 루프 경고 발동
- 불용어 리스트(`_STOPWORDS`)가 한국어 형태소 위주로 제한적 — 도메인 용어 미포함
- 루프 판정 문맥 윈도우(10발화)와 반복 횟수(3회) 모두 하드코딩

**수정 방향**:
- 현재 토픽의 키워드를 동적 불용어로 추가 (토픽명에 포함된 단어는 루프 대상에서 제외)
- 단순 단어 빈도가 아닌, "새로운 정보 없이 동일 주장 반복"을 감지하는 방식으로 개선
- 루프 판정 전 의미적 유사도 체크 (같은 단어라도 맥락이 다르면 루프 아님)

**관련 파일**: `analysis/triggers.py`, `config.py`

---

## 17. TTS 자료 요약 — 개입 타이밍 설계

**현재 문제**: TODO#11(TTS 기반 자료 요약)의 트리거 조건(침묵, info_needed, loop)이 정의되어 있으나, **회의 중 AI 음성 개입이 오히려 방해가 될 수 있는 상황**에 대한 고려가 부족함.

- 활발한 토론 중 침묵은 "생각 정리" 시간일 수 있음 → TTS가 끼어들면 흐름 끊김
- 빠른 발언 교대 중 info_needed 키워드가 수사적 표현일 수 있음 → 불필요한 개입
- 연속 TTS 쿨다운(30초)만으로는 부적절한 타이밍 방지가 불충분

**수정 방향**:
- 개입 적합도 판단 로직 추가: 침묵 길이, 직전 발화 속도, 토픽 진행 상태 등 복합 조건
- 사용자 컨트롤 강화: TTS on/off뿐 아니라 "요약 준비됨" 알림 → 사용자가 재생 결정
- push형(자동 재생) vs pull형(알림만, 사용자 트리거) 모드 선택

**관련 파일**: `pipeline.py` (`_maybe_speak_references`), `config.py`, `static/index.html`

---

## 12. 오디오 스트리밍-추론 파이프라인 오버랩 (레이턴시 최적화)

**현재 문제**: 클라이언트에서 오디오 패킷을 스트리밍으로 수신하다가 END 신호가 오면 STT → LLM 추론 파이프라인이 시작되는데, 추론 중에는 새로 도착하는 오디오 패킷이 대기 상태로 블로킹됨. 추론 완료 후에야 다음 오디오를 처리하므로 발화 간 레이턴시가 누적됨.

**목표**: LLM 추론이 진행되는 동안에도 다음 발화의 오디오 패킷을 비동기로 계속 수신·버퍼링하여, 추론 완료 즉시 다음 발화를 STT 처리할 수 있도록 파이프라인을 오버랩한다.

**구현 방향**:

### 12-1. 이중 버퍼 구조
- 현재 처리 중인 발화의 오디오와 다음 발화의 오디오를 분리하는 이중 버퍼(또는 큐) 도입
- `active_buffer`: 현재 STT/LLM 처리 중인 오디오
- `pending_buffer`: 추론 중 새로 도착하는 오디오 패킷을 축적
- END 신호 수신 시 `pending_buffer`를 `active_buffer`로 스왑

### 12-2. 비동기 수신 루프 분리
- 오디오 수신 루프와 추론 파이프라인을 별도 asyncio Task로 분리
- 수신 루프는 항상 실행 중: 패킷 도착 → 현재 상태에 따라 적절한 버퍼에 적재
- 추론 파이프라인은 END 신호 시 트리거, 완료 후 pending_buffer에 데이터가 있으면 즉시 다음 처리 시작

### 12-3. 상태 머신
```
IDLE → [패킷 수신] → BUFFERING → [END 수신] → PROCESSING
PROCESSING + [패킷 수신] → pending_buffer에 적재
PROCESSING → [추론 완료] → pending_buffer 확인 → BUFFERING 또는 IDLE
```

### 12-4. 관련 파일
- `api/websocket.py`: 오디오 수신 루프 수정, 이중 버퍼 관리
- `stt/whisper_stt.py`: STT 호출 인터페이스 (변경 최소화)
- `pipeline.py`: 추론 완료 콜백에서 pending_buffer 확인 로직

---

## 13. Agentic STT 후처리 파이프라인 (음성 인식 정확도 개선)

**현재 문제**: STT(faster-whisper) 모델이 음성을 텍스트로 변환할 때, 동음이의어·전문 용어·고유명사를 잘못 인식하는 경우가 빈번함. 예: "이율이 어떻게 되나요?" → "이효리 어떻게 되나요?", "PG사 수수료" → "피지사 수수료" 등. 현재는 STT 결과를 그대로 사용하므로 후속 분석(토픽 분류, 쟁점 구조화)의 품질도 연쇄적으로 저하됨.

**목표**: STT 1차 출력을 그대로 사용하지 않고, 회의 컨텍스트(참여자, 회사, 도메인)를 활용한 LLM 기반 후처리 단계를 추가하여 텍스트 정확도를 높인다.

**구현 방향**:

### 13-1. 도메인 용어 사전 (`data/domain_dict.json`)
- 회의 시작 시 사용자가 입력하거나 사전에 설정해두는 도메인별 용어 사전
- 구조: `{ "domain": "금융", "terms": ["이율", "PG사", "수수료", "결제 게이트웨이", ...] }`
- 회의 생성 API에서 도메인/회사명/주요 용어를 받아 세션별 용어 사전 구성
- 자주 사용되는 도메인 프리셋 제공 (금융, IT, 의료, 법률 등)

### 13-2. LLM 기반 교정 모듈 (`stt/post_processor.py`)
- STT 1차 출력을 받아 LLM으로 교정하는 모듈
- 입력: STT 원본 텍스트 + 도메인 용어 사전 + 회의 컨텍스트(최근 발화 N개)
- 프롬프트 전략:
  ```
  당신은 회의 음성 인식 교정기입니다.
  현재 회의 도메인: {domain}
  참여자: {participants}
  도메인 용어 사전: {terms}
  최근 발화 맥락: {recent_utterances}

  아래 STT 출력에서 도메인 용어, 고유명사, 동음이의어 오인식을 교정하세요.
  변경이 필요 없으면 원문 그대로 반환하세요.

  STT 출력: "{raw_text}"
  교정 결과:
  ```
- 교정 결과에 confidence threshold 적용: 원본과 너무 다르면(edit distance 과다) 원본 유지

### 13-3. 파이프라인 통합
- `pipeline.py`의 `on_utterance()` 흐름에 후처리 단계 삽입:
  ```
  오디오 → STT(1차 텍스트) → PostProcessor(교정 텍스트) → 토픽분류/쟁점구조화
  ```
- 후처리를 비동기로 실행하되, 12번(오버랩 파이프라인)과 연계하여 레이턴시 증가 최소화
- config에 `stt_post_processing: bool = True` 토글 추가
- 후처리 결과 로깅: 원본 vs 교정본 비교 로그 → 정확도 개선 추적 가능

### 13-4. 점진적 사전 학습
- 회의 진행 중 새로 등장하는 용어를 자동 감지하여 세션 사전에 추가
- 예: LLM이 첫 교정 시 "PG사"를 인식하면 이후 발화에서 동일 패턴 자동 교정
- 회의 종료 후 세션 사전을 사용자에게 제시 → 승인 시 도메인 프리셋에 반영

### 13-5. 관련 파일
- `stt/post_processor.py` (신규): LLM 교정 모듈
- `data/domain_dict.json` (신규): 도메인 용어 사전
- `config.py`: 후처리 관련 설정 추가
- `pipeline.py`: 후처리 단계 삽입
- `api/routes.py`: 회의 생성 시 도메인/용어 입력 API

---

## 14. STT 엔진 마이그레이션: faster-whisper → Cohere Transcribe

**현재**: faster-whisper large-v3 (CTranslate2, CPU int8) — M2 Pro에서 RTFx ~15x
**목표**: Cohere Transcribe (2B, Apache 2.0)로 교체하여 STT 정확도 향상

**배경**:
- Cohere Transcribe: WER 5.42% vs Whisper large-v3: 7.44% (영어 기준 27% 개선)
- 한국어 포함 14개 언어 지원, HF Open ASR 리더보드 1위 (2026-03-26)
- 단, GPU 최적화 모델이므로 M2 Pro CPU에서는 faster-whisper보다 느림
- **GPU 서버 배포 시 전환 권장** (A100 기준 RTFx 525x)

**속도 비교 (M2 Pro 32GB 예상)**:

| | faster-whisper (현재) | Cohere Transcribe |
|---|---|---|
| 런타임 | CTranslate2 CPU int8 | PyTorch FP16 |
| 10분 오디오 | ~40초 | ~2-4분 |
| 메모리 | ~1.5GB | ~4GB |

**마이그레이션 조건**: GPU 서버 환경이 확보되었을 때 진행

### 14-1. 구현 계획
- `stt/cohere_stt.py` 신규: `WhisperSTT`와 동일 인터페이스 (`feed_chunk`, `transcribe_file`)
- `config.py`: `stt_engine: str = "whisper" | "cohere"` 설정 추가
- `api/websocket.py`: 엔진 선택에 따라 STT 인스턴스 분기
- 의존성 추가: `transformers>=5.4.0`, `torch`

### 14-2. 검증 항목
- [ ] 한국어 WER 비교 테스트 (faster-whisper vs Cohere, 동일 샘플)
- [ ] GPU 환경 처리 속도 벤치마크
- [ ] 양자화 모델 출시 여부 확인 (2B FP16 → INT8/INT4)
- [ ] MPS(Apple Metal) 지원 상태 확인

### 14-3. 관련 자료
- HuggingFace: `CohereLabs/cohere-transcribe-03-2026`
- 라이선스: Apache 2.0
- 공식 블로그: https://cohere.com/blog/transcribe

---

## 11. TTS 기반 자료 요약 음성 안내

**목표**: 회의 중 말이 끊기거나 침묵이 발생했을 때, 수집된 web reference를 LLM으로 요약 → TTS로 음성 출력하여 회의 진행을 돕는다.

**트리거 조건** (기존 `TriggerDetector`와 연동):
- `silence` 트리거 발동 시 (5초+ 침묵) — 현재 토픽의 미소비 레퍼런스가 있을 때
- `info_needed` 트리거 발동 시 ("확인해봐야", "자료가 있나" 등) — 관련 레퍼런스 즉시 요약
- `loop` 트리거 발동 시 (논의 순환 감지) — 새로운 관점 제시를 위해 레퍼런스 요약

---

#### 11-1. TTS 엔진 모듈 (`tts/__init__.py`)

새 모듈 `tts/` 생성. STT와 대칭 구조.

```
tts/
├── __init__.py      # TTSEngine 인터페이스 + 팩토리
└── edge_tts.py      # edge-tts 기반 구현 (무료, 한국어 지원)
```

**구현 내용**:
- `TTSEngine` 프로토콜: `async def synthesize(text: str) -> bytes` (PCM/WAV 반환)
- 1차 구현: `edge-tts` 라이브러리 (Microsoft Edge TTS, 무료, 한국어 음성 `ko-KR-SunHiNeural`)
- 향후 확장: Google Cloud TTS, OpenAI TTS 등 provider 교체 가능하도록 설계
- 음성 출력은 16kHz mono WAV로 통일 (기존 오디오 파이프라인과 호환)
- TTS 결과 캐싱: 동일 요약문 재합성 방지 (간단한 dict 캐시)

**config.py 추가 설정**:
```python
# TTS
tts_enabled: bool = False                    # TTS 기능 on/off
tts_engine: str = "edge"                     # "edge" | "gtts" | "openai"
tts_voice: str = "ko-KR-SunHiNeural"        # edge-tts 음성 이름
tts_rate: str = "+10%"                       # 음성 속도 (회의 맥락에 맞게 약간 빠르게)
tts_max_chars: int = 300                     # 요약문 최대 글자수 (너무 긴 음성 방지)
tts_cooldown_sec: float = 30.0               # 연속 TTS 방지 쿨다운 (초)
```

**requirements.txt 추가**:
```
edge-tts>=6.1.0
```

---

#### 11-2. 레퍼런스 요약 생성기 (`analysis/ref_summarizer.py`)

수집된 Reference 목록을 LLM으로 요약하여 TTS에 전달할 짧은 안내문 생성.

**구현 내용**:
- `RefSummarizer.summarize(references: list[Reference], context: str) -> str`
  - `references`: 현재 토픽에서 수집된 레퍼런스 (relevance_score 상위 3~5개)
  - `context`: 현재 논의 맥락 (최근 발화 3개 요약)
- LLM 프롬프트: "회의 참석자에게 구두로 전달할 간결한 자료 요약문 생성"
  - 출력: 1~2문장, 300자 이내, 구어체
  - 예시: "관련 자료를 찾았습니다. PG사 응답 지연 관련해서, 최근 결제 게이트웨이 장애 보고서에 따르면 평균 응답 시간이 2.3초로 개선 중이고, AWS 리전 이전이 주요 원인으로 분석됩니다."
- 이미 요약/전달한 레퍼런스는 `_spoken_ref_ids: set`으로 추적하여 중복 방지
- 요약할 새로운 레퍼런스가 없으면 `None` 반환 → TTS 스킵

---

#### 11-3. 파이프라인 통합 (`pipeline.py`)

기존 `on_utterance()` 흐름에 TTS 판단 로직 추가.

**흐름**:
```
on_utterance()
  → _check_triggers()에서 silence/info_needed/loop 감지
  → _maybe_speak_references() 호출
    → 트리거 조건 확인 + 쿨다운 체크
    → RefSummarizer로 미소비 레퍼런스 요약
    → TTSEngine으로 음성 합성
    → WebSocket으로 오디오 데이터 전송 (type: "tts_audio")
    → _spoken_ref_ids 업데이트
```

**Pipeline 추가 속성**:
```python
self._tts_engine = None           # lazy init
self._ref_summarizer = None       # lazy init
self._last_tts_time: float = 0.0  # 쿨다운 추적
self._spoken_ref_ids: set = set() # 이미 음성 전달한 ref 추적
```

**핵심 메서드**:
```python
async def _maybe_speak_references(self, interventions: list[Intervention]) -> None:
    """트리거 발동 시 관련 레퍼런스를 요약하여 TTS로 출력."""
    if not settings.tts_enabled:
        return
    # 쿨다운 체크
    # TTS 대상 트리거 필터 (silence, info_needed, loop)
    # 현재 토픽의 미소비 레퍼런스 필터
    # LLM 요약 → TTS 합성 → WebSocket broadcast
```

---

#### 11-4. WebSocket 오디오 전송 (`api/websocket.py`)

TTS 합성 결과를 클라이언트에 전달하는 새 메시지 타입 추가.

**서버 → 클라이언트 메시지**:
```json
{
  "type": "tts_audio",
  "audio": "<base64 encoded WAV>",
  "text": "관련 자료를 찾았습니다. PG사 응답 지연 관련해서...",
  "trigger": "silence",
  "references": [
    {"title": "PG사 장애 보고서", "url": "https://..."}
  ]
}
```

- `audio`: base64 인코딩된 WAV 데이터 (프론트에서 `AudioContext`로 재생)
- `text`: TTS에 사용된 요약문 (UI에 자막으로 표시 가능)
- `trigger`: 어떤 트리거로 발동했는지 (UI 표시용)
- `references`: 요약에 사용된 원본 레퍼런스 목록 (클릭 링크용)

---

#### 11-5. 프론트엔드 오디오 재생 (`static/index.html`)

TTS 오디오를 받아 재생하는 UI 추가.

**구현 내용**:
- WebSocket `tts_audio` 메시지 수신 핸들러
- `AudioContext` + `decodeAudioData()`로 WAV 재생
  - 현재 마이크 입력과 간섭 방지: TTS 재생 중 STT 일시 정지 (echo cancellation)
  - 재생 완료 후 STT 재개
- UI 표시:
  - 개입 카드 영역에 "AI 안내" 타입 카드 추가 (파란색, 스피커 아이콘)
  - 카드에 요약 텍스트 표시 + 원본 레퍼런스 링크
  - TTS 재생 중 표시: 스피커 아이콘 애니메이션
- TTS on/off 토글 버튼 (상단 컨트롤 영역)

---

#### 11-6. Echo Cancellation 처리

TTS 음성이 마이크에 다시 입력되어 STT로 인식되는 문제 방지.

**방안** (택 1):
- **A. STT 일시정지**: TTS 재생 시작 → STT `pause()` → 재생 종료 → STT `resume()` (가장 단순)
- **B. 클라이언트 측 처리**: `AudioContext`에서 재생과 캡처를 분리, TTS 재생 중 마이크 음소거
- **C. 서버 측 마킹**: TTS 재생 시간대를 기록 → 해당 시간대 STT 결과 무시

**권장**: A안 (STT 일시정지) — 구현이 간단하고, 회의 중 AI가 말하는 동안 사람이 동시에 말할 가능성 낮음

---

#### 구현 순서 (권장)

| 단계 | 작업 | 의존성 | 예상 파일 |
|---|---|---|---|
| 1 | `config.py`에 TTS 설정 추가 | 없음 | `config.py` |
| 2 | TTS 엔진 모듈 구현 | edge-tts 설치 | `tts/__init__.py`, `tts/edge_tts.py` |
| 3 | 레퍼런스 요약 생성기 | LLM 모듈 | `analysis/ref_summarizer.py` |
| 4 | 파이프라인 통합 | 2, 3 | `pipeline.py` |
| 5 | WebSocket 전송 | 4 | `api/websocket.py` |
| 6 | 프론트엔드 재생 + UI | 5 | `static/index.html` |
| 7 | Echo Cancellation | 6 | `api/websocket.py`, `static/index.html` |
| 8 | 시나리오 테스트 | 전체 | `scripts/scenario_tts.py` |
