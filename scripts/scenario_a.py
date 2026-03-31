"""
시나리오 A: 스타트업 제품팀 스프린트 기획 회의

참석자:
  A — 김태호 (PM, 진행자)
  B — 박수진 (백엔드 개발)
  C — 이민준 (프론트엔드 개발)
  D — 정하은 (디자이너)

안건:
  1. 지난 스프린트 회고
  2. 결제 시스템 리팩토링 일정
  3. 신규 대시보드 UI 설계
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"

UTTERANCES = [
    # ── 안건 1: 지난 스프린트 회고 ──────────────────────────
    ("A", "00:00:05", "네 그럼 회의 시작하겠습니다. 오늘 스프린트 기획 회의인데요, 먼저 지난 스프린트 회고부터 하죠"),
    ("A", "00:00:18", "지난 스프린트에서 결제 모듈 안정화 작업 진행했었는데, 수진 씨 결과 공유해주시겠어요?"),
    ("B", "00:00:30", "네 결제 모듈 쪽은 카드사 연동 테스트까지 완료했고요, 근데 간헐적으로 타임아웃 나는 이슈가 아직 남아있어요"),
    ("B", "00:00:45", "로그 분석해보니까 PG사 응답이 3초 넘어가는 케이스가 하루에 열두 건 정도 발생하고 있습니다"),
    ("A", "00:00:58", "열두 건이면 전체 트랜잭션 대비 어느 정도 비율이에요?"),
    ("B", "00:01:08", "전체 일 평균 거래가 한 삼천 건 정도 되니까 0.4퍼센트 정도 됩니다"),
    ("A", "00:01:18", "0.4퍼센트면 좀 높긴 한데, 사용자 이탈로 이어지는 경우도 확인해봐야 할 것 같아요"),
    ("C", "00:01:30", "프론트 쪽에서 결제 실패 시 재시도 UX는 넣어뒀는데, 실제 재시도율 자료가 있나 봐야 할 것 같습니다"),
    ("A", "00:01:42", "좋습니다. 민준 씨 쪽 대시보드 마이그레이션은 어떻게 됐어요?"),
    # ── 안건 2: 결제 시스템 리팩토링 (토픽 전환 테스트) ────
    ("A", "00:02:30", "자 이제 다음 안건으로 넘어가서 결제 시스템 리팩토링 일정 이야기해보겠습니다"),
    ("A", "00:02:52", "좋습니다. 수고하셨습니다. 회의 마치겠습니다"),
]


async def run():
    async with httpx.AsyncClient(timeout=300) as client:
        # Ollama 로컬 모델로 전환
        resp = await client.post(f"{BASE_URL}/api/model", json={"provider": "ollama", "model": "qwen3.5:0.8b"})
        print(f"모델 전환: {resp.json()}\n")

        # 회의 시작
        resp = await client.post(f"{BASE_URL}/api/meeting/start", json={"title": "스프린트 기획 회의"})
        print(f"회의 시작: {resp.json()}\n")

        for speaker, time, text in UTTERANCES:
            resp = await client.post(
                f"{BASE_URL}/api/meeting/simulate",
                json={"speaker": speaker, "text": text, "time": time},
            )
            data = resp.json()
            topics = data.get("topics", [])
            interventions = data.get("interventions", [])
            current_topic = topics[-1]["title"] if topics else "(없음)"

            print(f"[{time}] {speaker}: {text}")
            if interventions:
                for iv in interventions:
                    print(f"  ⚡ [{iv['level']}] {iv['trigger_type']}: {iv['message']}")
            print()

            await asyncio.sleep(0.3)  # 서버 부하 방지

        # 회의 종료
        resp = await client.post(f"{BASE_URL}/api/meeting/end")
        print(f"\n회의 종료: {resp.json()}")

        # 최종 상태 조회
        resp = await client.get(f"{BASE_URL}/api/meeting/state")
        state = resp.json()
        print(f"\n=== 최종 요약 ===")
        print(f"총 발화: {len(state['utterances'])}건")
        print(f"토픽: {len(state['topics'])}개")
        for t in state["topics"]:
            print(f"  - [{t['id']}] {t['title']} ({t['start_time']} ~ {t.get('end_time', '진행중')})")
        print(f"개입 알림: {len(state['interventions'])}건")
        for iv in state["interventions"]:
            print(f"  - [{iv['level']}] {iv['trigger_type']}: {iv['message']}")


if __name__ == "__main__":
    asyncio.run(run())
