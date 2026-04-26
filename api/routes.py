"""REST API 엔드포인트."""

from __future__ import annotations

import dataclasses
from enum import Enum

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
    if isinstance(obj, Enum):
        return obj.value
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
    provider: str  # "openrouter" | "ollama" | "bonsai"
    model: str


class StartMeetingRequest(BaseModel):
    title: str | None = None
    company: str = ""
    description: str = ""


class MeetingTitleRequest(BaseModel):
    title: str


# ── 회의 라이프사이클 ────────────────────────────────────


@router.post("/meeting/start")
async def start_meeting(req: StartMeetingRequest | None = None):
    """새 회의 시작 → DB에 레코드 생성."""
    pipe = _get_pipeline()
    title = req.title if req else None
    company = req.company if req else ""
    description = req.description if req else ""
    meeting_id = await pipe.start_meeting(
        title=title, company=company, description=description,
    )
    return {"meeting_id": meeting_id, "status": "started"}


@router.post("/meeting/end")
async def end_meeting():
    """현재 회의 종료 → 제목 생성 + 회의록 요약 생성."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"error": "진행 중인 회의가 없습니다"}
    meeting_id = pipe.meeting_id
    summary = await pipe.end_meeting()
    # DB에서 생성된 제목 가져오기
    meeting = await db.get_meeting(meeting_id)
    title = meeting.get("title") if meeting else None
    return {"meeting_id": meeting_id, "title": title, "status": "ended", "summary": summary}


@router.put("/meeting/title")
async def update_current_meeting_title(body: MeetingTitleRequest):
    """현재 진행 중인 회의 제목 수정."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"error": "진행 중인 회의가 없습니다"}
    title = (body.title or "").strip() or "새 회의"
    await pipe.update_meeting_title(title)
    return {"ok": True, "meeting_id": pipe.meeting_id, "title": title}


# ── 실시간 상태 조회 (인메모리) ────────────────────────────


@router.get("/meeting/state")
async def get_meeting_state():
    """현재 회의 상태 조회 (토픽, 쟁점, 개입 등)."""
    pipe = _get_pipeline()
    state = pipe.state
    from config import settings
    issue_tokens = {}
    for topic in state.topics:
        issue_tokens[str(topic.id)] = pipe.issue_structurer.get_pending_tokens(topic.id)
    return {
        "utterances": _serialize(state.utterances),
        "topics": _serialize(state.topics),
        "issues": {str(k): _serialize(v) for k, v in state.issues.items()},
        "interventions": _serialize(state.interventions),
        "references": _serialize(state.references),
        "issue_tokens": issue_tokens,
        "issue_token_threshold": settings.issue_token_threshold,
    }


@router.post("/meeting/upload")
async def upload_audio(file: UploadFile):
    """녹음 파일 업로드 → faster-whisper STT + 화자 식별 → 파이프라인."""
    import asyncio
    import logging
    import time
    from audio_converter import convert_bytes
    from stt.whisper_stt import WhisperSTT
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
        whisper = WhisperSTT()
        try:
            utterances = await asyncio.to_thread(whisper.transcribe_file, data)
        except Exception as e:
            upload_logger.exception("STT 처리 실패")
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
    result = {
        "utterance": _serialize(utterance),
        "topics": _serialize(state.topics),
        "issues": {str(k): _serialize(v) for k, v in state.issues.items()},
        "interventions": _serialize(state.latest_interventions),
        "references": _serialize(state.references[-5:]),
    }
    if state.latest_corrections:
        result["corrections"] = _serialize(state.latest_corrections)
    return result


@router.get("/meeting/topics")
async def get_topics():
    """안건 목록 조회."""
    return {"topics": _serialize(_get_pipeline().state.topics)}


class TopicTitleRequest(BaseModel):
    title: str


@router.put("/meeting/topics/{topic_id}")
async def rename_topic(topic_id: int, body: TopicTitleRequest):
    """안건 제목 수정 — 인메모리(state.topics + topic_detector.segments) + DB 동기화."""
    pipe = _get_pipeline()
    title = body.title.strip() or "안건"
    found = False
    for t in pipe.state.topics:
        if t.id == topic_id:
            t.title = title
            found = True
    for t in pipe.topic_detector.segments:
        if t.id == topic_id:
            t.title = title
            found = True
    if not found:
        return {"error": "해당 안건을 찾을 수 없습니다"}
    if pipe.meeting_id:
        await db.update_topic_title(pipe.meeting_id, topic_id, title)
    return {"ok": True, "topic_id": topic_id, "title": title}


class TopicCreateRequest(BaseModel):
    title: str = "새 안건"


