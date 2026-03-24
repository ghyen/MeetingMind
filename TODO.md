# MeetingMind TODO

## 종합 테스트 결과 기반 (2026-03-24)

테스트: `scripts/scenario_full.py` — 53발화, Ollama qwen3.5:9b (no-think)
총 소요: 1272초 (21분), 발화당 평균 24초

---

### 백엔드 버그/이슈

#### ~~1. 쟁점 구조화 속도 병목~~ (수정됨)
- batch size 3→5, 프롬프트 최근 15개 발화로 제한, Ollama 시 순차 실행
- `config.py`에 `llm_provider` 추가 (#5도 함께 해결)

#### ~~2. 토픽 전환 "넘어가서" 누락~~ (수정됨)
- `_llm_judge()` 프롬프트에 wrap-up 표현 새 토픽 분류 지시 추가
- 강한 키워드 2개+ 동시 매칭 시 `_force_transition()`으로 LLM 스킵하여 전환 확정

#### ~~3. 입장(position) 과다 분해~~ (수정됨)
- `_create_initial()`, `_apply_delta()` 프롬프트에 "같은 화자 병합", "최대 5개" 제약 추가

#### ~~4. no_decision 알림 반복~~ (수정됨)
- `_emitted_no_decision` set으로 동일 토픽 1회만 발동
- 프론트에서도 같은 타입+토픽 중복 필터링

---

### 기능 개선

#### ~~5. Ollama 기본 프로바이더 설정~~ (수정됨 — #1과 함께)
- `config.py`에 `llm_provider` 필드 추가, `llm.py`에서 `settings.llm_provider`로 초기화
- `.env`에 `MM_LLM_PROVIDER=ollama` 설정 가능

#### ~~6. LLM 요약 품질 개선~~ (수정됨)
- 프롬프트에 품질 가이드라인 추가: "topic 10자 이내", "stance에 구체적 수치/사실"
- few-shot 예시(`_FEW_SHOT_EXAMPLE`) 추가하여 출력 형식 유도
- consensus/decision 타입 명시 (문자열 또는 null)

#### ~~7. 테스트 스크립트 에러 수정~~ (수정됨)
- `str(ig.get('consensus',''))[:60]`, `str(ig.get('decision',''))[:60]`으로 안전 변환

---

#### ~~10. 웹 검색(자료 수집) 실패~~ (해결됨)
- 프롬프트 few-shot 예시 추가, 빈 query 폴백, WebSearch 빈 query 차단

---

### UI 개선

#### ~~8. 토픽 전환 시 UI에 4번째 토픽(마무리) 탭 미표시~~ (수정됨)
- `_llm_judge()` 프롬프트에 wrap-up/마무리 표현을 새 토픽으로 분류하도록 지시 추가

#### ~~9. no_decision 알림이 우측 패널을 가득 채우는 문제~~ (수정됨)
- 백엔드: `TriggerDetector`에 `_emitted_no_decision` set 추가하여 동일 토픽 재발동 방지
- 프론트: `renderNewInterventions()`에서 같은 타입+토픽 중복 알림 필터링

---

### 미통과 항목 → 모두 수정 완료

| 항목 | 관련 TODO | 상태 |
|---|---|---|
| 토픽 전환 "넘어가서" 누락 | #2 | ✓ 수정됨 |
| 입장 과다 분해 (15개) | #3 | ✓ 수정됨 |
| no_decision 알림 반복 | #4 | ✓ 수정됨 |
| 쟁점 구조화 속도 (60~120초/발화) | #1 | ✓ 수정됨 |
| 웹 검색 자료 수집 0건 | #10 | ✓ 이전 해결 |
| LLM 요약 품질 (토픽명 과장, 입장 추상적) | #6 | ✓ 수정됨 |
