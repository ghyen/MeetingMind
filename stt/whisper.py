"""faster-whisper (ENERZAi 한국어 모델) 기반 STT.

- CTranslate2 기반 Whisper 4x 속도 향상
- ENERZAi 모델로 한국어 CER ~6.45%
- WhisperLive를 통한 WebSocket 의사스트리밍
"""

from __future__ import annotations

from models import Utterance
from stt import BaseSTT


class FasterWhisperSTT(BaseSTT):

    def __init__(self) -> None:
        self._model = None

    def load_model(self) -> None:
        # TODO: faster-whisper 모델 로드
        pass

    async def transcribe_chunk(self, audio_chunk: bytes) -> Utterance | None:
        # TODO: 추론 구현
        return None
