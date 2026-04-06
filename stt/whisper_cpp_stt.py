"""whisper.cpp 기반 파일 배치 STT adapter.

현재는 파일 업로드(batch) 경로 전용으로 사용한다.
실시간 스트리밍(feed_chunk)은 지원하지 않는다.
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


def _format_time(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class WhisperCppFileSTT:
    """whisper.cpp + Metal 기반 파일 배치 STT."""

    def __init__(self) -> None:
        self._speaker_id = SpeakerIdentifier()
        self._speaker_loaded = False

    def _ensure_speaker_model(self) -> None:
        if settings.diarization_enabled and not self._speaker_loaded:
            self._speaker_id.load()
            self._speaker_loaded = True

    def transcribe_file(self, audio_data: np.ndarray, sample_rate: int = 16000) -> list[Utterance]:
        self._ensure_speaker_model()

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
            segments = data.get("transcription", [])

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
