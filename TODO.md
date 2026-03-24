# MeetingMind TODO

## 종합 테스트 결과 기반 (2026-03-24)

테스트: `scripts/scenario_full.py` — 53발화, Ollama qwen3.5:9b (no-think)
총 소요: 1272초 (21분), 발화당 평균 24초

---

### 백엔드 버그/이슈

#### 1. 쟁점 구조화 속도 병목
- **현상**: 쟁점 구조화(IssueStructurer)가 트리거되는 발화에서 60~120초 소요
- **원인**: `_create_initial()`과 `_apply_delta()`가 전체 발화 내용을 프롬프트에 포함 → 토큰 수가 많아 Ollama 응답이 느림. 또한 `asyncio.gather`로 토픽 감지/쟁점/엔티티를 병렬 호출하지만 Ollama는 직렬 처리라 순차 대기 발생
- **개선 방향**:
  - 프롬프트 길이 제한 (최근 N개 발화만 포함)
  - batch size를 3 → 5로 늘려서 호출 빈도 감소
  - Ollama 사용 시 병렬 호출 대신 순차 호출로 변경 검토
- **파일**: `analysis/issues.py`, `pipeline.py`

#### 2. 토픽 전환 "넘어가서" 누락
- **현상**: "자 이제 마무리로 넘어가서 이번 스프린트 할 일을 정리하겠습니다"가 토픽 전환으로 감지 안됨
- **원인**: `topic_keywords`에 "넘어가서"가 있어 `_is_trigger()`는 통과하지만, `_llm_judge()`에서 LLM이 "마무리 정리"를 새 토픽이 아닌 현재 토픽의 연장으로 판단
- **개선 방향**:
  - LLM 프롬프트 개선 — "마무리", "정리" 같은 wrap-up도 별도 토픽으로 분류하도록 유도
  - 또는 키워드 매칭만으로 토픽 전환 확정하는 옵션 추가
- **파일**: `analysis/topic.py`

#### 3. 입장(position) 과다 분해
- **현상**: 토픽2에서 15개 입장 생성 — 발화 하나하나를 별도 입장으로 쪼개버림
- **원인**: `_apply_delta()`에서 "업데이트된 전체 JSON을 반환하세요"라고만 하니까 LLM이 발화를 병합하지 않고 추가만 함
- **개선 방향**:
  - 프롬프트에 "같은 화자의 입장은 병합하세요", "최대 5개 이내로 유지하세요" 등 제약 추가
  - `_apply_delta()` 프롬프트를 더 명확하게 수정
- **파일**: `analysis/issues.py`

#### 4. no_decision 알림 반복
- **현상**: 토픽 전환 후 매 발화마다 "이전 안건에 결정 없음" 알림이 계속 출력
- **원인**: `_check_no_decision()`이 `state.topics`에 2개 이상 있고 이전 토픽에 decision이 없으면 매번 발동
- **개선 방향**: 한 번 발동 후 동일 토픽에 대해 재발동하지 않도록 `_emitted_no_decision` set 추가
- **파일**: `analysis/triggers.py`

---

### 기능 개선

#### 5. Ollama 기본 프로바이더 설정
- **현상**: 서버 reload 시 `_active_provider`가 `"openrouter"`로 초기화되어 Ollama로 전환한 설정이 날아감
- **개선 방향**: `.env`에서 기본 프로바이더를 설정할 수 있도록 `config.py`에 `llm_provider` 필드 추가
- **파일**: `config.py`, `analysis/llm.py`

#### 6. LLM 요약 품질 개선
- **현상**: qwen3.5:9b (no-think)로 쟁점 구조화 시 토픽명이 과도하게 길고, 입장 설명이 추상적
- **개선 방향**:
  - 프롬프트에 "토픽명은 10자 이내", "입장은 구체적 수치/사실 포함" 등 품질 가이드라인 추가
  - few-shot 예시를 프롬프트에 포함
- **파일**: `analysis/issues.py`, `analysis/topic.py`

#### 7. 테스트 스크립트 에러 수정
- **현상**: `scenario_full.py` 검증 출력에서 `consensus`가 dict일 때 `[:60]` 슬라이싱 에러
- **수정**: `str(ig.get('consensus',''))[:60]`으로 안전하게 변환
- **파일**: `scripts/scenario_full.py`

---

#### 10. 웹 검색(자료 수집) 실패
- **현상**: Tavily 검색에서 `"Query is missing"` 에러 → DuckDuckGo 폴백도 실패 → 참고자료 0건
- **원인**: `EntityExtractor`가 LLM으로 엔티티 추출 시 `search_query`가 빈 문자열로 반환됨. qwen3.5:9b (no-think)가 프롬프트의 JSON 스키마를 정확히 따르지 못하는 것으로 추정
- **개선 방향**:
  - `EntityExtractor` 프롬프트 개선 — few-shot 예시 추가, query 필드에 대한 명확한 설명
  - `search_query`가 비어있으면 `entity.text`를 query로 폴백
  - 빈 query로 Tavily 호출하지 않도록 validation 추가
- **파일**: `search/__init__.py`

---

### UI 개선

#### 8. 토픽 전환 시 UI에 4번째 토픽(마무리) 탭 미표시
- 백엔드에서 토픽 4가 생성 안되는 문제 해결 후 자동 해결

#### 9. no_decision 알림이 우측 패널을 가득 채우는 문제
- 백엔드에서 중복 발동 방지 후 자동 해결, 또는 프론트에서 같은 타입의 알림 중복 표시 제한

---

### 테스트 결과 요약

| 항목 | 통과 |
|---|---|
| 첫 토픽 자동 생성 | O |
| 토픽 전환 "다음 안건" | O |
| 토픽 전환 "그건 그렇고" | O |
| 토픽 전환 "넘어가서" | X (LLM 판단 실패) |
| consensus 정상 감지 | O |
| consensus 오탐 방지 | O |
| info_needed 감지 | O |
| loop 감지 + 불용어 필터링 | O |
| 시간 초과 감지 | O |
| 결론 없이 전환 감지 | O |
| 쟁점 구조화 | O (품질 보통) |
| end_time 설정 | O |
