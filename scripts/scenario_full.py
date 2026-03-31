"""
종합 시나리오: 스타트업 제품팀 스프린트 기획 회의 (50발화)

테스트 목표:
  - 토픽 전환 감지 (키워드 3종: "다음 안건", "그건 그렇고", "넘어가서")
  - 첫 토픽 자동 생성
  - 쟁점 구조화 (찬반 대립 → 합의 도출)
  - 합의 감지 (consensus): "동의합니다", "그렇게 하죠"
  - 합의 오탐 방지: "좋습니다. ~" 뒤에 긴 문장
  - 정보 부족 감지 (info_needed): "확인해봐야", "자료가 있나"
  - 논의 순환 감지 (loop): 같은 주제 반복
  - 불용어 필터링: "정도", "합니다" 등 일반 단어 미감지
  - 엔티티 추출: 문서명, 수치, 인물, 조직 등
  - 시간 초과 감지: 안건 10분+ (타임스탬프 조작)
  - 결론 없이 전환 감지: 이전 안건 decision=None

참석자:
  A — 김태호 (PM, 진행자)
  B — 박수진 (백엔드 개발)
  C — 이민준 (프론트엔드 개발)
  D — 정하은 (디자이너)
"""

import asyncio
import json
import time
import httpx

BASE_URL = "http://localhost:8000"

