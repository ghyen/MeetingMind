"""faster-whisper 통합 STT — 실시간 스트리밍 + 파일 배치 모두 지원.

실시간: 오디오 청크 축적 → VAD로 침묵 감지 → 발화 단위로 faster-whisper 배치 처리
파일: 전체 오디오를 한번에 faster-whisper로 처리

화자 식별: 3dspeaker (sherpa-onnx) — 발화 단위 오디오에서 화자 임베딩 추출
"""

from __future__ import annotations

import logging

import numpy as np

from config import settings
from models import Utterance
from stt.speaker import SpeakerIdentifier

logger = logging.getLogger(__name__)

# ── 공통: 시간 포맷 ──

def _format_time(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class WhisperSTT:
    """faster-whisper 통합 엔진 (실시간 + 파일)."""

    def __init__(self) -> None:
        self._model = None
        self._speaker_id = SpeakerIdentifier()
        # 실시간 스트리밍 상태
        self._buffer: list[np.ndarray] = []  # 현재 발화 오디오 축적
        self._silence_ms: int = 0
        self._chunk_count: int = 0
        self._silence_threshold_ms: int = 1200  # 이 시간 침묵이면 발화 종료
        # 적응형 노이즈 플로어
        self._calibrating: bool = False
        self._calibration_rms: list[float] = []
        self._calibration_chunks: int = 4  # 0.5초 * 4 = 2초
        self._noise_floor: float = 0.0
        self._vad_threshold: float = 0.02  # 기본값 (캘리브레이션 전)
        self._vad_multiplier: float = 3.0

    def load_model(self, model_size: str = "large-v3") -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
        logger.info("faster-whisper '%s' 로드 완료", model_size)

        if settings.diarization_enabled:
            try:
                self._speaker_id.load()
            except Exception:
                logger.warning("화자 식별 모델 로드 실패", exc_info=True)

    # ── 파일 배치 처리 ──

    def transcribe_file(self, audio_data: np.ndarray, sample_rate: int = 16000) -> list[Utterance]:
        """float32 16kHz mono 오디오 → Utterance 리스트 (화자 포함)."""
        if self._model is None:
            self.load_model()

        segments, info = self._model.transcribe(
            audio_data,
            language="ko",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        utterances = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue

            start_sample = int(seg.start * sample_rate)
            end_sample = int(seg.end * sample_rate)
            seg_audio = audio_data[start_sample:end_sample]

            if settings.diarization_enabled and len(seg_audio) > 1600:
                speaker = self._speaker_id.identify(seg_audio)
            else:
                speaker = "Speaker 1"

            utterances.append(Utterance(
                time=_format_time(seg.start),
                speaker=speaker,
                text=text,
                is_final=True,
            ))

        return utterances

    # ── 실시간 스트리밍 처리 ──

    def feed_chunk(self, audio_chunk: bytes) -> Utterance | None:
        """오디오 청크(float32 PCM) 입력 → 발화 완성 시 Utterance 반환, 아니면 None.

        동작 원리:
        1. 각 청크(0.5초)의 RMS(에너지)를 계산하여 음성/침묵을 판별
        2. 음성이면 버퍼에 축적, 침묵이면 침묵 카운터 증가
        3. 침묵이 1.2초 이상 지속되면 "발화 종료"로 판단
        4. 축적된 오디오를 faster-whisper에 넘겨 텍스트 추출 + 화자 식별
        """
        if self._model is None:
            self.load_model()

        samples = np.frombuffer(audio_chunk, dtype=np.float32)
        self._chunk_count += 1

        # RMS(Root Mean Square) 계산 — 오디오 에너지 레벨의 척도
        rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

        # 캘리브레이션 모드: 배경 소음 레벨을 측정하여 적응형 VAD 임계값 설정
        # 2초간(4청크) 소음의 평균 RMS를 구하고 × 3배를 음성 판별 기준으로 사용
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
            logger.debug(
                "chunk#%d rms=%.4f thresh=%.4f speech=%s silence=%dms buf=%.1fs",
                self._chunk_count, rms, self._vad_threshold, is_speech, self._silence_ms, buf_sec,
            )

        if is_speech:
            self._buffer.append(samples)
            self._silence_ms = 0
            return None

        # 침묵 구간 — 버퍼가 있으면 침묵도 포함 (발화 끝부분 보존용: 마지막 음절 잘림 방지)
        if self._buffer:
            self._buffer.append(samples)
        self._silence_ms += settings.audio_chunk_ms

        if self._buffer and self._silence_ms >= self._silence_threshold_ms:
            # 발화 종료 판정 — 축적된 전체 오디오를 whisper로 한번에 처리
            all_audio = np.concatenate(self._buffer)
            self._buffer = []
            self._silence_ms = 0

            # 너무 짧은 발화 무시 (0.3초=4800 샘플 미만은 의미 없는 소음일 가능성 높음)
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
        """축적된 오디오 → whisper STT + 화자 식별.

        feed_chunk에서 발화 종료로 판정된 오디오 구간을 받아서:
        1. faster-whisper로 한국어 텍스트 추출 (vad_filter=False: 이미 VAD를 거쳤으므로)
        2. SpeakerIdentifier로 화자 임베딩 비교 → 화자 라벨 부여
        """
        segments, _ = self._model.transcribe(
            audio,
            language="ko",
            beam_size=5,
            vad_filter=False,  # feed_chunk의 RMS VAD로 이미 음성 구간만 잘라냈으므로 비활성화
        )
        texts = [seg.text.strip() for seg in segments if seg.text.strip()]
        text = " ".join(texts)
        if not text:
            return None

        # 화자 식별
        if settings.diarization_enabled and len(audio) > 1600:
            speaker = self._speaker_id.identify(audio)
        else:
            speaker = "Speaker 1"

        # 타임스탬프 (청크 기반 추정)
        time_str = _format_time(self._chunk_count * settings.audio_chunk_ms / 1000)

        return Utterance(
            time=time_str,
            speaker=speaker,
            text=text,
            is_final=True,
        )

    def reset_speakers(self) -> None:
        self._speaker_id.reset()

    def start_calibration(self) -> None:
        """노이즈 캘리브레이션 시작 (2초간 배경 소음 측정)."""
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
