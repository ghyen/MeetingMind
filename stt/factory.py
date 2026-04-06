"""STT 엔진 선택 팩토리.

현재 정책:
- 실시간(WebSocket): faster-whisper 고정
- 파일 업로드(batch): 설정값에 따라 faster-whisper / whisper.cpp 선택
"""

from __future__ import annotations

from stt.whisper_stt import WhisperSTT
from stt.whisper_cpp_stt import WhisperCppFileSTT


class WhisperFileSTT(WhisperSTT):
    """기존 업로드 경로와의 호환용 alias."""


def get_realtime_stt():
    return WhisperSTT()


def get_file_stt(engine: str):
    if engine == "whisper_cpp":
        return WhisperCppFileSTT()
    return WhisperFileSTT()
