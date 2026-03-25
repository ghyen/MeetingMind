"""STT 모듈 — 오디오 캡처, VAD, 화자 분리.

사용 조합: SenseVoice-Small (STT) + sherpa-onnx (스트리밍/화자분리)
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import numpy as np

from config import settings
from models import Utterance


# ── 오디오 캡처 ────────────────────────────────────────────────


class AudioCapture:
    """마이크 또는 파일에서 오디오를 청크 단위로 캡처."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * settings.audio_chunk_ms / 1000)
        self._running = False

    async def from_file(self, file_path: str) -> AsyncIterator[bytes]:
        """녹음 파일에서 오디오 청크 스트림.

        지원 포맷: wav, flac, ogg, mp3, aiff, m4a, webm 등 (audio_converter 참조)
        자동으로 16kHz mono float32로 변환.
        """
        from audio_converter import convert_file

        data = convert_file(file_path)

        # yield chunks
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i : i + self.chunk_size]
            yield chunk.astype(np.float32).tobytes()
            await asyncio.sleep(0)  # yield control

    async def from_microphone(self) -> AsyncIterator[bytes]:
        """마이크에서 실시간 오디오 스트림."""
        import sounddevice as sd

        queue: asyncio.Queue[bytes] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            loop.call_soon_threadsafe(
                queue.put_nowait, indata[:, 0].astype(np.float32).tobytes()
            )

        self._running = True
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_size,
            callback=callback,
        )
        stream.start()
        try:
            while self._running:
                chunk = await queue.get()
                yield chunk
        finally:
            stream.stop()
            stream.close()

    def stop(self) -> None:
        self._running = False


# ── VAD ────────────────────────────────────────────────────────


class VADFilter:
    """음성 활동 감지 — 무음 구간 필터링 (silero-vad via sherpa-onnx)."""

    def __init__(self) -> None:
        self.threshold = settings.vad_threshold
        self._model = None
        self._window_size = 512  # silero-vad window for 16kHz
        self._silence_ms = 0

    def load_model(self) -> None:
        import sherpa_onnx

        config = sherpa_onnx.VadModelConfig(
            silero_vad=sherpa_onnx.SileroVadModelConfig(
                model=settings.vad_model_path,
                threshold=self.threshold,
            ),
            sample_rate=16000,
        )
        self._model = sherpa_onnx.VadModel.create(config)
        self._window_size = self._model.window_size()

    def is_speech(self, audio_chunk: bytes) -> bool:
        """audio_chunk(float32 PCM bytes) → 음성 여부."""
        if self._model is None:
            return True

        samples = np.frombuffer(audio_chunk, dtype=np.float32)

        # silero-vad는 고정 윈도우 크기(512 @ 16kHz)로 처리
        speech_detected = False
        for i in range(0, len(samples) - self._window_size + 1, self._window_size):
            window = samples[i : i + self._window_size].tolist()
            if self._model.is_speech(window):
                speech_detected = True
                break

        if speech_detected:
            self._silence_ms = 0
        else:
            self._silence_ms += settings.audio_chunk_ms

        return speech_detected

    def get_silence_duration_ms(self) -> int:
        """현재 연속 무음 시간(ms)."""
        return self._silence_ms
