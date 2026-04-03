from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # STT
    stt_language: str = "ko"

    # VAD
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 300
    vad_model_path: str = "models/silero_vad.onnx"

    # 화자 분리
    diarization_enabled: bool = True
    max_speakers: int = 10
    speaker_embedding_model: str = "models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
    speaker_similarity_threshold: float = 0.5

    # 토픽 감지
    topic_silence_threshold_sec: float = 3.0
    topic_keywords: list[str] = ["다음 안건", "그건 그렇고", "자 이제", "넘어가서"]

    # 쟁점 구조화
    issue_batch_size: int = 10  # N개 발화마다 LLM으로 쟁점 업데이트

    # 개입 트리거
    loop_detection_count: int = 3
    long_silence_sec: float = 5.0
    time_over_alert_min: float = 10.0

    # LLM
    llm_api_key: str = ""
    llm_provider: str = "ollama"  # "ollama" | "openrouter" | "bonsai"
    llm_model_fast: str = "gemma4:e4b"
    llm_model_deep: str = "gemma4:e4b"
    ollama_base_url: str = "http://localhost:11434/v1"
    bonsai_base_url: str = "http://localhost:8080/v1"
    bonsai_model: str = "bonsai-8b"

    # DB
    db_path: str = "data/meetingmind.db"

    # 자료 수집
    chromadb_path: str = "data/chromadb"
    tavily_api_key: str = ""

    # 서버
    host: str = "0.0.0.0"
    port: int = 8000
    audio_chunk_ms: int = 500

    model_config = {"env_file": ".env", "env_prefix": "MM_", "extra": "ignore"}


settings = Settings()