@router.post("/meeting/topics")
async def create_topic(body: TopicCreateRequest):
    """수동 안건 추가 — 이전 안건 종료 후 새 안건 시작."""
    from models import Topic
    pipe = _get_pipeline()
    detector = pipe.topic_detector
    title = (body.title or "").strip() or "새 안건"
    start = pipe.state.utterances[-1].time if pipe.state.utterances else "00:00:00"
    detector._topic_counter += 1
    new_topic = Topic(id=detector._topic_counter, title=title, start_time=start)
    if detector.segments:
        detector.segments[-1].end_time = start
    detector.segments.append(new_topic)
    if pipe.state.topics:
        pipe.state.topics[-1].end_time = start
    pipe.state.topics.append(new_topic)
    if pipe.meeting_id:
        if len(pipe.state.topics) >= 2:
            prev = pipe.state.topics[-2]
            if prev.end_time:
                await db.update_topic_end_time(pipe.meeting_id, prev.id, prev.end_time)
        await db.save_topic(pipe.meeting_id, new_topic.id, title, start)
    return {"topic": _serialize(new_topic)}


@router.get("/meeting/issues/{topic_id}")
async def get_issue(topic_id: int):
    """특정 안건의 쟁점 구조 조회."""
    issue = _get_pipeline().state.issues.get(topic_id)
    return {"topic_id": topic_id, "issue": _serialize(issue) if issue else None}


class PositionUpdate(BaseModel):
    speaker: str
    stance: str
    arguments: list[str] = []
    evidence: list[str] = []


class IssueUpdateRequest(BaseModel):
    topic: str
    positions: list[PositionUpdate] = []
    consensus: str | None = None
    decision: str | None = None
    open_questions: list[str] = []


@router.put("/meeting/issues/{topic_id}")
async def update_issue(topic_id: int, body: IssueUpdateRequest):
    """쟁점 구조 수동 편집."""
    from models import IssueGraph, Position
    pipe = _get_pipeline()
    issue = IssueGraph(
        topic=body.topic,
        positions=[Position(speaker=p.speaker, stance=p.stance, arguments=p.arguments, evidence=p.evidence) for p in body.positions],
        consensus=body.consensus,
        decision=body.decision,
        open_questions=body.open_questions,
    )
    pipe.state.issues[topic_id] = issue
    pipe.issue_structurer._cache[topic_id] = issue
    if pipe.meeting_id:
        await db.save_issue(pipe.meeting_id, topic_id, dataclasses.asdict(issue))
    return {"ok": True}


class AskRequest(BaseModel):
    question: str


@router.post("/meeting/ask")
async def ask_ai(req: AskRequest):
    """AI 채팅 — 전체 스크립트 + 쟁점 구조 + 요약본을 컨텍스트로 답변.

    컨텍스트 구성:
      1) 저장된 회의 요약 (있으면)
      2) 안건별 쟁점 구조 (positions, consensus, decision, open_questions)
      3) 전체 발화 스크립트 (토큰 예산을 위해 최대 12,000자까지, 초과 시 앞부분 생략)
    """
    from analysis.llm import ask_json

    pipe = _get_pipeline()
    state = pipe.state

    # 화자 이름 + 저장된 요약을 DB에서 조회
    speaker_names: dict = {}
    saved_summary = None
    if pipe.meeting_id:
        meeting = await db.get_meeting(pipe.meeting_id)
        if meeting:
            speaker_names = meeting.get("speaker_names") or {}
        saved_summary = await db.get_summary(pipe.meeting_id)

    def _label(speaker: str) -> str:
        return speaker_names.get(speaker, speaker)

    # 1) 전체 스크립트 — 긴 회의는 앞부분 생략하여 최근 쪽을 보존
    lines = [f"[{u.time}] {_label(u.speaker)}: {u.text}" for u in state.utterances]
    transcript = "\n".join(lines)
    MAX_CHARS = 12000
    if len(transcript) > MAX_CHARS:
        transcript = "… (앞부분 생략) …\n" + transcript[-MAX_CHARS:]
    transcript = transcript or "(아직 발화가 없습니다)"

    # 2) 안건별 쟁점 구조
    issue_blocks = []
    for topic in state.topics:
        issue = state.issues.get(topic.id)
        header = f"[안건 {topic.id}] {topic.title}"
        if not issue:
            issue_blocks.append(f"{header}\n  (쟁점 없음)")
            continue
        parts = [header]
        for p in issue.positions:
            args = "; ".join(p.arguments) if p.arguments else "-"
            parts.append(f"  · {_label(p.speaker)} 입장: {p.stance} | 근거: {args}")
        if issue.consensus:
            parts.append(f"  · 합의: {issue.consensus}")
        if issue.decision:
            parts.append(f"  · 결정: {issue.decision}")
        if issue.open_questions:
            parts.append(f"  · 미결: {', '.join(issue.open_questions)}")
        issue_blocks.append("\n".join(parts))
    issues_text = "\n\n".join(issue_blocks) if issue_blocks else "(안건 없음)"

    # 3) 저장된 요약 (회의 종료 후)
    summary_text = ""
    if saved_summary:
        one_line = saved_summary.get("one_line", "")
        decisions = saved_summary.get("decisions", [])
        summary_text = f"한 줄 요약: {one_line}\n"
        if decisions:
            summary_text += "결정 사항:\n" + "\n".join(f"- {d}" for d in decisions)

    context_sections = []
    if summary_text:
        context_sections.append(f"## 회의 요약\n{summary_text}")
    context_sections.append(f"## 안건별 쟁점\n{issues_text}")
    context_sections.append(f"## 전체 스크립트\n{transcript}")
    context = "\n\n".join(context_sections)

    prompt = (
        "당신은 회의 어시스턴트입니다. 아래 회의 자료를 근거로 사용자 질문에 답하세요.\n\n"
        f"{context}\n\n"
        f"## 사용자 질문\n{req.question}\n\n"
        "규칙:\n"
        "- 회의 자료에 근거한 내용만 답변. 추측하지 말 것.\n"
        "- 자료에 없는 내용은 '회의에선 언급되지 않았어요'라고 답할 것.\n"
        "- 한국어로 2~4문장 이내 간결히.\n\n"
        '{"answer": "답변 내용"}'
    )

    try:
        result = await ask_json(prompt)
        return {"answer": result.get("answer", "") or "답변을 찾지 못했어요."}
    except Exception as e:
        return {"error": f"AI 호출 실패: {e}"}


