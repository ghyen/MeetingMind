"""whisper.cpp 기반 STT adapter.

- WhisperCppFileSTT: 파일 업로드(batch) 전용
- WhisperCppRealtimeSTT: 기존 RMS VAD/버퍼링을 재사용하고, 발화 완성 시 whisper-cli 호출
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from config import settings
from models import Utterance
from stt.speaker import SpeakerIdentifier
from stt.whisper_stt import WhisperSTT


def _format_time(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class _WhisperCppMixin:
    def __init__(self) -> None:
        self._speaker_id = SpeakerIdentifier()
        self._speaker_loaded = False

    def _ensure_speaker_model(self) -> None:
        if settings.diarization_enabled and not self._speaker_loaded:
            self._speaker_id.load()
            self._speaker_loaded = True

    def _run_whisper_cpp(self, audio_data: np.ndarray, sample_rate: int = 16000) -> list[dict]:
        model_path = Path(settings.whisper_cpp_model_path).expanduser()
        if not model_path.exists():
            raise FileNotFoundError(f"whisper.cpp 모델이 없습니다: {model_path}")

        with tempfile.TemporaryDirectory(prefix="meetingmind-whispercpp-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            wav_path = tmpdir_path / "input.wav"
            out_base = tmpdir_path / "result"

            sf.write(wav_path, audio_data, sample_rate, subtype="PCM_16")

            cmd = [
                "whisper-cli",
                "--language", settings.stt_language,
                "--model", str(model_path),
                "--file", str(wav_path),
                "--output-json",
                "--output-file", str(out_base),
                "--no-prints",
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            json_path = out_base.with_suffix('.json')
            data = json.loads(json_path.read_text())
            return data.get("transcription", [])


class WhisperCppFileSTT(_WhisperCppMixin):
    """whisper.cpp + Metal 기반 파일 배치 STT."""

    def __init__(self) -> None:
        super().__init__()

    def transcribe_file(self, audio_data: np.ndarray, sample_rate: int = 16000) -> list[Utterance]:
        self._ensure_speaker_model()
        segments = self._run_whisper_cpp(audio_data, sample_rate)

        utterances: list[Utterance] = []
        for seg in segments:
            text = seg.get("text", "").strip().strip('[]')
            if not text:
                continue

            start_ms = seg.get("offsets", {}).get("from", 0)
            end_ms = seg.get("offsets", {}).get("to", start_ms)
            start_sample = int(start_ms * sample_rate / 1000)
            end_sample = int(end_ms * sample_rate / 1000)
            seg_audio = audio_data[start_sample:end_sample]

            if settings.diarization_enabled and len(seg_audio) > 1600:
                speaker = self._speaker_id.identify(seg_audio)
            else:
                speaker = "Speaker 1"

            utterances.append(Utterance(
                time=_format_time(start_ms / 1000),
                speaker=speaker,
                text=text,
                is_final=True,
            ))

        return utterances


class WhisperCppRealtimeSTT(WhisperSTT, _WhisperCppMixin):
    """기존 실시간 버퍼링/VAD를 재사용하고, 발화 완료 시 whisper.cpp CLI 호출."""

    def __init__(self) -> None:
        WhisperSTT.__init__(self)
        _WhisperCppMixin.__init__(self)

    def load_model(self, model_size: str | None = None) -> None:
        # 실시간 경로에서는 whisper.cpp 모델 파일 존재 여부 + 화자 모델만 확인
        Path(settings.whisper_cpp_model_path).expanduser().exists() or (_ for _ in ()).throw(
            FileNotFoundError(f"whisper.cpp 모델이 없습니다: {settings.whisper_cpp_model_path}")
        )
        self._ensure_speaker_model()

    def _process_utterance(self, audio: np.ndarray) -> Utterance | None:
        segments = self._run_whisper_cpp(audio, 16000)
        texts = [seg.get("text", "").strip().strip('[]') for seg in segments if seg.get("text", "").strip()]
        text = " ".join(t for t in texts if t)
        if not text:
            return None

        if settings.diarization_enabled and len(audio) > 1600:
            speaker = self._speaker_id.identify(audio)
        else:
            speaker = "Speaker 1"

        time_str = _format_time(self._chunk_count * settings.audio_chunk_ms / 1000)
        return Utterance(
            time=time_str,
            speaker=speaker,
            text=text,
            is_final=True,
        )
