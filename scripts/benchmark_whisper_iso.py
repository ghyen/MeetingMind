"""프로세스 격리된 Whisper 벤치마크 — 한 번에 한 모델만 로드.

Usage:
    python benchmark_whisper_iso.py fp16
    python benchmark_whisper_iso.py 4bit
"""
import sys
import time
import json
import numpy as np
import soundfile as sf

AUDIO_PATH = "/Users/edmin/Documents/MeetingMind/test_audio/test_16k_mono.wav"
N_RUNS = 3
REPOS = {
    "fp16": "mlx-community/whisper-large-v3-turbo",
    "4bit": "mlx-community/whisper-large-v3-turbo-4bit",
}

mode = sys.argv[1]
repo = REPOS[mode]

audio, sr = sf.read(AUDIO_PATH)
duration = len(audio) / sr
print(f"[{mode}] Audio: {duration:.1f}s, Repo: {repo}")

from mlx_audio.stt.generate import generate_transcription

print(f"[{mode}] Warmup...")
t0 = time.time()
result = generate_transcription(
    model=repo,
    audio_path=AUDIO_PATH,
    verbose=False,
    format="txt",
    language="ko",
)
warmup = time.time() - t0
text = result.text if hasattr(result, "text") else (result["text"] if isinstance(result, dict) else str(result))
print(f"[{mode}] Warmup: {warmup:.2f}s (RTFx={duration/warmup:.1f}x)")
print(f"[{mode}] Sample: {text[:150]}")

times = []
for i in range(N_RUNS):
    t0 = time.time()
    generate_transcription(
        model=repo,
        audio_path=AUDIO_PATH,
        verbose=False,
        format="txt",
        language="ko",
    )
    e = time.time() - t0
    times.append(e)
    print(f"[{mode}] Run {i+1}: {e:.2f}s (RTFx={duration/e:.1f}x)")

avg = sum(times) / len(times)
result_data = {
    "mode": mode,
    "repo": repo,
    "duration": duration,
    "warmup": warmup,
    "runs": times,
    "avg": avg,
    "rtfx": duration / avg,
    "text_len": len(text),
    "text_sample": text[:500],
}
out_path = f"/Users/edmin/Documents/MeetingMind/benchmark_iso_{mode}.json"
with open(out_path, "w") as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)
print(f"\n[{mode}] Saved to {out_path}")
print(f"[{mode}] SUMMARY: avg={avg:.2f}s, RTFx={duration/avg:.1f}x")
