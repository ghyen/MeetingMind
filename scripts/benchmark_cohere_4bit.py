"""Cohere Transcribe MLX 4bit/8bit 단독 벤치마크."""
import sys
import time
import soundfile as sf
from mlx_audio.stt import load

AUDIO_PATH = "/Users/edmin/Documents/MeetingMind/test_audio/test_16k_mono.wav"
REPO = sys.argv[1] if len(sys.argv) > 1 else "beshkenadze/cohere-transcribe-03-2026-mlx-4bit"
N_RUNS = 3

audio, sr = sf.read(AUDIO_PATH)
duration = len(audio) / sr
print(f"Audio: {duration:.1f}s @ {sr}Hz")

print(f"\nLoading {REPO}...")
t0 = time.time()
model = load(REPO)
print(f"Load: {time.time()-t0:.2f}s")

print("Warmup...")
t0 = time.time()
out = model.generate(audio=AUDIO_PATH, language="ko", max_tokens=4096, verbose=False)
warmup = time.time() - t0
text = out.text if hasattr(out, "text") else str(out)
print(f"Warmup: {warmup:.2f}s (RTFx={duration/warmup:.1f}x)")
print(f"Sample text: {text[:200]}")

times = []
for i in range(N_RUNS):
    t0 = time.time()
    model.generate(audio=AUDIO_PATH, language="ko", max_tokens=4096, verbose=False)
    elapsed = time.time() - t0
    times.append(elapsed)
    print(f"Run {i+1}: {elapsed:.2f}s (RTFx={duration/elapsed:.1f}x)")

c_avg = sum(times) / len(times)
c_rtfx = duration / c_avg

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
w_avg = 10.25
w_rtfx = 18.2
print(f"Whisper turbo       : avg={w_avg:.2f}s  RTFx={w_rtfx:.1f}x")
print(f"Cohere ({REPO.split('/')[-1]}): avg={c_avg:.2f}s  RTFx={c_rtfx:.1f}x")
if c_avg < w_avg:
    print(f"\nCohere is {w_avg/c_avg:.2f}x faster")
else:
    print(f"\nWhisper is {c_avg/w_avg:.2f}x faster")

print("\n--- Cohere text ---")
print(text[:400])
