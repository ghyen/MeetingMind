"""실측 분석 — meeting_id 기반으로 DB + 서버 로그에서 발표용 수치 추출.

출력:
  1. 화자 분리 결과 (발화 분포)
  2. 토픽 감지 경로 A/B/C 분포 (로그 기반)
  3. 쟁점 구조화 결과 (positions, consensus)
  4. 개입 트리거 6종 발동 여부
  5. 자료 수집 결과
  6. _StepTimer 단계별 시간 분포 (로그 기반)
  7. 📊 발표용 핵심 수치 요약

사용법:
    ./venv/bin/python scripts/analyze_meeting_log.py                        # 가장 최근 회의
    ./venv/bin/python scripts/analyze_meeting_log.py --meeting-id 24        # 특정 회의
    ./venv/bin/python scripts/analyze_meeting_log.py --log logs/server.log  # 다른 로그 파일
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "meetingmind.db"
DEFAULT_LOG = ROOT / "logs" / "server.log"

TRIGGER_TYPES = ["consensus", "info_needed", "no_decision", "loop", "silence", "time_over"]

# _StepTimer 로그 패턴
# 예: "[파이프라인 발화#7] 총 1.23초 | DB저장 0.01s (1%) | ..."
STEPTIMER_PATTERN = re.compile(
    r"\[파이프라인 발화#(\d+)\]\s*총\s*([\d.]+)초\s*\|\s*(.+)"
)
STEP_KV_PATTERN = re.compile(r"([가-힣A-Za-z_]+):\s+([\d.]+)s\s*\(\d+%\)")

# 토픽 감지 경로 추정 (analysis/topic.py 로그 관점)
# — 실제 서버 로그에 경로별 명시 로그가 없으면 이 부분은 "추정"으로 표시
TOPIC_LLM_PATTERN = re.compile(r"(토픽|topic).*?(LLM|gemma|ollama|ask_json)", re.IGNORECASE)


# ── DB 조회 ──────────────────────────────────────────────────────────────


def fetch_meeting(meeting_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    m = c.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
    if not m:
        sys.exit(f"❌ meeting_id={meeting_id} 없음. --meeting-id 생략 시 가장 최근 회의 자동 선택됨.")

    return {
        "meeting": dict(m),
        "utterances": [dict(u) for u in c.execute(
            "SELECT * FROM utterances WHERE meeting_id=? ORDER BY id", (meeting_id,)
        )],
        "topics": [dict(t) for t in c.execute(
            "SELECT * FROM topics WHERE meeting_id=? ORDER BY id", (meeting_id,)
        )],
        "interventions": [dict(i) for i in c.execute(
            "SELECT * FROM interventions WHERE meeting_id=? ORDER BY id", (meeting_id,)
        )],
        "issues": [dict(i) for i in c.execute(
            "SELECT * FROM issues WHERE meeting_id=? ORDER BY id", (meeting_id,)
        )],
        "refs": [dict(r) for r in c.execute(
            "SELECT * FROM refs WHERE meeting_id=? ORDER BY id", (meeting_id,)
        )],
    }


def latest_meeting_id() -> int | None:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id FROM meetings ORDER BY id DESC LIMIT 1").fetchone()
    return row[0] if row else None


# ── 로그 파싱 ────────────────────────────────────────────────────────────


def parse_log(log_path: Path) -> dict:
    """_StepTimer 로그 + 토픽 감지 LLM 로그 추출."""
    if not log_path.exists():
        return {"available": False, "reason": f"로그 파일 없음: {log_path}"}

    steps_by_utt: dict[int, dict[str, float]] = {}
    totals: list[float] = []
    topic_llm_hits = 0

    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = STEPTIMER_PATTERN.search(line)
        if m:
            utt_no = int(m.group(1))
            total = float(m.group(2))
            steps_str = m.group(3)
            totals.append(total)
            step_dict: dict[str, float] = {}
            for kv in STEP_KV_PATTERN.finditer(steps_str):
                step_dict[kv.group(1)] = float(kv.group(2))
            steps_by_utt[utt_no] = step_dict
            continue

        if TOPIC_LLM_PATTERN.search(line):
            topic_llm_hits += 1

    return {
        "available": True,
        "steps_by_utt": steps_by_utt,
        "totals": totals,
        "topic_llm_hits": topic_llm_hits,
    }


# ── 리포트 출력 ──────────────────────────────────────────────────────────


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def report(data: dict, log: dict) -> None:
    m = data["meeting"]
    U = data["utterances"]
    T = data["topics"]
    I = data["interventions"]
    S = data["issues"]
    R = data["refs"]

    # 헤더
    section(f"회의 #{m['id']}: {m['title'] or '(제목 없음)'}")
    print(f"  시작: {m['started_at']}")
    print(f"  종료: {m.get('ended_at') or '진행중'}")
    print(f"  오디오: {m.get('audio_path') or '-'}")

    # 1. 화자 분리
    section("1. 화자 분리")
    speakers = Counter(u["speaker"] for u in U)
    print(f"  총 발화: {len(U)}개")
    print(f"  감지된 화자: {len(speakers)}명")
    for spk, cnt in speakers.most_common():
        pct = cnt / len(U) * 100 if U else 0
        print(f"    {spk:<15} {cnt:>3}개  ({pct:.0f}%)")

    # 2. 토픽 감지
    section("2. 토픽 감지")
    print(f"  감지된 토픽: {len(T)}개")
    for t in T:
        # 토픽 내 발화 수 (해당 topic 시작~종료 시간대)
        print(f"  #{t['id']:<3} '{t['title']}' ({t['start_time']} ~ {t['end_time'] or '진행중'})")

    # 토픽 감지 경로 분포는 명시적 로그가 없으면 추정만
    if log["available"]:
        print(f"\n  토픽 감지 LLM 호출 (로그 기반 추정): {log['topic_llm_hits']}회")
        print(f"  → 발화 {len(U)}개 중 {log['topic_llm_hits']}/{len(U)} ({log['topic_llm_hits']/len(U)*100:.1f}%)가 LLM fallback 경유")

    # 3. 쟁점 구조화
    section("3. 쟁점 구조화")
    print(f"  쟁점 구조 생성: {len(S)}개 (= 쟁점 구조화 LLM 호출 횟수)")
    for s in S:
        try:
            ig = json.loads(s["issue_graph_json"])
        except Exception:
            ig = {}
        positions = ig.get("positions", [])
        decision = ig.get("decision")
        consensus = ig.get("consensus")
        print(f"  토픽#{s['topic_id']:<3} positions={len(positions)}, consensus={'✓' if consensus else '-'}, decision={'✓' if decision else '-'}")
        for p in positions[:3]:
            stance = p.get("stance", "")
            print(f"             [{p.get('speaker','?')}] {stance[:55]}")

    # 4. 개입 트리거
    section("4. 개입 트리거 (목표: 6종 모두 발동)")
    by_type = Counter(i["trigger_type"] for i in I)
    hits = 0
    for tt in TRIGGER_TYPES:
        cnt = by_type.get(tt, 0)
        status = "✅" if cnt > 0 else "❌"
        if cnt > 0:
            hits += 1
        print(f"  {status} {tt:<15} {cnt}건")
    print(f"\n  커버리지: {hits}/6 ({hits/6*100:.0f}%)")

    if I:
        print(f"\n  발동 타임라인:")
        for i in I:
            msg = (i["message"] or "")[:55]
            print(f"    [{i['time']}] {i['trigger_type']:<12} ({i['level']:<8}) {msg}")

    # 5. 자료 수집
    section("5. 자료 수집 (부동의 게이트)")
    print(f"  수집 건수: {len(R)}건")
    sources = Counter(r["source"] for r in R)
    for src, cnt in sources.most_common():
        print(f"    {src}: {cnt}건")
    for r in R[:5]:
        title = (r.get("title") or "")[:50]
        print(f"    [{r['source']:<10}] {title} (score={r.get('relevance_score', 0):.2f})")

    # 6. _StepTimer
    section("6. 단계별 처리 시간 (_StepTimer)")
    if not log["available"]:
        print(f"  ⚠️  {log['reason']}")
        print(f"  → 서버를 `python main.py 2>&1 | tee logs/server.log`로 실행 후 재측정 권장")
    elif not log["totals"]:
        print(f"  ⚠️  _StepTimer 로그 없음 (서버 실행 중 발화 없음 or 다른 포맷)")
    else:
        totals = log["totals"]
        print(f"  측정된 발화: {len(totals)}개")
        print(f"  발화 당 총 처리 시간:")
        print(f"    평균  {mean(totals):.2f}s")
        print(f"    중앙  {median(totals):.2f}s")
        print(f"    최소  {min(totals):.2f}s")
        print(f"    최대  {max(totals):.2f}s")

        # 단계별 평균
        all_step_names: set[str] = set()
        for steps in log["steps_by_utt"].values():
            all_step_names.update(steps.keys())

        if all_step_names:
            print(f"\n  단계별 평균 시간:")
            for name in sorted(all_step_names):
                values = [s.get(name, 0) for s in log["steps_by_utt"].values()]
                avg = mean(values) if values else 0
                avg_pct = avg / mean(totals) * 100 if totals else 0
                print(f"    {name:<12} {avg*1000:>6.0f}ms  ({avg_pct:>4.1f}%)")

    # 7. 발표용 요약
    section("📊 발표용 핵심 수치")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   📥 입력   발화 {len(U)}개, 화자 {len(speakers)}명, 토픽 {len(T)}개")
    print(f"   ⚡ 트리거 {hits}/6 종 발동 ({', '.join(tt for tt in TRIGGER_TYPES if by_type.get(tt, 0) > 0)})")
    print(f"   🧠 LLM    쟁점 구조화 {len(S)}회" + (f", 토픽 감지 추정 {log['topic_llm_hits']}회" if log['available'] else ""))
    print(f"   📚 검색   자료 수집 {len(R)}건 (부동의 게이트 통과)")

    # LLM 절감률 계산
    baseline = len(U) * 3  # 발화당 3 LLM 단순 가정
    actual = len(S)
    if log["available"]:
        actual += log["topic_llm_hits"]
    saved_pct = (1 - actual / baseline) * 100 if baseline else 0
    print(f"   💰 LLM 호출 절감")
    print(f"       baseline (발화당 3 LLM): {baseline}회")
    print(f"       실측                   : {actual}회")
    print(f"       절감률                  : {saved_pct:.1f}%")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ── 메인 ─────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meeting-id", type=int, help="분석할 meeting_id (생략 시 가장 최근)")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG, help=f"서버 로그 경로 (기본: {DEFAULT_LOG})")
    args = ap.parse_args()

    if args.meeting_id is None:
        args.meeting_id = latest_meeting_id()
        if args.meeting_id is None:
            sys.exit("❌ 회의 데이터 없음. 먼저 run_audio_test.py로 회의를 생성하세요.")
        print(f"[자동] 가장 최근 회의 선택: #{args.meeting_id}")

    data = fetch_meeting(args.meeting_id)
    log_data = parse_log(args.log)
    report(data, log_data)


if __name__ == "__main__":
    main()
