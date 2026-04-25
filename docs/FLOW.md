# MeetingMind 전체 플로우 가이드

음성 입력부터 분석 결과 출력까지의 전체 데이터 흐름을 설명한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        입력 (3가지 경로)                         │
│  ① 실시간 마이크 (WebSocket /ws/audio)                          │
│  ② 파일 업로드 (POST /api/meeting/upload)                       │
│  ③ 텍스트 시뮬레이션 (POST /api/meeting/simulate)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STT + 화자 식별                              │
│  faster-whisper (실시간 + 파일 배치)                             │
│  SpeakerIdentifier (3dspeaker 임베딩 기반 화자 식별)             │
│  → 결과: Utterance(time, speaker, text)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Pipeline.on_utterance()                         │
│                                                                  │
│  1. DB 저장 (utterance)                                          │
│  2. 토픽 전환 감지 (TopicDetector)                               │
│  3. 트리거 감지 (TriggerDetector)                                │
│  4. 쟁점 구조화 (IssueStructurer)                                │
│  5. 자료 수집 (ReferenceCollector) ← 4가 갱신될 때만 호출         │
│     쟁점 요약본(topic + open_question)을 쿼리로 1회 검색          │
│  6. WebSocket broadcast                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Pipeline.end_meeting()                          │
│                                                                  │
│  회의록 요약 생성 (LLM) → DB 저장                                │
│  → 제목, 참석자, 안건별 요약, 결정 사항, 액션 아이템              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     출력 (4가지 경로)                             │
│  ① WebSocket /ws/updates: 실시간 이벤트 push                    │
│  ② WebSocket /ws/audio 응답: transcript + analysis               │
│  ③ REST API /api/meeting/*: 상태 조회                            │
│  ④ SQLite DB: 영구 저장 (회의 히스토리 + 요약)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. 서버 시작

**파일**: `main.py`

```python
# main.py — FastAPI lifespan으로 앱 시작 시 로그 핸들러 + DB 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    _ws_log_handler.set_loop(asyncio.get_running_loop())  # 로그 → WebSocket 전달 활성화
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    import db
    await db.init_db()
    yield

# main.py — 전역 Pipeline 싱글톤 (모든 요청이 이 인스턴스를 공유)
pipeline = Pipeline()
pipeline.add_listener(_broadcast_event)  # Pipeline 이벤트 → WebSocket broadcast

# main.py — _WSLogHandler: 서버 로그를 WebSocket으로 broadcast (브라우저 로그 패널용)
# MeetingMind 모듈(pipeline, analysis, stt, search, db, api) INFO+ 로그만 전달
```

**설정 로드**: `config.py`
- `Settings` 클래스가 `.env` 파일에서 `MM_` 접두사 환경변수를 읽어 설정
- STT, VAD, 화자분리, 토픽감지, 개입트리거, LLM, DB, 쟁점배치(`issue_batch_size`) 등 관리

---

## 2. 입력 경로

### 2-A. 실시간 마이크 (WebSocket)

**파일**: `api/websocket.py:58-147`

```
브라우저                          서버 (/ws/audio)
  │                                │
  │── WebSocket 연결 ──────────────▶│ manager.connect()
  │                                │ WhisperSTT 모델 로드
  │                                │ pipe.start_meeting()
  │◀── {"type":"ready"} ──────────│
  │                                │
  │── audio chunk (bytes) ─────────▶│ whisper.feed_chunk(chunk)
  │   (float32 PCM, 0.5초 단위)    │    ↓
  │                                │ RMS 기반 VAD로 음성/침묵 판별
  │◀── {"type":"status",          │ (음성 감지 시)
  │     "state":"buffering",       │  buffer_sec, chunks 포함
  │     "buffer_sec":2.5} ────────│
  │                                │ 침묵 1.2초 이상이면 발화 종료
  │                                │ 축적된 오디오 → whisper 인식
  │◀── {"type":"transcript",...} ──│ Utterance 반환
  │◀── {"type":"status",          │
  │     "state":"analyzing"} ──────│ 분석 시작 알림
  │                                │ pipe.on_utterance() (백그라운드)
  │◀── {"type":"analysis",...} ────│ topics + issues + interventions + references
  │◀── {"type":"status",          │
  │     "state":"done"} ───────────│ 분석 완료 알림
  │                                │
  │── "calibrate" (텍스트) ─────────▶│ 노이즈 캘리브레이션 시작
  │◀── {"type":"calibrated",...} ──│ 2초간 배경 소음 측정 후 완료
  │                                │
  │── 연결 종료 ───────────────────▶│ whisper.flush() → 잔여 버퍼 처리
```

**코드 흐름**:
1. 클라이언트가 `/ws/audio`에 WebSocket 연결 (`websocket.py:58-59`)
2. `WhisperSTT` 모델 로드 — `faster-whisper large-v3` + 화자 식별 모델 (`websocket.py:79-86`)
3. 회의 자동 시작 (`websocket.py:88-92`)
4. 오디오 청크 수신 루프 (`websocket.py:108-134`):
   - `whisper.feed_chunk(audio_chunk)` 호출 → `whisper_stt.py:109`
   - 발화 완성 시 `Utterance` 반환 → transcript 전송 + 백그라운드 분석
5. 연결 종료 시 `whisper.flush()`로 잔여 오디오 처리 (`websocket.py:135-142`)

### 2-B. 파일 업로드

**파일**: `api/routes.py:85-132`

```
클라이언트                              서버 (POST /api/meeting/upload)
  │                                      │
  │── multipart/form-data (파일) ──────▶│
  │                                      │ ① 오디오 변환 (audio_converter)
  │                                      │    다양한 포맷 → 16kHz mono float32
  │                                      │
  │                                      │ ② WhisperFileSTT.transcribe_file()
  │                                      │    전체 오디오 배치 처리
  │                                      │    + 세그먼트별 화자 식별
  │                                      │
  │                                      │ ③ 각 Utterance를 순차적으로
  │                                      │    pipe.on_utterance() 호출
  │                                      │
  │◀── JSON 응답 (발화 목록) ───────────│
```

**코드 흐름**:
1. 파일 바이트 읽기 (`routes.py:98`)
2. `convert_bytes()` → 16kHz mono float32 변환 (`audio_converter.py:83`)
   - soundfile 직접 지원: wav, flac, ogg, mp3 등 (`audio_converter.py:24-27`)
   - ffmpeg 필요: m4a, aac, webm 등 (`audio_converter.py:30-33`)
3. `WhisperFileSTT.transcribe_file(data)` → 배치 STT (`whisper_stt.py:67-105`)
4. 각 발화마다 `pipe.on_utterance()` 순차 호출 (`routes.py:125-129`)

### 2-C. 텍스트 시뮬레이션

**파일**: `api/routes.py:135-170`

STT 없이 직접 텍스트를 파이프라인에 주입. 테스트/개발용.

```python
# routes.py:155-161
utterance = Utterance(time=time_str, speaker=req.speaker, text=req.text)
await pipe.on_utterance(utterance)
```

시간은 자동 계산 (발화당 5초 간격) 또는 직접 지정 가능.

---

## 3. STT + 화자 식별

### 3-A. 실시간 STT: WhisperSTT (faster-whisper 기반)

**파일**: `stt/whisper_stt.py:30-227`

두 가지 모드를 하나의 클래스에서 처리:

#### 실시간 모드 (`feed_chunk`)

```
오디오 청크 (0.5초)
     │
     ▼
 RMS 계산 (에너지 레벨)    ← whisper_stt.py:122
     │
     ├── RMS > threshold → 음성: 버퍼에 축적
     │                            ↓
     │                      silence_ms = 0
     │
     └── RMS ≤ threshold → 침묵: silence_ms += 500ms
                                  ↓
                          silence ≥ 1200ms?
                            ├── No → 대기 (침묵도 버퍼에 포함)
                            └── Yes → 발화 종료!
                                       ↓
                                 축적된 오디오 → _process_utterance()
                                       ↓
                                 faster-whisper 텍스트 추출
                                 + SpeakerIdentifier 화자 식별
                                       ↓
                                 Utterance 반환
```

**핵심 로직** (`whisper_stt.py:109-168`):
- 간이 VAD: RMS (Root Mean Square) 에너지로 음성/침묵 판별
- 캘리브레이션: 2초간 배경 소음 측정 → 적응형 임계값 설정 (`whisper_stt.py:125-135`)
- 발화 최소 길이: 0.3초 미만은 무시 (`whisper_stt.py:163`)

#### 파일 배치 모드 (`transcribe_file`)

**코드**: `whisper_stt.py:67-105`

```
전체 오디오 (float32 배열)
     │
     ▼
faster-whisper.transcribe()      ← whisper_stt.py:72-81
  - VAD 필터 활성화 (min_silence_duration_ms=500)
  - beam_size=5, language="ko"
     │
     ▼
세그먼트별 처리:
  각 segment → start/end 시간으로 오디오 구간 잘라냄
            → SpeakerIdentifier.identify()로 화자 식별
            → Utterance 생성
```

### 3-B. 화자 식별: SpeakerIdentifier

**파일**: `stt/speaker.py`

```
오디오 샘플 (float32)
     │
     ▼
SpeakerEmbeddingExtractor       ← speaker.py:31-40
  create_stream() → accept_waveform() → compute()
  → 화자 임베딩 벡터 추출 (고차원 벡터)
     │
     ▼
SpeakerEmbeddingManager.search()  ← speaker.py:72
  등록된 화자들과 코사인 유사도 비교
  threshold: 0.5 (config.py:20)
     │
     ├── 매칭됨 → 기존 화자 이름 반환 ("Speaker 1")
     │
     └── 매칭 안됨 → 새 화자 등록             ← speaker.py:74-78
                    speaker_count += 1
                    manager.add("Speaker N", embedding)
                    → "Speaker N" 반환
```

---

## 4. 파이프라인 분석

**파일**: `pipeline.py:70-289`

모든 입력 경로는 최종적으로 `Pipeline.on_utterance(utterance)`를 호출한다.

### 4-0. 전체 실행 순서

```python
# pipeline.py:151-213
async def on_utterance(self, utterance: Utterance):
    # ① DB 저장
    await self._save_utterance(utterance)

    # ② 토픽 전환 감지
    new_topic = await self.topic_detector.check(utterance)

    # ③ 현재 토픽에 발화 추가
    if self.state.topics:
        self.state.topics[-1].utterances.append(utterance)

    # ④ 트리거 감지 (항상 먼저, 직렬)
    await self._check_triggers(utterance)

    # ⑤ 쟁점 구조화 → 갱신된 경우에만 자료 수집
    #    issue_token_threshold(500토큰)마다 1회 갱신, 갱신 시에만 검색 트리거
    #    → 발화당 검색 대비 웹 호출 빈도 대폭 감소
    updated_issue = await self._update_issues(utterance)
    if updated_issue is not None and self.state.topics:
        await self._search_references(self.state.topics[-1], updated_issue)

    # ⑥ WebSocket broadcast
    await self._emit("utterance", utterance)
    if new_topic:
        await self._emit("topic", new_topic)
```

### 4-1. 토픽 전환 감지 (TopicDetector)

**파일**: `analysis/topic.py`

3단계 필터로 토픽 전환을 판단한다:

```
발화 입력
  │
  ├── 첫 발화? → "회의 시작" 토픽 자동 생성        ← topic.py:31-39
  │
  ▼
[1차 필터] 키워드 1개+ 또는 긴 침묵(3초+)          ← topic.py:71-78
  │
  ├── 통과 못함 → return None (토픽 전환 없음)
  │
  ▼
[2차 필터] 키워드 2개+ 동시 매칭                    ← topic.py:58-69
  │
  ├── 2개+ 매칭 → LLM 없이 전환 확정
  │               새 Topic 생성
  │
  └── 1개만 매칭 → [3차 판단] LLM 최종 판단        ← topic.py:80-102
                     최근 10개 발화를 컨텍스트로 전달
                     LLM이 {"changed": true/false, "title": "..."} 응답
                     ↓
                     changed=true → 새 Topic 생성
                     changed=false → return None
```

**1차 필터 키워드** (`config.py:24`):
```python
topic_keywords = ["다음 안건", "그건 그렇고", "자 이제", "넘어가서"]
```

**2차 필터 키워드** (`topic.py:56`):
```python
_SECOND_FILTER_KEYWORDS = ["마무리", "정리", "넘어가서", "다음 안건", "다음으로"]
```

**토픽 전환 시 처리**:
- 이전 토픽의 `end_time`을 현재 토픽의 `start_time`으로 설정 (`topic.py:50-51`)
- DB에 새 토픽 저장 + 이전 토픽 end_time 업데이트 (`pipeline.py:226-240`)

### 4-2. 트리거 감지 (TriggerDetector)

**파일**: `analysis/triggers.py`

6가지 트리거를 매 발화마다 검사한다:

```
발화 + MeetingState
  │
  ├── _check_consensus()       키워드: "그렇게 하죠", "동의합니다" 등
  │     └─ 오탐 방지: 키워드 제거 후 나머지가 10자 초과면 무시  ← triggers.py:67-69
  │
  ├── _check_info_needed()     키워드: "확인해봐야", "자료가 있나" 등
  │
  ├── _check_no_decision()     이전 토픽에 decision=None이면 경고
  │     └─ 중복 방지: 같은 토픽에 대해 1번만 발생              ← triggers.py:91
  │
  ├── _check_loop()            최근 10발화에서 같은 단어 3회+ 반복
  │     └─ 불용어 필터: "정도", "합니다" 등 일반 단어 제외      ← triggers.py:26-34
  │
  ├── _check_silence()         연속 무음 5초+ (MeetingState.current_silence_ms)
  │
  └── _check_time_over()       안건 시작~현재 발화 시간 차이 > 10분
        └─ HH:MM:SS 문자열 파싱으로 시간 차이 계산              ← triggers.py:178-184
```

**Intervention 결과 구조** (`models.py:57-64`):
```python
@dataclass
class Intervention:
    trigger_type: str   # "loop" | "no_decision" | "consensus" | "silence" | "info_needed" | "time_over"
    message: str        # UI에 표시할 메시지
    level: AlertLevel   # INFO | WARNING | ACTION_REQUIRED
    topic_id: int | None
```

### 4-3. 쟁점 구조화 (IssueStructurer)

**파일**: `analysis/issues.py`

점진적 업데이트 방식 — 발화 5개마다 배치로 LLM 호출:

```
새 발화 입력
  │
  ├── 현재 토픽에 IssueGraph 없음? → _create_initial()     ← issues.py:37
  │     전체 발화(최대 15개)를 LLM에 전달
  │     → 초기 쟁점 구조 생성
  │
  ├── pending 발화 < 5개? → 기존 IssueGraph 그대로 반환     ← issues.py:42-43
  │
  └── pending 발화 ≥ 5개? → _apply_delta()                  ← issues.py:39-41
        기존 구조 + 새 발화를 LLM에 전달
        → 변경분만 반영한 업데이트 구조 반환
```

**IssueGraph 구조** (`models.py:40-48`):
```python
@dataclass
class IssueGraph:
    topic: str                      # 안건명 (10자 이내)
    positions: list[Position]       # 화자별 입장 (최대 5개)
    consensus: str | None           # 합의 사항
    open_questions: list[str]       # 미결 이슈
    decision: str | None            # 최종 결정
```

**Position 병합 로직** (`issues.py:93-117`):
- 같은 화자의 입장은 하나로 병합
- stance는 더 긴 것으로 교체
- arguments, evidence는 중복 제거 후 합산

### 4-4. 자료 수집 (ReferenceCollector)

**파일**: `search/__init__.py`

쟁점 구조가 실제 갱신될 때만 호출 — 발화당 LLM 엔티티 추출을 제거하고
요약본(IssueGraph) 기준 1회 검색으로 단순화. 호출 빈도가 issue_token_threshold(500토큰)
주기로 떨어져 웹 API 호출이 대폭 감소.

```
쟁점 갱신(IssueGraph + 안건 Topic)
  │
  ▼
[ReferenceCollector.search_for_issue()]            ← search/__init__.py
  │
  ├── 쿼리 합성: "{topic.title} {issue.topic} {open_questions[0]}"
  │   동일 쿼리는 _query_cache(set)로 스킵
  │
  ├── InternalSearch (ChromaDB 벡터 검색)           ← search/__init__.py
  │     사내 문서 임베딩 DB에서 유사도 검색
  │     relevance_score = 1.0 - distance
  │
  └── WebSearch (Tavily → DuckDuckGo 폴백)          ← search/__init__.py
        외부 웹 검색
        Tavily API 키 없으면 DuckDuckGo 폴백
  │
  ▼
결과 합산 → relevance_score 내림차순 정렬
→ Reference 리스트 반환
```

> `EntityExtractor` 클래스는 `search/__init__.py`에 남아 있으나 파이프라인 기본 경로에서는 사용하지 않는다.

### 4-5. 회의록 요약 (generate_summary)

**파일**: `analysis/summary.py`

회의 종료 시(`Pipeline.end_meeting()`) 한 번만 실행:

```
end_meeting() 호출
  │
  ▼
전체 발화 + 안건별 쟁점 → LLM 프롬프트 구성
  │
  ▼
ask_json() → 구조화된 회의록 JSON 반환
  │
  ▼
DB summaries 테이블에 저장
```

**출력 구조**:
```json
{
  "title": "회의 제목",
  "participants": ["Speaker 1", "Speaker 2"],
  "topics": [
    {
      "title": "안건명",
      "summary": "논의 요약",
      "decision": "결정 사항 (없으면 null)",
      "open_questions": ["미결 이슈"]
    }
  ],
  "action_items": [
    {"assignee": "담당자", "task": "할 일", "topic": "관련 안건"}
  ],
  "key_decisions": ["주요 결정 사항"]
}
```

---

## 5. LLM 호출

**파일**: `analysis/llm.py`

모든 LLM 호출은 `ask_json()` 함수를 통한다.

```
ask_json(prompt)                                     ← llm.py:75-97
  │
  ├── provider="ollama" → _ask_ollama()              ← llm.py:58-72
  │     Ollama 네이티브 API (/api/chat)
  │     think=False로 reasoning 비활성화
  │     timeout: 120초
  │
  └── provider="openrouter" → OpenAI 호환 API           ← llm.py:82-88
        response_format={"type":"json_object"}
  │
  ▼
JSON 파싱 (마크다운 코드블록 제거)                     ← llm.py:91-97
→ dict 반환
```

**LLM을 사용하는 곳**:
1. `TopicDetector._llm_judge()` — 토픽 전환 3차 판단 (`topic.py:80`)
2. `IssueStructurer._create_initial()` — 초기 쟁점 구조 생성 (`issues.py:48`)
3. `IssueStructurer._apply_delta()` — 쟁점 점진적 업데이트 (`issues.py:68`)
4. `generate_summary()` — 회의 종료 시 전체 회의록 요약 (`analysis/summary.py`)

---

## 6. 결과 출력

### 6-A. WebSocket 실시간 push

**파일**: `api/websocket.py:32-55`, `main.py:47-57`

```python
# main.py:47-54 — Pipeline 이벤트를 WebSocket /ws/updates 클라이언트에 broadcast
async def _broadcast_event(event_type: str, data=None):
    await manager.broadcast({
        "type": event_type,   # "utterance" | "topic"
        "data": _serialize(data),
    })
```

`/ws/updates`에 연결된 모든 클라이언트가 이벤트를 수신.
`/ws/audio`는 별도로 해당 연결에만 `transcript`/`analysis` 전송.

### 6-B. REST API 조회

**파일**: `api/routes.py`

| 엔드포인트 | 메서드 | 설명 | 코드 위치 |
|---|---|---|---|
| `/api/meeting/start` | POST | 회의 시작 | `routes.py:49` |
| `/api/meeting/end` | POST | 회의 종료 + 요약 생성 | `routes.py:58` |
| `/api/meeting/state` | GET | 현재 회의 상태 (인메모리) | `routes.py:72` |
| `/api/meeting/upload` | POST | 파일 업로드 STT | `routes.py:85` |
| `/api/meeting/simulate` | POST | 텍스트 시뮬레이션 | `routes.py:135` |
| `/api/meeting/topics` | GET | 안건 목록 | `routes.py:173` |
| `/api/meeting/issues/{id}` | GET | 특정 안건 쟁점 | `routes.py:179` |
| `/api/meeting/summary` | GET | 회의록 요약 | `routes.py:186` |
| `/api/meeting/interventions` | GET | 개입 알림 목록 | `routes.py:193` |
| `/api/meeting/reset` | POST | 상태 초기화 | `routes.py:192` |
| `/api/meetings` | GET | 저장된 회의 목록 (DB) | `routes.py:213` |
| `/api/meetings/{id}` | GET | 회의 전체 데이터 (DB) | `routes.py:220` |
| `/api/models` | GET | LLM 모델 목록 | `routes.py:232` |
| `/api/model` | GET/POST | 활성 모델 조회/변경 | `routes.py:248,255` |

### 6-C. WebSocket 엔드포인트

| 엔드포인트 | 설명 | 코드 위치 |
|---|---|---|
| `/ws/audio` | 오디오 청크 → STT + 분석 | `websocket.py:58` |
| `/ws/speaker` | 오디오 → 화자 식별만 | `websocket.py:150` |
| `/ws/speaker-id` | 화자 식별 (명령 기반) | `websocket.py:194` |
| `/ws/updates` | 분석 결과 실시간 push | `websocket.py:249` |

### 6-D. DB 영구 저장

**파일**: `db/__init__.py` (활성), `db.py` (레거시)

DB 스키마 (`db/__init__.py:15-67`):
```
meetings        → 회의 메타데이터 (id, title, started_at, ended_at)
utterances      → 발화 기록 (meeting_id, time, speaker, text)
topics          → 토픽/안건 (meeting_id, topic_seq, title, start_time, end_time)
issues          → 쟁점 구조 (meeting_id, topic_id, issue_graph_json)
interventions   → 개입 알림 (meeting_id, trigger_type, message, level)
refs            → 참고 자료 (meeting_id, query, source, title, snippet, url)
summaries       → 회의록 요약 (meeting_id, summary_json)
```

---

## 7. 데이터 모델 요약

**파일**: `models.py`

```
Utterance           STT 결과 단위 (time, speaker, text, is_final)
  │
  ▼
Topic               토픽 세그먼트 (id, title, start_time, end_time, utterances[])
  │
  ├── IssueGraph    논점 그래프 (topic, positions[], consensus, open_questions[], decision)
  │     └── Position   화자별 입장 (speaker, stance, arguments[], evidence[])
  │
  ├── Intervention  개입 카드 (trigger_type, message, level, topic_id)
  │
  └── Reference     참고 자료 (query, source, title, snippet, url, relevance_score)
```

---

## 8. MeetingState (인메모리 상태)

**파일**: `pipeline.py:57-68`

Pipeline이 관리하는 현재 회의의 전체 상태:

```python
@dataclass
class MeetingState:
    utterances: list[Utterance]           # 모든 발화
    topics: list[Topic]                   # 토픽 목록 (각 토픽에 utterances 포함)
    issues: dict[int, IssueGraph]         # topic_id → 쟁점 구조
    interventions: list[Intervention]     # 전체 개입 히스토리
    latest_interventions: list[Intervention]  # 직전 발화에서 발생한 개입만
    references: list[Reference]           # 수집된 참고 자료 전체
    latest_corrections: list[Utterance]   # 직전 STT 교정 결과
    current_silence_ms: float             # 현재 연속 무음 시간
```

---

## 9. Lazy Loading 패턴

**파일**: `pipeline.py:95-135`

모든 분석 모듈은 처음 사용 시점에 로드 (startup 시간 최소화):

```python
@property
def topic_detector(self):
    if self._topic_detector is None:
        from analysis.topic import TopicDetector  # 여기서 import
        self._topic_detector = TopicDetector()
    return self._topic_detector
```

같은 패턴: `issue_structurer`, `trigger_detector`, `reference_collector`, `stt_corrector`

---

## 10. 프론트엔드 (static/index.html)

**파일**: `static/index.html`

단일 HTML 파일. 3-column + 하단 로그 패널 레이아웃:
- **좌측**: 실시간 트랜스크립트 (발화 목록) + live-bar (상태 표시)
- **중앙**: 토픽 탭 + 쟁점 구조 (IssueGraph 카드)
- **우측**: 개입 알림 + 참고 자료
- **하단**: 접이식 Server Logs 패널 (서버 로그 실시간 표시)

**브라우저 → 서버 통신**:
1. WebSocket `/ws/audio`: 마이크 오디오 스트리밍 + 처리 상태(status) 수신
2. WebSocket `/ws/speaker-id`: Web Speech API 발화 단위로 화자 식별 요청
3. WebSocket `/ws/updates`: 서버 로그 + broadcast 이벤트 수신 (상시 연결, 자동 재연결)
4. REST API: 회의 시작/종료, 히스토리 조회, 파일 업로드

**Dev Panel**: 하단 우측에 시뮬레이션/디버그 패널 (텍스트 발화 입력, 프리셋 시나리오)

**Log Panel**: 화면 하단 접이식 패널. `/ws/updates` WebSocket으로 서버 로그를 실시간 수신하여 표시. `main.py`의 `_WSLogHandler`가 MeetingMind 모듈 로그를 broadcast. 로그 레벨별 색상 구분, 최대 300개 유지, 새 로그 도착 시 알림 dot 표시.