UTTERANCES = [
    # ══════════════════════════════════════════════════════════
    # 안건 1: 지난 스프린트 회고 (00:00 ~ 04:00)
    # 테스트: 첫 토픽 자동 생성, 엔티티 추출(PG사, 카드사), 정보 부족
    # ══════════════════════════════════════════════════════════
    ("A", "00:00:05", "네 그럼 회의 시작하겠습니다. 오늘 스프린트 기획 회의인데요, 먼저 지난 스프린트 회고부터 하죠"),
    ("A", "00:00:18", "지난 스프린트에서 결제 모듈 안정화 작업 진행했었는데, 수진 씨 결과 공유해주시겠어요?"),
    ("B", "00:00:35", "네 결제 모듈 쪽은 카드사 연동 테스트까지 완료했고요, 근데 간헐적으로 타임아웃 나는 이슈가 아직 남아있어요"),
    ("B", "00:00:50", "로그 분석해보니까 PG사 응답이 3초 넘어가는 케이스가 하루에 열두 건 정도 발생하고 있습니다"),
    ("A", "00:01:05", "열두 건이면 전체 트랜잭션 대비 어느 정도 비율이에요?"),
    # 테스트: info_needed ("확인해봐야")
    ("B", "00:01:18", "전체 일 평균 거래가 한 삼천 건 정도 되니까 0.4퍼센트 정도 됩니다"),
    ("A", "00:01:30", "0.4퍼센트면 좀 높긴 한데, 사용자 이탈로 이어지는 경우도 확인해봐야 할 것 같아요"),
    # 테스트: info_needed ("자료가 있나")
    ("C", "00:01:45", "프론트 쪽에서 결제 실패 시 재시도 UX는 넣어뒀는데, 실제 재시도율 자료가 있나 봐야 할 것 같습니다"),
    # 테스트: consensus 오탐 방지 — "좋습니다" 뒤에 긴 문장
    ("A", "00:02:00", "좋습니다. 민준 씨 쪽 대시보드 마이그레이션은 어떻게 됐어요?"),
    ("C", "00:02:15", "Vue에서 React로 전환하는 거 80퍼센트 정도 끝났고요, 차트 컴포넌트만 남았는데 이게 좀 까다로워서 이번 스프린트로 넘어왔습니다"),
    # 테스트: 엔티티 추출 (Figma)
    ("D", "00:02:30", "차트 컴포넌트 디자인은 저도 수정 사항이 있어요. Figma에 업데이트해둘 테니까 반영 전에 한번 봐주세요"),
    ("C", "00:02:45", "네 알겠습니다. Figma 링크 슬랙으로 보내주세요"),
    # 테스트: 짧은 합의 (consensus 정상 감지)
    ("A", "00:03:00", "그러면 차트 컴포넌트 마무리는 이번 스프린트에서 끝내는 걸로 합의하겠습니다"),
    ("B", "00:03:10", "동의합니다"),
    ("C", "00:03:15", "네 그렇게 하죠"),

    # ══════════════════════════════════════════════════════════
    # 안건 2: 결제 시스템 리팩토링 (04:00 ~ 15:00)
    # 테스트: 토픽 전환 ("다음 안건"), 찬반 대립, 합의 도출
    #         시간 초과 (10분+ 안건), 엔티티 추출 (CTO, DevOps)
    # ══════════════════════════════════════════════════════════
    ("A", "00:04:00", "자 이제 다음 안건으로 넘어가서 결제 시스템 리팩토링 일정 이야기해보겠습니다"),
    ("A", "00:04:15", "CTO님이 이번 분기 안에 결제 아키텍처 전면 리팩토링하자고 하셨는데, 현실적으로 가능한 일정이 어떻게 될까요"),
    # 테스트: 반대 입장
    ("B", "00:04:35", "솔직히 전면 리팩토링은 이번 분기에 무리라고 봅니다. 최소 6주는 걸릴 것 같은데 남은 기간이 5주밖에 안 돼요"),
    ("A", "00:04:50", "6주면 좀 빡빡하네요. 단계적으로 나눠서 할 수는 없나요?"),
    ("B", "00:05:10", "단계적으로 하면 첫 번째로 PG사 추상화 레이어 먼저 만들고, 두 번째로 결제 상태 머신 리팩토링, 세 번째로 정산 모듈 분리하는 순서가 맞을 것 같습니다"),
    ("B", "00:05:30", "1단계 PG사 추상화만 이번 분기에 끝내고 나머지는 다음 분기로 넘기는 게 현실적입니다"),
    ("C", "00:05:50", "프론트에서도 결제 플로우 변경되면 UI 작업이 필요한데, 리팩토링 일정이 명확해야 저도 계획을 세울 수 있어요"),
    ("A", "00:06:10", "그러면 1단계 PG사 추상화 레이어를 이번 스프린트에서 설계하고 다음 스프린트에서 구현하는 건 어떨까요"),
    ("B", "00:06:30", "설계까지는 이번 스프린트에 가능합니다. 근데 구현은 다음 스프린트에서 시작하려면 테스트 환경부터 세팅해야 하는데"),
    # 테스트: 엔티티 추출 (DevOps팀, 스테이징)
    ("B", "00:06:50", "테스트 환경 세팅이 관건이에요. DevOps팀에 스테이징 환경에 PG 샌드박스 연동 요청해야 합니다"),
    ("A", "00:07:10", "알겠습니다. 그러면 이번 스프린트는 설계 문서 작성, DevOps 요청까지 하고 다음 스프린트부터 구현 시작하는 걸로 합의하면 될까요"),
    # 테스트: 합의 정상 감지
    ("B", "00:07:25", "네 동의합니다"),
    ("C", "00:07:30", "저도 동의합니다"),
    # 테스트: 논의 순환 — 결제 리팩토링 같은 키워드 반복
    ("A", "00:08:00", "근데 결제 리팩토링 하면서 기존 결제 API 하위 호환성은 어떻게 하죠?"),
    ("B", "00:08:20", "결제 API 하위 호환은 당연히 유지해야죠. 결제 쪽 인터페이스는 바꾸면 안 됩니다"),
    ("C", "00:08:40", "결제 쪽 API 스펙이 바뀌면 결제 화면 전부 다시 테스트해야 하는데요"),
    ("A", "00:09:00", "결제 API 스펙은 유지하는 걸로 확정합시다"),
    ("B", "00:09:15", "그렇게 하죠"),
    # 테스트: 시간 초과 (안건 시작 04:00 → 현재 15:00 = 11분 경과)
    ("A", "00:15:00", "이 안건에 시간을 너무 많이 쓴 것 같네요. 마무리하겠습니다"),

    # ══════════════════════════════════════════════════════════
    # 안건 3: 신규 대시보드 UI 설계 (15:30 ~ 22:00)
    # 테스트: 토픽 전환 ("그건 그렇고"), 결론 없이 전환 감지 가능,
    #         쟁점 구조화 (A안/B안/C안 비교)
    # ══════════════════════════════════════════════════════════
    ("A", "00:15:30", "그건 그렇고 신규 대시보드 UI 설계 건으로 넘어가겠습니다"),
    ("A", "00:15:45", "하은 씨가 1차 시안 준비해오셨다고 들었는데, 공유 부탁드립니다"),
    ("D", "00:16:00", "네 Figma에 올려뒀는데요, 크게 세 가지 방향으로 시안을 잡았어요"),
    ("D", "00:16:15", "A안은 기존 레이아웃 유지하면서 카드형 위젯으로 정보 밀도를 높인 거고요"),
    ("D", "00:16:30", "B안은 좌측 네비게이션을 접을 수 있게 해서 메인 영역을 넓힌 디자인이에요"),
    ("D", "00:16:45", "C안은 완전히 새로운 구조로 탭 기반 네비게이션에 드래그 앤 드롭 커스터마이징이 가능한 형태입니다"),
    ("A", "00:17:00", "세 가지 다 장단점이 있을 것 같은데, 일단 개발 공수 관점에서 민준 씨 의견은요?"),
    ("C", "00:17:20", "A안이 공수가 가장 적고요 한 2주면 되고, B안은 3주, C안은 드래그 앤 드롭 때문에 한 5주는 잡아야 합니다"),
    # 테스트: 엔티티 추출 (사용자 리서치)
    ("D", "00:17:40", "저도 B안 추천이에요. 사용자 리서치에서도 화면이 좁다는 피드백이 가장 많았거든요"),
    ("B", "00:17:55", "백엔드 API 관점에서는 세 안 다 큰 차이 없습니다. B안으로 가시죠"),
    # 테스트: consensus 정상 감지
    ("A", "00:18:10", "그러면 B안으로 합의된 거로 하겠습니다"),
    ("D", "00:18:25", "네 금요일까지 상세 시안이랑 컴포넌트 가이드까지 정리해서 올리겠습니다"),

    # ══════════════════════════════════════════════════════════
    # 안건 4: 마무리 (22:00 ~)
    # 테스트: 토픽 전환 ("넘어가서"), 전체 요약
    # ══════════════════════════════════════════════════════════
    ("A", "00:22:00", "자 이제 마무리로 넘어가서 이번 스프린트 할 일을 정리하겠습니다"),
    ("A", "00:22:15", "정리하면 이번 스프린트에서 할 일은 결제 리팩토링 설계 문서, DevOps 요청, 대시보드 B안 상세 시안, 차트 컴포넌트 마이그레이션 마무리입니다"),
    ("A", "00:22:30", "다들 이의 없으시면 이걸로 스프린트 백로그 확정하겠습니다"),
    ("B", "00:22:38", "이의 없습니다"),
    ("C", "00:22:42", "동의합니다"),
    ("D", "00:22:46", "저도 좋습니다"),
    ("A", "00:22:55", "좋습니다. 수고하셨습니다. 회의 마치겠습니다"),
]

