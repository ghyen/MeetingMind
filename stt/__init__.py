"""STT 모듈 — 오디오 캡처, VAD, 음성인식, 화자 분리.

흐름: 오디오 입력 → VAD → 청크 분할 → STT 엔진 → 화자 분리 → Utterance
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from config import settings
from models import Utterance


# ── 오디오 캡처 ────────────────────────────────────────────────


class AudioCapture:
    """마이크 또는 파일에서 오디오를 청크 단위로 캡처."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * settings.audio_chunk_ms / 1000)
        self._running = False

    async def from_microphone(self) -> AsyncIterator[bytes]:
        """마이크에서 실시간 오디오 스트림."""
        # TODO: pyaudio/sounddevice로 구현
        self._running = True
        while self._running:
            await asyncio.sleep(settings.audio_chunk_ms / 1000)
            yield b""

    async def from_file(self, file_path: str) -> AsyncIterator[bytes]:
        """녹음 파일에서 오디오 청크 스트림 (MVP용)."""
        # TODO: soundfile/pydub로 구현
        yield b""

    def stop(self) -> None:
        self._running = False


# ── VAD ────────────────────────────────────────────────────────


class VADFilter:
    """음성 활동 감지 — 무음 구간 필터링 (silero-vad)."""

    def __init__(self) -> None:
        self.threshold = settings.vad_threshold
        self._model = None

    def load_model(self) -> None:
        # TODO: torch.hub.load('snakers4/silero-vad', 'silero_vad')
        pass

    def is_speech(self, audio_chunk: bytes) -> bool:
        # TODO: silero-vad 추론
        return True


# ── STT 엔진 베이스 ────────────────────────────────────────────


class BaseSTT(ABC):
    @abstractmethod
    def load_model(self) -> None: ...

    @abstractmethod
    async def transcribe_chunk(self, audio_chunk: bytes) -> Utterance | None: ...


def create_engine() -> BaseSTT:
    """설정에 따라 STT 엔진 인스턴스 반환."""
    if settings.stt_engine == "faster_whisper":
        from stt.whisper import FasterWhisperSTT
        return FasterWhisperSTT()
    from stt.sensevoice import SenseVoiceSTT
    return SenseVoiceSTT()


# ── 화자 분리 ──────────────────────────────────────────────────


class Diarizer:
    """화자 분리 — sherpa-onnx 내장 diarization 또는 pyannote."""

    def load_model(self) -> None:
        # TODO: sherpa-onnx 또는 pyannote 모델 로드
        pass

    async def identify_speaker(self, audio_chunk: bytes) -> str:
        # TODO: 화자 식별
        return "unknown"
