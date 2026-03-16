from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # STT
    stt_engine: str = "sensevoice"  # "sensevoice" | "faster_whisper"
    stt_model_path: str = "models/sensevoice-small"
    stt_language: str = "ko"

    # VAD
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 300

    # 화자 분리
    diarization_enabled: bool = True
    max_speakers: int = 10

    # 토픽 감지
    topic_silence_threshold_sec: float = 3.0
    topic_keywords: list[str] = ["다음 안건", "그건 그렇고", "자 이제", "넘어가서"]

    # 개입 트리거
    loop_detection_count: int = 3
    long_silence_sec: float = 5.0
    time_over_alert_min: float = 10.0

    # LLM
    llm_api_key: str = ""
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    llm_model_deep: str = "claude-sonnet-4-6-20250514"

    # 서버
    host: str = "0.0.0.0"
    port: int = 8000
    audio_chunk_ms: int = 500

    model_config = {"env_file": ".env", "env_prefix": "MM_"}


settings = Settings()
