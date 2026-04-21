"""Whisper turbo fp16 (mlx-whisper) vs 4bit (mlx-audio) — 엔진이 다르지만 동일 오디오/언어로 속도 비교."""
import time
import numpy as np
import soundfile as sf
import mlx_whisper
from mlx_audio.stt import load

AUDIO_PATH = "/Users/edmin/Documents/MeetingMind/test_audio/test_16k_mono.wav"
FP16_REPO = "mlx-community/whisper-large-v3-turbo"
Q4_REPO = "mlx-community/whisper-large-v3-turbo-4bit"
N_RUNS = 3

audio, sr = sf.read(AUDIO_PATH)
duration = len(audio) / sr
audio_np = audio.astype(np.float32)
print(f"Audio: {duration:.1f}s @ {sr}Hz\n")


def bench_fp16():
    print(f"=== fp16 via mlx-whisper ({FP16_REPO}) ===")
    print("Warmup...")
    t0 = time.time()
    r = mlx_whisper.transcribe(audio_np, path_or_hf_repo=FP16_REPO, language="ko", verbose=False)
    print(f"Warmup: {time.time()-t0:.2f}s")
    text = " ".join(s["text"].strip() for s in r.get("segments", []))
    times = []
    for i in range(N_RUNS):
        t0 = time.time()
        mlx_whisper.transcribe(audio_np, path_or_hf_repo=FP16_REPO, language="ko", verbose=False)
        e = time.time() - t0
        times.append(e)
        print(f"Run {i+1}: {e:.2f}s (RTFx={duration/e:.1f}x)")
    avg = sum(times) / len(times)
    return avg, text


def bench_q4():
    print(f"\n=== 4bit via mlx-audio ({Q4_REPO}) ===")
    print(f"Loading...")
    t0 = time.time()
    model = load(Q4_REPO)
    print(f"Load: {time.time()-t0:.2f}s")

    print("Warmup...")
    t0 = time.time()
    out = model.generate(audio=AUDIO_PATH, language="ko", max_tokens=4096, verbose=False)
    print(f"Warmup: {time.time()-t0:.2f}s")
    text = out.text if hasattr(out, "text") else str(out)

    times = []
    for i in range(N_RUNS):
        t0 = time.time()
        model.generate(audio=AUDIO_PATH, language="ko", max_tokens=4096, verbose=False)
        e = time.time() - t0
        times.append(e)
        print(f"Run {i+1}: {e:.2f}s (RTFx={duration/e:.1f}x)")
    avg = sum(times) / len(times)
    return avg, text


fp16_avg, fp16_text = bench_fp16()
q4_avg, q4_text = bench_q4()

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"fp16 (mlx-whisper): avg={fp16_avg:.2f}s  RTFx={duration/fp16_avg:.1f}x")
print(f"4bit (mlx-audio)  : avg={q4_avg:.2f}s  RTFx={duration/q4_avg:.1f}x")
if q4_avg < fp16_avg:
    print(f"\n4bit is {fp16_avg/q4_avg:.2f}x faster")
else:
    print(f"\nfp16 is {q4_avg/fp16_avg:.2f}x faster")

print(f"\nfp16 len: {len(fp16_text)}  |  4bit len: {len(q4_text)}")
print(f"\n--- fp16 (first 300) ---\n{fp16_text[:300]}")
print(f"\n--- 4bit (first 300) ---\n{q4_text[:300]}")