class NoteCreate(BaseModel):
    topic_id: int
    text: str


@router.post("/meeting/notes")
async def create_note(body: NoteCreate):
    """현재 진행 중인 회의의 쟁점별 메모 저장."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"error": "진행 중인 회의가 없습니다"}
    text = (body.text or "").strip()
    if not text:
        return {"error": "메모 내용이 비어 있습니다"}
    note = await db.save_note(pipe.meeting_id, body.topic_id, text)
    return {"note": note}


@router.get("/meeting/notes")
async def list_notes(topic_id: int | None = None):
    """현재 진행 중인 회의의 메모 조회. topic_id가 있으면 해당 안건만."""
    pipe = _get_pipeline()
    if not pipe.meeting_id:
        return {"notes": []}
    notes = await db.get_notes(pipe.meeting_id, topic_id)
    return {"notes": notes}


@router.get("/meetings/{meeting_id}/notes")
async def list_meeting_notes(meeting_id: int, topic_id: int | None = None):
    """특정 회의의 메모 조회 (요약 화면/히스토리용)."""
    notes = await db.get_notes(meeting_id, topic_id)
    return {"notes": notes}


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
    pipe._stt_corrector = None
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


@router.put("/meetings/{meeting_id}/title")
async def update_meeting_title(meeting_id: int, body: MeetingTitleRequest):
    """저장된 회의 제목 수정."""
    title = (body.title or "").strip() or "새 회의"
    meeting = await db.get_meeting(meeting_id)
    if not meeting:
        return {"error": "회의를 찾을 수 없습니다"}
    pipe = _get_pipeline()
    if pipe.meeting_id == meeting_id:
        await pipe.update_meeting_title(title)
    else:
        await db.update_meeting_title(meeting_id, title)
    return {"ok": True, "meeting_id": meeting_id, "title": title}


class SpeakerNamesUpdate(BaseModel):
    speaker_names: dict


@router.put("/meetings/{meeting_id}/speaker-names")
async def update_speaker_names(meeting_id: int, body: SpeakerNamesUpdate):
    await db.update_speaker_names(meeting_id, body.speaker_names)
    return {"ok": True}


@router.put("/meeting/speaker-names")
async def update_current_speaker_names(body: SpeakerNamesUpdate):
    """현재 진행 중인 회의의 화자 이름 업데이트."""
    pipe = _get_pipeline()
    if pipe.meeting_id:
        await db.update_speaker_names(pipe.meeting_id, body.speaker_names)
    return {"ok": True}


# ── 모델 선택 ─────────────────────────────────────────


@router.get("/models")
async def list_models():
    """사용 가능한 LLM 모델 목록."""
    from analysis.llm import get_active_model, list_ollama_models, list_bonsai_models
    from config import settings

    ollama_models = await list_ollama_models()
    bonsai_models = await list_bonsai_models()
    return {
        "active": get_active_model(),
        "providers": {
            "openrouter": [settings.llm_model_fast],
            "ollama": ollama_models,
            "bonsai": bonsai_models,
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
