# MeetingMind TODO

---

## [BUG] 요약 화면에 쟁점 구조화 미표시 ㅇ

**현상**: 회의 종료 후 summary 화면에 쟁점 구조화(IssueCard) 섹션이 없음  
**원인**: `SummaryScreen`(Chrome.jsx:358)이 `one_line`, `decisions`, `action_items`만 렌더링함. `state.issues`를 summary 화면에 props로 넘기지 않음  
**수정**:
- `index.html:418` `<SummaryScreen>`에 `issues={state.issues}` prop 추가
- `Chrome.jsx` `SummaryScreen` 컴포넌트에 `issues` prop 수신 후 안건별 read-only 쟁점 카드 렌더링 (IssueCard 재사용)

---

## [BUG] 쟁점 구조화 토큰 로딩바 미표시 ㅇ

**현상**: IssueCard에 다음 LLM 업데이트까지 누적 토큰이 얼마나 쌓였는지 시각적 표시 없음  
**원인**: `GET /api/meeting/state`가 `issue_tokens`(토픽별 누적 토큰)와 `issue_token_threshold`(500)를 이미 반환 중(routes.py:90-100). 프론트에서 이 값을 사용 안 함  
**수정**:
- `IssueCard.jsx`에 로딩바 추가: `pendingTokens / threshold * 100` %로 채우기
- `index.html`의 `<IssueCard>` 호출부에 `pendingTokens={state.issue_tokens?.[activeTopicId] || 0}` `tokenThreshold={state.issue_token_threshold || 500}` props 전달
- LLM 호출 중(pendingTokens === 0이고 직전에 임계치 도달)엔 스피너 표시

---

## [BUG] 화자 최대 155명 생성 ㅇ

**현상**: 화자 식별기가 새 화자를 무제한 등록해 `Speaker 155`까지 생김  
**원인**: `stt/speaker.py:67-71`에서 유사도 임계치(0.5) 미달 시 무조건 신규 화자 등록. `max_speakers` 설정(config.py:16 = 10)이 있으나 코드에서 전혀 체크 안 함  
**수정**:
1. `config.py` `speaker_similarity_threshold` 0.5 → 0.65로 상향
2. `speaker.py:identify()`에서 `speaker_count >= settings.max_speakers`이면 새 등록 대신 가장 유사도 높은 기존 화자에 할당 (임계치 미달이어도 best match 반환)

---

## [BUG] Whisper 반복 텍스트 할루시네이션 ㅇ

**현상**: 동일 단어/토큰이 수십 번 반복되는 STT 결과 발생. DB 실측 사례:
- `#603` Speaker 14: `welcome to the VIRT VIRT VIRT × 55회...` (378자)
- `#777` Speaker 6: `다음 회의 보러 vis vis vis × 200회...` (872자)
- 공통 패턴: **정상 텍스트로 시작 → 짧은 토큰이 뒤쪽에서 반복** (decoding loop)

**원인 (코드 분석 결과 4가지 복합)**:

1. **`condition_on_previous_text=True` (mlx_whisper 기본값)** — `venv/.../mlx_whisper/transcribe.py:71`. 이전 세그먼트 출력을 다음 윈도우 prompt로 사용해서 한 번 반복이 시작되면 고착됨. 공식 docstring도 "disabling makes the model less prone to getting stuck in a failure loop, such as repetition looping"라고 명시.

2. **VAD가 트레일링 묵음을 버퍼에 포함시킴** — `stt/whisper_stt.py:144-146`. 발화 종료 후에도 `silence_ms >= 800ms`가 될 때까지 묵음 청크를 계속 `_buffer.append(samples)` 함. 결과적으로 Whisper에 **speech + 800ms 묵음**이 전달됨. 트레일링 묵음에서의 할루시네이션은 Whisper의 잘 알려진 failure mode.

3. **fallback temperature가 소진되면 repetition 결과를 그대로 반환** — `mlx_whisper/transcribe.py:228-229`. `compression_ratio_threshold=2.4` 초과 시 temperature 체인 `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`로 재시도. 모두 실패하면 break 없이 마지막 결과 반환. 극단적 반복은 이 경로로 통과됨.

4. **후처리 필터 부재** — `whisper_stt.py:185-186`이 segments를 검증 없이 join. `analysis/correction.py`는 오타 교정만 하고 반복 패턴 검사 안 함.

**수정**:
1. `stt/whisper_stt.py:_process_utterance()`에서 `mlx_whisper.transcribe()` 호출 파라미터 추가
   - `condition_on_previous_text=False` — 반복 loop 억제 (1번 원인)
   - `compression_ratio_threshold=2.0` (기본 2.4 → 2.0) — 반복 detection 민감도 상향, 조기 fallback 유도 (3번 원인)
