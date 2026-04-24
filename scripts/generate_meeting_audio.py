"""edge-tts로 회의 오디오 생성.

파이프라인:
  1. scripts/meeting_script.json 로드
  2. 각 발화를 화자별 voice_id로 TTS → mp3
  3. pydub로 concat (자연 간격 + 지정 silence 구간 삽입)
  4. 16kHz mono wav 저장 → stt.from_file() 입력 포맷 맞춤

사용법:
    python scripts/generate_meeting_audio.py
"""
from __future__ import annotations

import asyncio
import json
import random
import tempfile
from pathlib import Path

import edge_tts
from pydub import AudioSegment

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_JSON = ROOT / "scripts" / "meeting_script.json"
OUTPUT_WAV = ROOT / "test_audio" / "meeting_tts.wav"

# 발화 간 자연 간격 (ms)
PAUSE_MIN_MS = 700
PAUSE_MAX_MS = 1500
# 고정 시드 (재현성)
SEED = 42


async def synthesize(text: str, voice: str, out_path: Path, retries: int = 3) -> None:
    """edge-tts 합성 + 짧은 텍스트 workaround + 재시도."""
    # edge-tts는 3자 미만 텍스트에서 NoAudioReceived 자주 발생 → 패딩
    padded = text.strip()
    if len(padded) < 3:
        padded = f"{padded} 네."

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(padded, voice)
            await communicate.save(str(out_path))
            return
        except Exception as e:  # NoAudioReceived 포함 모든 네트워크/합성 오류
            last_err = e
            await asyncio.sleep(1.0)
    raise RuntimeError(f"TTS 실패 ({retries}회 재시도) — 텍스트: {text!r}, 마지막 오류: {last_err}")


async def main() -> None:
    script = json.loads(SCRIPT_JSON.read_text(encoding="utf-8"))
    voices: dict[str, str] = script["voices"]
    utterances: list[dict] = script["utterances"]

    tmpdir = Path(tempfile.mkdtemp(prefix="mm_tts_"))
    print(f"📁 임시 디렉터리: {tmpdir}")
    print(f"🎙️  TTS 생성 시작 — 발화 {len(utterances)}개\n")

    audios: list[AudioSegment] = []
    for idx, u in enumerate(utterances):
        voice = voices[u["speaker"]]
        mp3 = tmpdir / f"{idx:03d}.mp3"
        await synthesize(u["text"], voice, mp3)
        seg = AudioSegment.from_mp3(mp3)
        audios.append(seg)
        dur = len(seg) / 1000
        preview = u["text"][:50].replace("\n", " ")
        print(f"[{idx + 1:>3}/{len(utterances)}] {u['speaker']:<3} {dur:>5.1f}s  {preview}")

    # 합성 — 자연 간격 + 지정 silence
    rng = random.Random(SEED)
    final = AudioSegment.empty()
    for u, seg in zip(utterances, audios):
        # 발화 전 자연 간격 (첫 발화는 0)
        pause_before = 0 if len(final) == 0 else rng.randint(PAUSE_MIN_MS, PAUSE_MAX_MS)
        pause_after_extra = u.get("pause_after_ms", 0)

        final += AudioSegment.silent(duration=pause_before)
        final += seg
        if pause_after_extra > 0:
            final += AudioSegment.silent(duration=pause_after_extra)

    # 16kHz mono → 파이프라인 입력 포맷
    final = final.set_frame_rate(16000).set_channels(1)
    OUTPUT_WAV.parent.mkdir(parents=True, exist_ok=True)
    final.export(str(OUTPUT_WAV), format="wav")

    total_sec = len(final) / 1000
    total_min = total_sec / 60
    print()
    print(f"✅ 생성 완료: {OUTPUT_WAV.relative_to(ROOT)}")
    print(f"   총 길이: {total_min:.1f}분 ({total_sec:.0f}초)")
    print(f"   발화 수: {len(utterances)}개")
    print(f"   샘플레이트: 16000 Hz mono")


if __name__ == "__main__":
    asyncio.run(main())
