"""REST API 엔드포인트."""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

import db

router = APIRouter(prefix="/api")


def _get_pipeline():
    from main import pipeline
    return pipeline


def _serialize(obj):
    """dataclass/enum → dict 재귀 직렬화."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


class SimulateRequest(BaseModel):
    speaker: str = "A"
    text: str
    time: str | None = None


class ModelSelectRequest(BaseModel):
    provider: str  # "openrouter" | "ollama"
    model: str


class StartMeetingRequest(BaseModel):
    title: str | None = None


# ── 회의 라이프사이클 ────────────────────────────────────


@router.post("/meeting/start")
async def start_meeting(req: StartMeetingRequest | None = None):
    """새 회의 시작 → DB에 레코드 생성."""
    pipe = _get_pipeline()
    title = req.title if req else None
    meeting_id = await pipe.start_meeting(title=title)
    return {"meeting_id": meeting_id, "status": "started"}


@router.post("/meeting/end")
async def end_meeting():
    """현재 회의 종료 → 회의록 요약 생성."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"error": "진행 중인 회의가 없습니다"}
    meeting_id = pipe.meeting_id
    summary = await pipe.end_meeting()
    return {"meeting_id": meeting_id, "status": "ended", "summary": summary}


# ── 실시간 상태 조회 (인메모리) ────────────────────────────


@router.get("/meeting/state")
async def get_meeting_state():
    """현재 회의 상태 조회 (토픽, 쟁점, 개입 등)."""
    state = _get_pipeline().state
    return {
        "utterances": _serialize(state.utterances),
        "topics": _serialize(state.topics),
        "issues": {str(k): _serialize(v) for k, v in state.issues.items()},
        "interventions": _serialize(state.interventions),
        "references": _serialize(state.references),
    }


@router.post("/meeting/upload")
async def upload_audio(file: UploadFile):
    """녹음 파일 업로드 → faster-whisper STT + 화자 식별 → 파이프라인."""
    import asyncio
    import logging
    import time
    from audio_converter import convert_bytes
    from stt.whisper_stt import WhisperFileSTT
    from pipeline import _StepTimer

    upload_logger = logging.getLogger(__name__)
    timer = _StepTimer()
    pipe = _get_pipeline()
    raw = await file.read()

    # 오디오 디코딩 → 16kHz mono float32
    async with timer.step("오디오변환"):
        try:
            data = convert_bytes(raw, filename=file.filename or "audio.wav")
        except Exception as e:
            return {"error": f"오디오 변환 실패: {e}"}

    audio_sec = len(data) / 16000
    upload_logger.info("오디오 길이: %.1f초", audio_sec)

    # 회의 자동 시작
    if not pipe.meeting_id:
        await pipe.start_meeting(title=file.filename, audio_path=file.filename)

    # faster-whisper로 배치 STT + 화자 식별
    async with timer.step("Whisper STT"):
        whisper = WhisperFileSTT()
        try:
            utterances = await asyncio.to_thread(whisper.transcribe_file, data)
        except Exception as e:
            return {"error": f"STT 처리 실패: {e}"}

    upload_logger.info("STT 결과: %d개 발화", len(utterances))

    # 파이프라인에 발화 전달
    async with timer.step("분석 파이프라인"):
        results = []
        for utt in utterances:
            await pipe.on_utterance(utt)
            results.append(_serialize(utt))

    timer.log_summary(f"업로드 전체 ({file.filename})")
    return {"filename": file.filename, "utterances": results, "status": "done"}


@router.post("/meeting/simulate")
async def simulate_utterance(req: SimulateRequest):
    """텍스트 발화 시뮬레이션 — STT 없이 파이프라인 테스트."""
    from models import Utterance

    pipe = _get_pipeline()

    # 회의 자동 시작 (아직 시작되지 않았으면)
    if not pipe.meeting_id:
        await pipe.start_meeting(title="시뮬레이션 회의")

    # 시간 자동 계산
    if req.time:
        time_str = req.time
    else:
        n = len(pipe.state.utterances)
        total_sec = n * 5  # 발화당 5초 간격 가정
        h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
        time_str = f"{h:02d}:{m:02d}:{s:02d}"

    utterance = Utterance(
        time=time_str,
        speaker=req.speaker,
        text=req.text,
        is_final=True,
    )
    await pipe.on_utterance(utterance)

    state = pipe.state
    return {
        "utterance": _serialize(utterance),
        "topics": _serialize(state.topics),
        "issues": {str(k): _serialize(v) for k, v in state.issues.items()},
        "interventions": _serialize(state.latest_interventions),
        "references": _serialize(state.references[-5:]),
    }


@router.get("/meeting/topics")
async def get_topics():
    """안건 목록 조회."""
    return {"topics": _serialize(_get_pipeline().state.topics)}


@router.get("/meeting/issues/{topic_id}")
async def get_issue(topic_id: int):
    """특정 안건의 쟁점 구조 조회."""
    issue = _get_pipeline().state.issues.get(topic_id)
    return {"topic_id": topic_id, "issue": _serialize(issue) if issue else None}


@router.get("/meeting/summary")
async def get_summary():
    """현재 회의 요약 조회."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"error": "진행 중인 회의가 없습니다"}
    summary = await db.get_summary(pipe.meeting_id)
    return {"summary": summary}


@router.get("/meeting/interventions")
async def get_interventions():
    """개입 알림 목록 조회."""
    return {"interventions": _serialize(_get_pipeline().state.interventions)}


@router.post("/meeting/reset")
async def reset_meeting():
    """회의 상태 초기화."""
    from pipeline import MeetingState
    pipe = _get_pipeline()
    # 진행 중이던 회의 종료
    if pipe.meeting_id:
        await pipe.end_meeting()
    pipe.state = MeetingState()
    pipe.meeting_id = None
    pipe.topic_detector._topic_counter = 0
    pipe.topic_detector.segments = []
    pipe.topic_detector._recent = []
    pipe.issue_structurer._cache = {}
    pipe.issue_structurer._pending = {}
    return {"status": "reset"}


# ── 회의 히스토리 조회 (DB) ─────────────────────────────


@router.get("/meetings")
async def list_meetings():
    """저장된 회의 목록 조회."""
    meetings = await db.list_meetings()
    return {"meetings": meetings}


@router.get("/meetings/{meeting_id}")
async def get_meeting_detail(meeting_id: int):
    """특정 회의 전체 데이터 조회."""
    data = await db.get_full_meeting(meeting_id)
    if not data:
        return {"error": "회의를 찾을 수 없습니다"}
    return data


# ── 모델 선택 ─────────────────────────────────────────


@router.get("/models")
async def list_models():
    """사용 가능한 LLM 모델 목록."""
    from analysis.llm import get_active_model, list_ollama_models
    from config import settings

    ollama_models = await list_ollama_models()
    return {
        "active": get_active_model(),
        "providers": {
            "openrouter": [settings.llm_model_fast],
            "ollama": ollama_models,
        },
    }


@router.get("/model")
async def get_model():
    """현재 활성 모델 조회."""
    from analysis.llm import get_active_model
    return get_active_model()


@router.post("/model")
async def set_model(req: ModelSelectRequest):
    """활성 모델 변경."""
    from analysis.llm import set_active_model
    return set_active_model(req.provider, req.model)
