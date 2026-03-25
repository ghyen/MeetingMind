"""SenseVoice-Small STT + sherpa-onnx 스트리밍/화자분리.

SenseVoice-Small (funasr):
  - 비자기회귀 아키텍처 → 10초 오디오를 70ms에 처리
  - 한국어 1급 지원 (zh, en, yue, ja, ko)

sherpa-onnx:
  - 네이티브 실시간 스트리밍
  - SpeakerEmbeddingExtractor + SpeakerEmbeddingManager로 실시간 화자 식별
  - ONNX Runtime 기반 완전 오프라인 동작
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from config import settings
from models import Utterance

logger = logging.getLogger(__name__)


class SpeakerIdentifier:
    """sherpa-onnx SpeakerEmbeddingExtractor 기반 실시간 화자 식별."""

    def __init__(self) -> None:
        self._extractor = None
        self._manager = None
        self._speaker_count = 0

    def load(self) -> None:
        import sherpa_onnx

        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=settings.speaker_embedding_model,
            num_threads=2,
        )
        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self._manager = sherpa_onnx.SpeakerEmbeddingManager(self._extractor.dim)
        logger.info(
            "Speaker embedding 로드 완료 (dim=%d, threshold=%.2f)",
            self._extractor.dim,
            settings.speaker_similarity_threshold,
        )

    def identify(self, samples: np.ndarray) -> str:
        """float32 오디오 샘플 → 화자 라벨 ("Speaker 1", "Speaker 2", ...)."""
        if self._extractor is None or len(samples) < 1600:  # 0.1초 미만은 스킵
            return self._fallback_label()

        # 임베딩 추출
        stream = self._extractor.create_stream()
        stream.accept_waveform(16000, samples.tolist())
        stream.input_finished()

        if not self._extractor.is_ready(stream):
            return self._fallback_label()

        embedding = self._extractor.compute(stream)

        # 등록된 화자 중 매칭
        name = self._manager.search(embedding, settings.speaker_similarity_threshold)

        if not name:
            # 새 화자 등록
            self._speaker_count += 1
            name = f"Speaker {self._speaker_count}"
            self._manager.add(name, embedding)
            logger.info("새 화자 등록: %s", name)

        return name

    def _fallback_label(self) -> str:
        """오디오가 너무 짧을 때 마지막 화자 또는 기본값."""
        if self._speaker_count > 0:
            return f"Speaker {self._speaker_count}"
        return "Speaker 1"

    def reset(self) -> None:
        """화자 목록 초기화 (새 회의 시작 시)."""
        if self._manager is not None:
            # 모든 화자 제거
            for name in list(self._manager.all_speakers):
                self._manager.remove(name)
        self._speaker_count = 0


class SenseVoiceEngine:
    """SenseVoice + sherpa-onnx 통합 엔진."""

    def __init__(self) -> None:
        self._recognizer = None  # sherpa-onnx 스트리밍 recognizer
        self._stream = None  # 현재 온라인 스트림
        self._chunk_count = 0  # 타임스탬프 계산용
        self._last_text = ""  # 중복 결과 필터링
        self._speaker_id = SpeakerIdentifier()
        self._utterance_samples: list[np.ndarray] = []  # 현재 발화의 오디오 축적

    def load_model(self) -> None:
        """sherpa-onnx 스트리밍 recognizer + 화자 식별 초기화."""
        import sherpa_onnx

        model_dir = Path(settings.sherpa_model_dir)

        self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(model_dir / "tokens.txt"),
            encoder=str(model_dir / "encoder-epoch-99-avg-1.int8.onnx"),
            decoder=str(model_dir / "decoder-epoch-99-avg-1.int8.onnx"),
            joiner=str(model_dir / "joiner-epoch-99-avg-1.int8.onnx"),
            num_threads=2,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=1.5,
            rule2_min_trailing_silence=0.8,
            rule3_min_utterance_length=10,
        )
        self._stream = self._recognizer.create_stream()

        # 화자 식별 로드
        if settings.diarization_enabled:
            try:
                self._speaker_id.load()
            except Exception:
                logger.warning("화자 식별 모델 로드 실패 — 화자 구분 없이 진행", exc_info=True)

    async def transcribe_chunk(self, audio_chunk: bytes) -> Utterance | None:
        """오디오 청크 → Utterance (화자 포함).

        partial result는 is_final=False, endpoint 감지 시 is_final=True.
        """
        if self._recognizer is None:
            return None

        samples = np.frombuffer(audio_chunk, dtype=np.float32)

        # 현재 발화의 오디오 축적 (화자 식별용)
        self._utterance_samples.append(samples)

        self._stream.accept_waveform(16000, samples.tolist())

        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        text = self._recognizer.get_result(self._stream).strip()
        self._chunk_count += 1

        if not text:
            return None

        is_final = self._recognizer.is_endpoint(self._stream)

        # partial이 이전과 동일하면 스킵
        if text == self._last_text and not is_final:
            return None

        # 화자 식별
        if is_final and settings.diarization_enabled:
            # 축적된 오디오로 화자 식별
            all_samples = np.concatenate(self._utterance_samples)
            speaker = self._speaker_id.identify(all_samples)
        else:
            speaker = self._speaker_id._fallback_label()

        utterance = Utterance(
            time=self._format_time(self._chunk_count),
            speaker=speaker,
            text=text,
            is_final=is_final,
        )

        if is_final:
            self._recognizer.reset(self._stream)
            self._last_text = ""
            self._utterance_samples = []  # 다음 발화를 위해 초기화
        else:
            self._last_text = text

        return utterance

    def reset_speakers(self) -> None:
        """화자 목록 초기화 (새 회의 시작 시)."""
        self._speaker_id.reset()

    def _format_time(self, chunk_index: int) -> str:
        """청크 인덱스 → HH:MM:SS 포맷 타임스탬프."""
        total_sec = int(chunk_index * settings.audio_chunk_ms / 1000)
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
