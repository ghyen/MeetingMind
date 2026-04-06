"""STT 엔진 선택 팩토리."""

from __future__ import annotations

from stt.whisper_stt import WhisperSTT
from stt.whisper_cpp_stt import WhisperCppFileSTT, WhisperCppRealtimeSTT


class WhisperFileSTT(WhisperSTT):
    """기존 업로드 경로와의 호환용 alias."""


def get_realtime_stt(engine: str):
    if engine == "whisper_cpp":
        return WhisperCppRealtimeSTT()
    return WhisperSTT()


def get_file_stt(engine: str):
    if engine == "whisper_cpp":
        return WhisperCppFileSTT()
    return WhisperFileSTT()
