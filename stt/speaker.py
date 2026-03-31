"""sherpa-onnx 3dspeaker 기반 실시간 화자 식별.

sherpa-onnx SpeakerEmbeddingExtractor + SpeakerEmbeddingManager로
발화 단위 오디오에서 화자 임베딩을 추출하고 코사인 유사도로 화자를 식별한다.
ONNX Runtime 기반 완전 오프라인 동작.
"""

from __future__ import annotations

import logging

import numpy as np

from config import settings

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
        """float32 오디오 샘플 → 화자 라벨 ("Speaker 1", "Speaker 2", ...).

        동작 원리:
        1. 오디오에서 화자 임베딩(고차원 벡터)을 추출
        2. 기등록된 화자 임베딩들과 코사인 유사도 비교
        3. 유사도가 threshold(0.5) 이상이면 기존 화자로 판정
        4. 매칭 없으면 새 화자로 등록하고 임베딩 저장
        """
        if self._extractor is None or len(samples) < 1600:  # 0.1초(1600샘플) 미만은 임베딩 추출 불가
            return self._fallback_label()

        # 임베딩 추출: 오디오 → 고차원 벡터 (화자의 "목소리 지문")
        stream = self._extractor.create_stream()
        stream.accept_waveform(16000, samples.tolist())
        stream.input_finished()

        if not self._extractor.is_ready(stream):
            return self._fallback_label()

        embedding = self._extractor.compute(stream)

        # 등록된 화자 임베딩들과 코사인 유사도 비교 → 가장 유사한 화자 반환
        name = self._manager.search(embedding, settings.speaker_similarity_threshold)

        if not name:
            # 새 화자 등록 — 다음부터 이 임베딩과 비교하여 같은 화자 인식
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
