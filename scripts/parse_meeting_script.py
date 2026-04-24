"""test_meeting_script.md → meeting_script.json 자동 변환.

발화 추출 규칙:
  - `**화자명**: 발화` 패턴만 발화로 인식 (주석, 헤더, 체크리스트 제외)
  - `[5초 침묵 — ...]` 지시문 직전 발화에 pause_after_ms=5500 설정
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SPEAKER_PATTERN = re.compile(r"^\*\*(김팀장|이리드|박재무|최기획)\*\*:\s*(.+)$")
SILENCE_PATTERN = re.compile(r"\[5초 침묵")

VOICES: dict[str, str] = {
    "김팀장": "ko-KR-InJoonNeural",
    "이리드": "ko-KR-HyunsuMultilingualNeural",
    "박재무": "ko-KR-SunHiNeural",
    "최기획": "en-US-EmmaMultilingualNeural",  # edge-tts는 한국어 여성이 SunHi 1명뿐 → 다국어 여성 voice 사용
}

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_MD = ROOT / "test_meeting_script.md"
SCRIPT_JSON = ROOT / "scripts" / "meeting_script.json"


def parse(md_path: Path) -> dict:
    utterances: list[dict] = []
    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue

        m = SPEAKER_PATTERN.match(line)
        if m:
            utterances.append({"speaker": m.group(1), "text": m.group(2).strip()})
            continue

        if SILENCE_PATTERN.search(line) and utterances:
            utterances[-1]["pause_after_ms"] = 5500

    return {"voices": VOICES, "utterances": utterances}


def main() -> None:
    result = parse(SCRIPT_MD)
    SCRIPT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    n = len(result["utterances"])
    silences = sum(1 for u in result["utterances"] if "pause_after_ms" in u)
    by_speaker: dict[str, int] = {}
    for u in result["utterances"]:
        by_speaker[u["speaker"]] = by_speaker.get(u["speaker"], 0) + 1

    print(f"✅ 발화 {n}개 추출")
    print(f"   5초 침묵 삽입 지점: {silences}개")
    for spk, cnt in sorted(by_speaker.items(), key=lambda x: -x[1]):
        print(f"   {spk}: {cnt}개")
    print(f"✅ 출력: {SCRIPT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
