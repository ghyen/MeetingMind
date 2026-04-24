"""TTS 오디오를 MeetingMind 파이프라인에 업로드하여 end-to-end 실측.

사용법:
    # 1) 서버 실행 (별도 터미널):
    #    MM_TIME_OVER_ALERT_MIN=4.0 ./venv/bin/python main.py 2>&1 | tee logs/server.log
    # 2) 이 스크립트 실행:
    ./venv/bin/python scripts/run_audio_test.py

동작:
  - test_audio/meeting_tts.wav 업로드 → STT → 파이프라인 전체 처리
  - 완료 후 새로 생성된 meeting_id 출력 → analyze_meeting_log.py 입력으로
  - 파이프라인 전체 경과 시간 측정

전제: 서버가 http://localhost:8000에서 실행 중
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
AUDIO_PATH = ROOT / "test_audio" / "meeting_tts.wav"
BASE_URL = "http://localhost:8000"


async def main() -> None:
    if not AUDIO_PATH.exists():
        sys.exit(f"❌ 오디오 없음: {AUDIO_PATH}\n   먼저 generate_meeting_audio.py 실행")

    size_mb = AUDIO_PATH.stat().st_size / (1024 * 1024)
    print(f"📄 업로드 대상: {AUDIO_PATH.name} ({size_mb:.1f} MB)\n")

    async with httpx.AsyncClient(timeout=3600) as client:
        # 1. 서버 헬스 체크
        try:
            r = await client.get(f"{BASE_URL}/api/meetings")
        except httpx.ConnectError:
            sys.exit(f"❌ 서버 연결 실패: {BASE_URL}\n   서버를 먼저 실행하세요.")
        prev_ids = {m["id"] for m in r.json()["meetings"]}
        print(f"✅ 서버 응답 — 기존 회의 {len(prev_ids)}건\n")

        # 2. 업로드 (STT + 파이프라인 전체 동기 처리)
        print(f"📤 업로드 시작 — LLM 호출 포함해서 수~수십 분 소요 가능\n")
        t0 = time.time()
        with open(AUDIO_PATH, "rb") as f:
            resp = await client.post(
                f"{BASE_URL}/api/meeting/upload",
                files={"file": (AUDIO_PATH.name, f, "audio/wav")},
            )
        elapsed = time.time() - t0

        if resp.status_code != 200:
            sys.exit(f"❌ 업로드 실패 ({resp.status_code}): {resp.text[:500]}")

        result = resp.json()
        print(f"✅ 업로드/처리 완료 ({elapsed:.1f}초)")
        if "error" in result:
            sys.exit(f"❌ 서버 내부 오류: {result['error']}")
        n_utt = len(result.get("utterances", []))
        print(f"   응답 utterances: {n_utt}개\n")
        if n_utt == 0:
            print("⚠️  STT가 0개 발화 반환 — 원인 확인 필요 (서버 로그 참고)\n")

        # 3. 새 meeting_id 확인
        r2 = await client.get(f"{BASE_URL}/api/meetings")
        new_meetings = [m for m in r2.json()["meetings"] if m["id"] not in prev_ids]
        if not new_meetings:
            sys.exit("⚠️  새 회의가 생성되지 않았습니다. 업로드 응답 확인 필요.")

        m = new_meetings[0]
        print(f"🆔 회의 ID: {m['id']}")
        print(f"   제목: {m['title']}")
        print(f"   시작: {m['started_at']}")
        print(f"   종료: {m.get('ended_at') or '진행중'}")

        # 4. 요약 통계 (빠른 확인용)
        state_resp = await client.get(f"{BASE_URL}/api/meeting/state")
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"\n📊 즉시 집계:")
            print(f"   발화: {len(state.get('utterances', []))}개")
            print(f"   토픽: {len(state.get('topics', []))}개")
            print(f"   트리거: {len(state.get('interventions', []))}건")

        print(f"\n➡️  다음 단계:")
        print(f"   ./venv/bin/python scripts/analyze_meeting_log.py --meeting-id {m['id']}")


if __name__ == "__main__":
    asyncio.run(main())