# ── 기대 결과 ──────────────────────────────────────────────
EXPECTED = {
    "min_topics": 4,            # 회의 시작 + 결제 리팩토링 + UI 설계 + 마무리
    "topic_titles_contain": ["결제", "대시보드"],
    "consensus_min": 3,         # 동의합니다 x 여러 건
    "info_needed_min": 2,       # 확인해봐야 + 자료가 있나
    "false_consensus": "좋습니다. 민준",  # 이게 consensus로 잡히면 안 됨
    "loop_keyword": "결제",     # 결제가 loop으로 감지
    "no_loop_stopwords": ["정도", "합니다"],  # 불용어 미감지
}


async def run():
    start_time = time.time()

    async with httpx.AsyncClient(timeout=300) as client:
        # Ollama 로컬 모델로 전환
        resp = await client.post(f"{BASE_URL}/api/model", json={"provider": "ollama", "model": "qwen3.5:0.8b"})
        print(f"모델 전환: {resp.json()}\n")

        # 회의 시작
        resp = await client.post(f"{BASE_URL}/api/meeting/start", json={"title": "스프린트 기획 회의 (종합 테스트)"})
        print(f"회의 시작: {resp.json()}\n")

        for i, (speaker, ts, text) in enumerate(UTTERANCES, 1):
            t0 = time.time()
            resp = await client.post(
                f"{BASE_URL}/api/meeting/simulate",
                json={"speaker": speaker, "text": text, "time": ts},
            )
            elapsed = time.time() - t0
            data = resp.json()
            topics = data.get("topics", [])
            interventions = data.get("interventions", [])

            topic_label = topics[-1]["title"] if topics else "-"
            print(f"[{i:02d}/{len(UTTERANCES)}] [{ts}] {speaker}: {text[:60]}{'...' if len(text)>60 else ''}")
            if interventions:
                for iv in interventions:
                    print(f"         ⚡ [{iv['level']}] {iv['trigger_type']}: {iv['message'][:80]}")
            print(f"         topic={topic_label} | {elapsed:.1f}s")
            print()

            await asyncio.sleep(0.2)

        # 회의 종료
        resp = await client.post(f"{BASE_URL}/api/meeting/end")
        print(f"\n회의 종료: {resp.json()}")

        # 최종 상태 조회
        resp = await client.get(f"{BASE_URL}/api/meeting/state")
        state = resp.json()

        total_time = time.time() - start_time

        # ── 결과 출력 ──────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  종합 테스트 결과 (총 {total_time:.0f}초)")
        print(f"{'='*60}\n")

        # 발화
        print(f"[발화] 총 {len(state['utterances'])}건")

        # 토픽
        topics = state["topics"]
        print(f"\n[토픽] {len(topics)}개")
        for t in topics:
            utt_count = len(t.get("utterances", []))
            print(f"  #{t['id']} {t['title']} ({t['start_time']} ~ {t.get('end_time') or '진행중'}) [{utt_count}발화]")

        # 쟁점
        issues = state["issues"]
        print(f"\n[쟁점] {len(issues)}개 토픽에 대해 구조화됨")
        for tid, ig in issues.items():
            if ig:
                positions = ig.get("positions", [])
                print(f"  토픽#{tid} '{ig.get('topic','')}': {len(positions)}개 입장")
                for p in positions:
                    print(f"    [{p['speaker']}] {p['stance'][:50]}")
                if ig.get("consensus"):
                    print(f"    ✓ 합의: {str(ig.get('consensus', ''))[:60]}")
                if ig.get("decision"):
                    print(f"    ✓ 결정: {str(ig.get('decision', ''))[:60]}")
                if ig.get("open_questions"):
                    print(f"    ? 미결: {', '.join(ig['open_questions'][:3])}")

        # 개입 알림
        interventions = state["interventions"]
        print(f"\n[개입 알림] 총 {len(interventions)}건")
        by_type = {}
        for iv in interventions:
            by_type.setdefault(iv["trigger_type"], []).append(iv)
        for tt, items in by_type.items():
            print(f"  {tt}: {len(items)}건")
            for item in items[:3]:
                print(f"    - [{item['level']}] {item['message'][:70]}")
            if len(items) > 3:
                print(f"    ... 외 {len(items)-3}건")

        # 참고자료
        refs = state["references"]
        print(f"\n[참고자료] {len(refs)}건")
        for r in refs[:5]:
            print(f"  [{r['source']}] {r['title'][:40]} (score:{r.get('relevance_score',0):.2f})")

        # ── 자동 검증 ──────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  자동 검증")
        print(f"{'='*60}\n")

        passed = 0
        failed = 0

        def check(name, condition, detail=""):
            nonlocal passed, failed
            if condition:
                passed += 1
                print(f"  ✓ PASS: {name}")
            else:
                failed += 1
                print(f"  ✗ FAIL: {name} {detail}")

        # 1. 토픽 수
        check("토픽 >= 4개", len(topics) >= EXPECTED["min_topics"],
              f"(실제: {len(topics)}개)")

        # 2. 토픽명에 키워드 포함
        all_titles = " ".join(t["title"] for t in topics)
        for kw in EXPECTED["topic_titles_contain"]:
            check(f"토픽명에 '{kw}' 포함", kw in all_titles, f"(titles: {all_titles})")

        # 3. 첫 토픽 자동 생성
        check("첫 토픽 자동 생성", len(topics) > 0 and topics[0]["start_time"] == "00:00:05",
              f"(first: {topics[0]['start_time'] if topics else 'N/A'})")

        # 4. consensus 감지
        consensus_count = sum(1 for iv in interventions if iv["trigger_type"] == "consensus")
        check(f"consensus >= {EXPECTED['consensus_min']}건",
              consensus_count >= EXPECTED["consensus_min"],
              f"(실제: {consensus_count}건)")

        # 5. consensus 오탐 방지
        false_hit = any(
            iv["trigger_type"] == "consensus" and EXPECTED["false_consensus"] in iv["message"]
            for iv in interventions
        )
        check("consensus 오탐 방지 ('좋습니다. 민준~')", not false_hit)

        # 6. info_needed 감지
        info_count = sum(1 for iv in interventions if iv["trigger_type"] == "info_needed")
        check(f"info_needed >= {EXPECTED['info_needed_min']}건",
              info_count >= EXPECTED["info_needed_min"],
              f"(실제: {info_count}건)")

        # 7. loop 감지 with 결제 키워드
        loop_msgs = [iv["message"] for iv in interventions if iv["trigger_type"] == "loop"]
        has_loop_kw = any(EXPECTED["loop_keyword"] in m for m in loop_msgs)
        check(f"loop 감지 ('{EXPECTED['loop_keyword']}' 키워드)", has_loop_kw,
              f"(loop msgs: {len(loop_msgs)}건)")

        # 8. 불용어 미감지
        for sw in EXPECTED["no_loop_stopwords"]:
            sw_in_loop = any(sw in m.split("키워드: ")[-1] if "키워드:" in m else False for m in loop_msgs)
            check(f"불용어 '{sw}' loop 미감지", not sw_in_loop)

        # 9. 시간 초과 감지
        time_over = any(iv["trigger_type"] == "time_over" for iv in interventions)
        check("시간 초과 감지 (10분+)", time_over)

        # 10. 쟁점 구조화 존재
        has_issues = any(ig is not None for ig in issues.values())
        check("쟁점 구조화 1개 이상", has_issues)

        # 11. 토픽 전환 시 end_time 설정
        ended_topics = [t for t in topics if t.get("end_time")]
        check("토픽 end_time 설정 (1개 이상)", len(ended_topics) >= 1,
              f"(ended: {len(ended_topics)}개)")

        print(f"\n  결과: {passed} passed, {failed} failed / {passed+failed} total")
        print(f"  소요: {total_time:.0f}초 ({total_time/len(UTTERANCES):.1f}초/발화)")

        # ── LLM 요약 품질 평가 ─────────────────────────────
        print(f"\n{'='*60}")
        print(f"  LLM 요약 품질 평가 (qwen3.5:0.8b no-think)")
        print(f"{'='*60}\n")

        for tid, ig in issues.items():
            if not ig:
                continue
            print(f"  [토픽 #{tid}] {ig.get('topic','')}")
            print(f"  입장 수: {len(ig.get('positions',[]))}개")
            for p in ig.get("positions", []):
                args = p.get("arguments", [])
                print(f"    {p['speaker']}: {p['stance'][:50]} (근거 {len(args)}개)")
            consensus = ig.get("consensus")
            decision = ig.get("decision")
            oq = ig.get("open_questions", [])
            print(f"  합의: {consensus or '없음'}")
            print(f"  결정: {decision or '없음'}")
            print(f"  미결: {oq or '없음'}")

            # 품질 점수 (간이)
            score = 0
            if ig.get("positions"):
                score += 2
            if len(ig.get("positions", [])) >= 2:
                score += 1
            if consensus:
                score += 2
            if decision:
                score += 2
            if oq:
                score += 1
            if any(p.get("arguments") for p in ig.get("positions", [])):
                score += 2
            print(f"  품질 점수: {score}/10")
            print()


if __name__ == "__main__":
    asyncio.run(run())
