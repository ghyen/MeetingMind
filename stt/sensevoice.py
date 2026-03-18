"""SenseVoice-Small STT + sherpa-onnx 스트리밍/화자분리.

SenseVoice-Small (funasr):
  - 비자기회귀 아키텍처 → 10초 오디오를 70ms에 처리
  - 한국어 1급 지원 (zh, en, yue, ja, ko)

sherpa-onnx:
  - 네이티브 실시간 스트리밍
  - 화자 분리 내장 — 별도 라이브러리 불필요
  - ONNX Runtime 기반 완전 오프라인 동작
"""

from __future__ import annotations

from models import Utterance


class SenseVoiceEngine:
    """SenseVoice + sherpa-onnx 통합 엔진."""

    def __init__(self) -> None:
        self._recognizer = None  # sherpa-onnx 스트리밍 recognizer
        self._diarizer = None  # sherpa-onnx 화자 분리

    def load_model(self) -> None:
        """모델 로드.

        # sherpa-onnx 스트리밍 recognizer
        import sherpa_onnx
        self._recognizer = sherpa_onnx.OnlineRecognizer.from_pretrained(...)

        # SenseVoice (funasr)
        from funasr import AutoModel
        self._model = AutoModel(model="iic/SenseVoiceSmall")

        # sherpa-onnx 화자 분리
        self._diarizer = sherpa_onnx.SpeakerDiarization(...)
        """
        pass

    async def transcribe_chunk(self, audio_chunk: bytes) -> Utterance | None:
        """오디오 청크 → Utterance (화자 포함)."""
        # TODO: sherpa-onnx 스트리밍으로 오디오 전달 → partial/final transcript
        # TODO: 화자 분리 결과 병합
        return None
