"""Whisper turbo fp16 vs 4bit 속도/품질 비교 (mlx-whisper 경로)."""
import time
import numpy as np
import soundfile as sf
import mlx_whisper

AUDIO_PATH = "/Users/edmin/Documents/MeetingMind/test_audio/test_16k_mono.wav"
FP16_REPO = "mlx-community/whisper-large-v3-turbo"
Q4_REPO = "mlx-community/whisper-large-v3-turbo-4bit"
N_RUNS = 3

audio, sr = sf.read(AUDIO_PATH)
duration = len(audio) / sr
audio = audio.astype(np.float32)
print(f"Audio: {duration:.1f}s @ {sr}Hz\n")


def bench(repo, label):
    print(f"=== {label} ({repo}) ===")
    print("Warmup...")
    t0 = time.time()
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=repo, language="ko", verbose=False)
    warmup = time.time() - t0
    text = " ".join(s["text"].strip() for s in result.get("segments", []))
    print(f"Warmup: {warmup:.2f}s (RTFx={duration/warmup:.1f}x)")

    times = []
    for i in range(N_RUNS):
        t0 = time.time()
        mlx_whisper.transcribe(audio, path_or_hf_repo=repo, language="ko", verbose=False)
        elapsed = time.time() - t0
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.2f}s (RTFx={duration/elapsed:.1f}x)")
    avg = sum(times) / len(times)
    return avg, duration / avg, text


fp16_avg, fp16_rtfx, fp16_text = bench(FP16_REPO, "fp16")
print()
q4_avg, q4_rtfx, q4_text = bench(Q4_REPO, "4bit")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"fp16 : avg={fp16_avg:.2f}s  RTFx={fp16_rtfx:.1f}x")
print(f"4bit : avg={q4_avg:.2f}s  RTFx={q4_rtfx:.1f}x")
speedup = fp16_avg / q4_avg
if speedup > 1:
    print(f"\n4bit is {speedup:.2f}x faster")
else:
    print(f"\nfp16 is {1/speedup:.2f}x faster")

# 품질 비교: 글자 수 기준 유사도
print("\n--- Text comparison (first 300 chars) ---")
print(f"fp16: {fp16_text[:300]}")
print(f"\n4bit: {q4_text[:300]}")
print(f"\nfp16 len: {len(fp16_text)}  |  4bit len: {len(q4_text)}")
