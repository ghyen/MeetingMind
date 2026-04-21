"""Whisper large-v3-turbo vs Cohere Transcribe Mixed-3bit4bit 속도 비교."""
import time
import numpy as np
import soundfile as sf

AUDIO_PATH = "/Users/edmin/Documents/MeetingMind/test_audio/test_16k_mono.wav"
WHISPER_REPO = "mlx-community/whisper-large-v3-turbo"
COHERE_REPO = "MarkChen1214/cohere-transcribe-03-2026-MLX-Mixed-3bit4bit"
N_RUNS = 3


def load_audio():
    audio, sr = sf.read(AUDIO_PATH)
    assert sr == 16000, f"Expected 16kHz, got {sr}"
    audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, len(audio) / sr


def bench_whisper(audio, duration):
    import mlx_whisper
    print("\n=== Whisper large-v3-turbo ===")
    print("Warmup...")
    t0 = time.time()
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_REPO, language="ko", verbose=False)
    warmup = time.time() - t0
    text = " ".join(s["text"].strip() for s in result.get("segments", []))
    print(f"Warmup: {warmup:.2f}s")
    print(f"Sample text: {text[:120]}...")

    times = []
    for i in range(N_RUNS):
        t0 = time.time()
        mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_REPO, language="ko", verbose=False)
        elapsed = time.time() - t0
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.2f}s (RTFx={duration/elapsed:.1f}x)")

    avg = sum(times) / len(times)
    return avg, duration / avg, text


def bench_cohere(audio, duration):
    from mlx_audio.stt import load
    print("\n=== Cohere Transcribe Mixed-3bit4bit ===")
    print(f"Loading {COHERE_REPO}...")
    t0 = time.time()
    model, processor = load(COHERE_REPO)
    load_time = time.time() - t0
    print(f"Load: {load_time:.2f}s")

    print("Warmup...")
    t0 = time.time()
    result = model.generate(audio=AUDIO_PATH)
    warmup = time.time() - t0
    text = result.get("text", "") if isinstance(result, dict) else str(result)
    print(f"Warmup: {warmup:.2f}s")
    print(f"Sample text: {text[:120]}...")

    times = []
    for i in range(N_RUNS):
        t0 = time.time()
        model.generate(audio=AUDIO_PATH)
        elapsed = time.time() - t0
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.2f}s (RTFx={duration/elapsed:.1f}x)")

    avg = sum(times) / len(times)
    return avg, duration / avg, text


def main():
    audio, duration = load_audio()
    print(f"Audio: {duration:.1f}s @ 16kHz mono")

    w_avg, w_rtfx, w_text = bench_whisper(audio, duration)
    c_avg, c_rtfx, c_text = bench_cohere(audio, duration)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Whisper turbo : avg={w_avg:.2f}s  RTFx={w_rtfx:.1f}x")
    print(f"Cohere 3/4bit : avg={c_avg:.2f}s  RTFx={c_rtfx:.1f}x")
    speedup = w_avg / c_avg
    faster = "Cohere" if speedup > 1 else "Whisper"
    print(f"\n{faster} is {max(speedup, 1/speedup):.2f}x faster")

    print("\n--- Text comparison (first 200 chars) ---")
    print(f"Whisper: {w_text[:200]}")
    print(f"Cohere : {c_text[:200]}")


if __name__ == "__main__":
    main()
