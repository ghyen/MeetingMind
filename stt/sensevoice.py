"""SenseVoice-Small 기반 STT.

- 비자기회귀 아키텍처 → 10초 오디오를 70ms에 처리
- 한국어 1급 지원 (zh, en, yue, ja, ko)
- MIT 라이선스
"""

from __future__ import annotations

from models import Utterance
from stt import BaseSTT


class SenseVoiceSTT(BaseSTT):

    def __init__(self) -> None:
        self._model = None

    def load_model(self) -> None:
        # TODO: SenseVoice 모델 로드
        pass

    async def transcribe_chunk(self, audio_chunk: bytes) -> Utterance | None:
        # TODO: 추론 구현
        return None