2. `feed_chunk()`에서 트레일링 묵음 trim — 버퍼 처리 전, 뒷쪽 연속 묵음 청크를 200ms만 남기고 버림 (2번 원인)
3. `_process_utterance()`에 반복 필터 추가 (4번 원인)
   - 같은 단어(공백 구분)가 4회 이상 연속 반복되면 반복 시작 지점 이전까지만 남김
   - 전체 utterance가 반복으로만 구성되면(정상 prefix가 2단어 미만) `return None`으로 드랍
   - 로그로 어떤 utterance가 잘렸는지 기록 (향후 임계치 튜닝용)

---

## [BUG] 반복 감지 알림 과다 발생 (999개) ㅇ

**현상**: 회의 중 `loop` 트리거 알림이 수백 개 생성됨  
**원인**: `triggers.py:_check_loop()`가 최근 10개 발화에서 같은 단어 3회 이상을 반복으로 판정. 회의 도메인 용어가 자연스럽게 반복돼도 루프로 오탐  
**수정**:
- `config.py` `loop_detection_count` 3 → 10으로 상향
- `triggers.py:_check_loop()` 윈도우 `[-10:]` → `[-20:]`으로 확장
- 동일 토픽에서 loop 알림이 이미 발생했으면 5분 쿨다운 (중복 알림 방지)

---

## [BUG] 알림 개수 교대로 1개/2개/1개 표시 ㅇ

**현상**: 알림이 1개 → 2개 → 1개 식으로 교대로 보임  
**원인**: WS `analysis` 메시지에서 `interventions: m.interventions || s.interventions`로 **전체 교체**. 서버가 매 발화마다 latest_interventions(최신 발화에서 감지된 것만)를 보내면 이전 알림이 덮어써짐  
**수정**:
- `index.html` WS 핸들러에서 interventions를 교체가 아닌 **누적(append)** 방식으로 변경
- 또는 서버 analysis 메시지에 누적 전체 목록을 포함하도록 `api/websocket.py` 수정

---

## [BUG] consensus/info_needed/silence/time_over 알림이 한 번도 안 뜸

**현상**: loop 외의 다른 트리거(합의 신호, 자료 부족, 침묵, 시간 초과) 알림이 전혀 표시 안 됨  
**원인 후보**:
- `_check_consensus` / `_check_info_needed` 키워드가 실제 발화에서 매칭 안 됨
- `_check_silence`는 `state.current_silence_ms`를 참조하는데, 이 값이 파이프라인에서 업데이트 안 되고 있을 가능성
- `_check_time_over`는 토픽 `start_time`이 null이면 `_time_diff_minutes`가 0을 반환
**조사 필요**: 각 `_check_*` 함수에 로그 추가해서 실제 호출/매칭 여부 확인

---

## [BUG] 웹 검색 미동작 ㅇ

**현상**: 회의 중 자료 검색이 전혀 안 됨, References 탭에 아무것도 안 뜸  
**원인**: `pipeline.py:_search_references()`가 `_has_disagreement()`가 True일 때만 실행. 쟁점 구조화에서 positions 2개 이상 + consensus 없음이어야 조건 충족  
**추가 원인**: `search/__init__.py:WebSearch`가 Tavily API 키 없으면 DuckDuckGo 폴백 사용, 하지만 DuckDuckGo도 네트워크/버전 이슈로 실패할 수 있음  
**조사 필요**:
- `MM_TAVILY_API_KEY` 환경변수 설정 여부 확인
- DuckDuckGo fallback 로그 확인 (`search/__init__.py`에 에러 로그 추가)
- `_has_disagreement()` 조건이 실제로 True가 되는지 확인

---

## [FEAT] AI 채팅 실제 구현 ㅇ

**현상**: 우측 채팅탭에서 질문하면 "백엔드 연결 시 AI가 회의 컨텍스트로 답변해요." 고정 문자열만 반환  
**원인**: `index.html:askAi()`가 `window.claude?.complete`에만 의존. 실제 API 엔드포인트 없음  
**수정**:
- `api/routes.py`에 `POST /api/meeting/ask` 엔드포인트 추가
  - 요청: `{ question: string }`
  - 처리: 최근 발화 20개를 컨텍스트로 `ask_json()` 또는 스트리밍 호출
  - 응답: `{ answer: string }`
- `index.html:askAi()`에서 `window.MM.api.ask(question)` 호출하도록 수정
- `static/app/api.js`에 `ask(question)` 메서드 추가

---

## [FEAT] 쟁점 구조화 하단 메모 입력창 ㅇ

