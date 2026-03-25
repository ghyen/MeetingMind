"""
3자 회의: 마케팅 캠페인 리뷰 (20발화)

참석자: A(팀장), B(마케터), C(디자이너)
안건: 1) 지난 캠페인 성과 → 2) 다음 캠페인 방향
테스트: 토픽 전환, 합의, 정보 부족, 엔티티 추출, 웹 검색, 쟁점 구조화, 화자 3명
"""

import asyncio
import time
import httpx

BASE_URL = "http://localhost:8000"

UTTERANCES = [
    # ── 안건 1: 지난 캠페인 성과 리뷰 ──
    ("A", "00:00:05", "오늘은 지난 분기 마케팅 캠페인 성과 리뷰하고 다음 분기 방향 잡겠습니다"),
    ("A", "00:00:15", "먼저 지난 인스타그램 캠페인 결과 공유해주세요"),
    ("B", "00:00:30", "인스타그램 리드 캠페인 CTR이 2.3퍼센트였고 전환율은 1.1퍼센트입니다"),
    ("B", "00:00:45", "근데 Google Ads 쪽은 CTR 0.8퍼센트밖에 안 나왔어요. GA4 데이터를 확인해봐야 할 것 같습니다"),
    ("C", "00:01:00", "배너 디자인이 A/B 테스트에서 B안이 클릭률 40퍼센트 높았는데 전환은 비슷했어요"),
    ("A", "00:01:15", "전환율이 비슷하면 크리에이티브 문제보다 랜딩페이지 문제 아닌가요?"),
    ("B", "00:01:30", "맞아요. 랜딩페이지 이탈률 자료가 있나 봐야 할 것 같습니다"),
    ("C", "00:01:45", "동의합니다"),

    # ── 안건 2: 다음 캠페인 방향 ──
    ("A", "00:02:00", "자 이제 다음 안건으로 넘어가서 다음 분기 캠페인 방향 논의하겠습니다"),
    ("B", "00:02:15", "저는 TikTok 숏폼 중심으로 가야 한다고 봅니다. MZ세대 도달률이 인스타 대비 3배입니다"),
    ("C", "00:02:30", "근데 TikTok은 브랜드 이미지 컨트롤이 어려워요. 저는 인스타 릴스 강화가 낫다고 생각합니다"),
    ("B", "00:02:45", "TikTok 광고 단가가 인스타 대비 절반이에요. 예산 효율성을 봐야죠"),
    ("C", "00:03:00", "예산이 아니라 브랜드 톤앤매너가 중요합니다. TikTok 컨텐츠는 우리 브랜드랑 안 맞아요"),
    ("A", "00:03:15", "둘 다 일리가 있네요. 그러면 예산 70퍼센트는 인스타 릴스, 30퍼센트는 TikTok 테스트로 가는 건 어떨까요"),
    ("B", "00:03:30", "그렇게 하죠"),
    ("C", "00:03:35", "동의합니다"),

    # ── 마무리 ──
    ("A", "00:03:45", "그건 그렇고 마지막으로 정리하면 다음 분기는 인스타 릴스 70퍼센트 TikTok 30퍼센트로 확정합니다"),
    ("A", "00:03:55", "랜딩페이지 개선은 C가 다음 주까지 시안 잡아주세요"),
    ("C", "00:04:05", "네 알겠습니다"),
    ("A", "00:04:10", "수고하셨습니다"),
]


async def run():
    start = time.time()
    async with httpx.AsyncClient(timeout=300) as client:
        await client.post(f"{BASE_URL}/api/model", json={"provider": "ollama", "model": "qwen3.5:9b"})
        resp = await client.post(f"{BASE_URL}/api/meeting/start", json={"title": "마케팅 캠페인 리뷰"})
        print(f"회의 시작: {resp.json()}\n")

        for i, (spk, ts, text) in enumerate(UTTERANCES, 1):
            t0 = time.time()
            resp = await client.post(
                f"{BASE_URL}/api/meeting/simulate",
                json={"speaker": spk, "text": text, "time": ts},
            )
            data = resp.json()
            ivs = data.get("interventions", [])
            topics = data.get("topics", [])
            topic = topics[-1]["title"] if topics else "-"
            print(f"[{i:02d}] [{ts}] {spk}: {text[:55]}{'...' if len(text)>55 else ''}")
            for iv in ivs:
                print(f"     ⚡ [{iv['level']}] {iv['trigger_type']}: {iv['message'][:60]}")
            print(f"     topic={topic} | {time.time()-t0:.1f}s\n")
            await asyncio.sleep(0.2)

        await client.post(f"{BASE_URL}/api/meeting/end")

        # 결과 조회
        state = (await client.get(f"{BASE_URL}/api/meeting/state")).json()
        elapsed = time.time() - start

        print(f"{'='*50}")
        print(f" 결과 ({elapsed:.0f}초)")
        print(f"{'='*50}")
        print(f"발화: {len(state['utterances'])}건")
        print(f"토픽: {len(state['topics'])}개")
        for t in state["topics"]:
            print(f"  #{t['id']} {t['title']} ({t['start_time']}~{t.get('end_time','')}) [{len(t.get('utterances',[]))}발화]")
        print(f"쟁점: {len(state['issues'])}개")
        for tid, ig in state["issues"].items():
            if ig:
                print(f"  #{tid} {ig.get('topic','')}: {len(ig.get('positions',[]))}입장, consensus={ig.get('consensus','N/A')}")
        print(f"알림: {len(state['interventions'])}건")
        for iv in state["interventions"]:
            print(f"  [{iv['level']}] {iv['trigger_type']}: {iv['message'][:60]}")
        print(f"참고자료: {len(state['references'])}건")
        for r in state["references"][:5]:
            print(f"  [{r['source']}] {r['title'][:40]}")


if __name__ == "__main__":
    asyncio.run(run())
