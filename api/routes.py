"""REST API 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile

router = APIRouter(prefix="/api")


@router.get("/meeting/state")
async def get_meeting_state():
    """현재 회의 상태 조회 (토픽, 쟁점, 개입 등)."""
    # TODO: pipeline.state 반환
    return {"status": "ok"}


@router.post("/meeting/upload")
async def upload_audio(file: UploadFile):
    """녹음 파일 업로드 → 분석 시작 (MVP용)."""
    # TODO: 파일 저장 → pipeline 실행
    return {"filename": file.filename, "status": "processing"}


@router.get("/meeting/topics")
async def get_topics():
    """안건 목록 조회."""
    # TODO: pipeline.state.topics 반환
    return {"topics": []}


@router.get("/meeting/issues/{topic_id}")
async def get_issue(topic_id: int):
    """특정 안건의 쟁점 구조 조회."""
    # TODO: pipeline.state.issues[topic_id] 반환
    return {"topic_id": topic_id, "issue": None}


@router.get("/meeting/interventions")
async def get_interventions():
    """개입 알림 목록 조회."""
    # TODO: pipeline.state.interventions 반환
    return {"interventions": []}