**현상**: IssueCard 하단에 자유 메모를 남길 공간이 없음  
**수정**:
- DB: `notes` 테이블 추가 (`meeting_id`, `topic_id`, `text`, `created_at`)
- `db/__init__.py`: `save_note()`, `get_notes()` 함수 추가
- `api/routes.py`: `POST /api/meeting/notes` (저장), `GET /api/meeting/notes` (조회) 추가
- `IssueCard.jsx` 하단(RecordBar 위)에 메모 입력창 추가
  - textarea + 엔터 키로 저장
  - 저장된 메모는 IssueCard 안에 타임스탬프와 함께 리스트로 표시

---

## [FEAT] 사이드바 접기/펴기 이동 ㅇ

**현상**: 대화창(TranscriptPanel)에 접기/펴기 토글이 있는데 이게 왼쪽 사이드바(회의 히스토리)로 이동해야 함  
**수정**:
- `Chrome.jsx:Sidebar`에 collapse/expand 토글 버튼 추가 (접힌 상태: 48px 너비, 아이콘만 표시)
- `static/app/Transcript.jsx`에서 자체 토글 버튼 제거
- `index.html`에서 `transcriptOpen` 상태 → `sidebarOpen` 상태로 변경, Sidebar에 prop 전달

---

## [FEAT] TopBar 설정 아이콘 → 서버 로그 모달로 교체 ㅇ

**현상**: TopBar 우측에 설정 아이콘(기어)이 있고 LLM 모델 선택/초기화 모달이 열림  
**수정**:
- TopBar의 설정 아이콘 제거 (모델 설정은 다른 방법으로 접근하거나 유지)
- 대신 TopBar에 "로그" 아이콘 버튼 추가 → 클릭하면 작은 서버 로그 모달 표시
- 서버 로그 모달: `/ws/updates` WebSocket에서 수신한 로그를 스크롤 가능한 패널에 표시
  - 로그 레벨별 색상 (INFO=회색, WARNING=주황, ERROR=빨강)
  - 최대 200줄 유지, 자동 스크롤

---

## 15. 토픽 감지 묵음 체크 Dead Code 수정

**현재 문제**: `topic.py`의 stage 1에서 묵음(3초+)을 토픽 전환 후보로 판단하는 로직이 있으나, `_last_silence_ms`가 **항상 0**이라 실제로 작동하지 않음.

**수정 방향**:
- `pipeline.py`에서 `WhisperSTT`의 묵음 시간을 `TopicDetector`에 전달하는 경로 추가
- `_last_silence_ms` 업데이트 로직 구현

**관련 파일**: `analysis/topic.py`, `pipeline.py`, `stt/whisper_stt.py`

---

## 16. 루프 감지 오탐 개선 — 도메인 용어 반복 필터링

**현재 문제**: `triggers.py`의 `_check_loop()`가 최근 10개 발화에서 동일 단어 3회 이상 반복을 루프로 판정하는데, **도메인 핵심 용어의 정상적 반복을 루프로 오탐**할 수 있음.

**수정 방향**:
- 현재 토픽의 키워드를 동적 불용어로 추가
- 단순 단어 빈도가 아닌, 의미적 유사도 기반으로 개선

**관련 파일**: `analysis/triggers.py`, `config.py`

---

## 17. TTS 자료 요약 — 개입 타이밍 설계

**현재 문제**: TTS 트리거 조건이 정의되어 있으나 회의 흐름 방해 가능성 있음.

**수정 방향**:
- 개입 적합도 판단 로직 추가
- push형(자동 재생) vs pull형(알림만) 모드 선택

**관련 파일**: `pipeline.py`, `config.py`, `static/index.html`

---

## 12. 오디오 스트리밍-추론 파이프라인 오버랩 (레이턴시 최적화)

**현재 문제**: LLM 추론 중 새로 도착하는 오디오 패킷이 대기 상태로 블로킹됨.

**구현 방향**: 이중 버퍼 구조 + 비동기 수신 루프 분리

**관련 파일**: `api/websocket.py`, `stt/whisper_stt.py`, `pipeline.py`

---

## 13. Agentic STT 후처리 파이프라인 (음성 인식 정확도 개선)

**현재 문제**: STT 1차 출력의 동음이의어·전문 용어 오인식

**구현 방향**: LLM 기반 교정 모듈 + 도메인 용어 사전

**관련 파일**: `stt/post_processor.py` (신규), `config.py`, `pipeline.py`

---
---

## 11. TTS 기반 자료 요약 음성 안내

**목표**: 침묵/loop/info_needed 트리거 시 수집된 자료를 LLM 요약 → TTS 음성 출력

**관련 파일**: `tts/` (신규), `analysis/ref_summarizer.py` (신규), `pipeline.py`, `api/websocket.py`
