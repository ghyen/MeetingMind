"""mlx-whisper 통합 STT — Apple Silicon GPU/ANE 활용.

실시간: 오디오 청크 축적 → VAD로 침묵 감지 → 발화 단위로 mlx-whisper 처리
파일: 전체 오디오를 한번에 mlx-whisper로 처리

화자 식별: 3dspeaker (sherpa-onnx) — 발화 단위 오디오에서 화자 임베딩 추출
"""

from __future__ import annotations

import logging
import time

import numpy as np

from config import settings
from models import Utterance
from stt.speaker import SpeakerIdentifier

logger = logging.getLogger(__name__)

_MLX_REPOS: dict[str, str] = {
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "tiny": "mlx-community/whisper-tiny-mlx",
}


def _format_time(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class WhisperSTT:
    """mlx-whisper 통합 엔진 (실시간 + 파일)."""

    def __init__(self) -> None:
        self._mlx_repo: str | None = None
        self._speaker_id = SpeakerIdentifier()
        # 실시간 스트리밍 상태
        self._buffer: list[np.ndarray] = []
        self._silence_ms: int = 0
        self._chunk_count: int = 0
        self._silence_threshold_ms: int = 800  # 800ms 침묵이면 발화 종료 (기존 1200ms)
        # 적응형 노이즈 플로어
        self._calibrating: bool = False
        self._calibration_rms: list[float] = []
        self._calibration_chunks: int = 4
        self._noise_floor: float = 0.0
        self._vad_threshold: float = 0.02
        self._vad_multiplier: float = 3.0

    def load_model(self, model_size: str | None = None) -> None:
        import mlx_whisper

        model_size = model_size or settings.stt_model_size
        self._mlx_repo = _MLX_REPOS.get(model_size, f"mlx-community/whisper-{model_size}-mlx")

        # 더미 오디오로 모델 워밍업 (첫 실제 요청 지연 방지)
        dummy = np.zeros(3200, dtype=np.float32)
        mlx_whisper.transcribe(dummy, path_or_hf_repo=self._mlx_repo, language="ko", verbose=False)
        logger.info("mlx-whisper %s → %s 로드 완료", model_size, self._mlx_repo)

        if settings.diarization_enabled:
            try:
                self._speaker_id.load()
            except Exception:
                logger.warning("화자 식별 모델 로드 실패", exc_info=True)

    # ── 파일 배치 처리 ──

    def transcribe_file(self, audio_data: np.ndarray, sample_rate: int = 16000) -> list[Utterance]:
        """float32 16kHz mono 오디오 → Utterance 리스트."""
        if self._mlx_repo is None:
            self.load_model()

        import mlx_whisper
        result = mlx_whisper.transcribe(
            audio_data,
            path_or_hf_repo=self._mlx_repo,
            language="ko",
            verbose=False,
        )

        utterances = []
        for seg in result.get("segments", []):
            text = seg["text"].strip()
            if not text:
                continue

            start_sample = int(seg["start"] * sample_rate)
            end_sample = int(seg["end"] * sample_rate)
            seg_audio = audio_data[start_sample:end_sample]

            if settings.diarization_enabled and len(seg_audio) > 1600:
                speaker = self._speaker_id.identify(seg_audio)
            else:
                speaker = "Speaker 1"

            utterances.append(Utterance(
                time=_format_time(seg["start"]),
                speaker=speaker,
                text=text,
                is_final=True,
            ))

        return utterances

    # ── 실시간 스트리밍 처리 ──

    def feed_chunk(self, audio_chunk: bytes) -> Utterance | None:
        """오디오 청크(float32 PCM) 입력 → 발화 완성 시 Utterance 반환."""
        if self._mlx_repo is None:
            self.load_model()

        samples = np.frombuffer(audio_chunk, dtype=np.float32)
        self._chunk_count += 1

        rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

        if self._calibrating:
            self._calibration_rms.append(rms)
            if len(self._calibration_rms) >= self._calibration_chunks:
                self._noise_floor = sum(self._calibration_rms) / len(self._calibration_rms)
                self._vad_threshold = max(self._noise_floor * self._vad_multiplier, 0.005)
                self._calibrating = False
                logger.info(
                    "노이즈 캘리브레이션 완료: floor=%.4f, threshold=%.4f",
                    self._noise_floor, self._vad_threshold,
                )
            return None

        is_speech = rms > self._vad_threshold

        if self._chunk_count <= 10 or self._chunk_count % 50 == 0:
            buf_sec = sum(len(b) for b in self._buffer) / 16000 if self._buffer else 0
            logger.info(
                "chunk#%d rms=%.4f thresh=%.4f speech=%s silence=%dms buf=%.1fs",
                self._chunk_count, rms, self._vad_threshold, is_speech, self._silence_ms, buf_sec,
            )

        if is_speech:
            self._buffer.append(samples)
            self._silence_ms = 0
            return None

        if self._buffer:
            self._buffer.append(samples)
        self._silence_ms += settings.audio_chunk_ms

        if self._buffer and self._silence_ms >= self._silence_threshold_ms:
            all_audio = np.concatenate(self._buffer)
            self._buffer = []
            self._silence_ms = 0

            if len(all_audio) < 16000 * 0.3:
                return None

            return self._process_utterance(all_audio)

        return None

    def flush(self) -> Utterance | None:
        """남은 버퍼 강제 처리 (녹음 종료 시 호출)."""
        if not self._buffer:
            return None
        all_audio = np.concatenate(self._buffer)
        self._buffer = []
        self._silence_ms = 0
        if len(all_audio) < 16000 * 0.3:
            return None
        return self._process_utterance(all_audio)

    def _process_utterance(self, audio: np.ndarray) -> Utterance | None:
        """축적된 오디오 → mlx-whisper STT + 화자 식별."""
        import mlx_whisper

        audio_sec = len(audio) / 16000
        logger.info("Whisper 처리 시작: 오디오 %.1f초", audio_sec)

        t0 = time.time()
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._mlx_repo,
            language="ko",
            verbose=False,
        )
        texts = [seg["text"].strip() for seg in result.get("segments", []) if seg["text"].strip()]
        text = " ".join(texts)
        stt_elapsed = time.time() - t0

        if not text:
            logger.info("Whisper 결과 없음 (%.2f초 소요)", stt_elapsed)
            return None

        t1 = time.time()
        if settings.diarization_enabled and len(audio) > 1600:
            speaker = self._speaker_id.identify(audio)
        else:
            speaker = "Speaker 1"
        spk_elapsed = time.time() - t1

        time_str = _format_time(self._chunk_count * settings.audio_chunk_ms / 1000)

        logger.info(
            "Whisper 완료: [%s] %s: %s (STT %.2f초 + 화자 %.2f초 = 총 %.2f초)",
            time_str, speaker, text, stt_elapsed, spk_elapsed, stt_elapsed + spk_elapsed,
        )

        return Utterance(
            time=time_str,
            speaker=speaker,
            text=text,
            is_final=True,
        )

    def reset_speakers(self) -> None:
        self._speaker_id.reset()

    def start_calibration(self) -> None:
        """노이즈 캘리브레이션 시작."""
        self._calibrating = True
        self._calibration_rms = []
        logger.info("노이즈 캘리브레이션 시작 (%.1f초)", self._calibration_chunks * 0.5)

    def reset_stream(self) -> None:
        """스트리밍 상태 초기화."""
        self._buffer = []
        self._silence_ms = 0
        self._chunk_count = 0
        self._calibrating = False
        self._calibration_rms = []
