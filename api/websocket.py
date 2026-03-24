"""WebSocket 핸들러 — 실시간 오디오 스트리밍 & 결과 푸시."""

from __future__ import annotations

import dataclasses
import logging
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


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


class ConnectionManager:
    """WebSocket 연결 관리."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict) -> None:
        """모든 연결된 클라이언트에 데이터 전송."""
        for connection in self.active_connections:
            await connection.send_json(data)


manager = ConnectionManager()


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    """오디오 청크를 받아 실시간 처리 결과를 반환.

    클라이언트 → 서버: 오디오 청크 (bytes)
    서버 → 클라이언트: transcript, 토픽, 쟁점, 개입 알림 (JSON)
    """
    pipe = _get_pipeline()

    await manager.connect(websocket)

    # STT 모델 로드 (최초 1회)
    if pipe.stt._recognizer is None:
        try:
            pipe.stt.load_model()
        except Exception as e:
            logger.error("STT 모델 로드 실패: %s", e, exc_info=True)
            await websocket.send_json({"error": f"STT 모델 로드 실패: {e}"})
            await websocket.close()
            manager.disconnect(websocket)
            return

    # 회의 자동 시작
    if not pipe.meeting_id:
        try:
            await pipe.start_meeting(title="실시간 회의")
        except Exception:
            logger.warning("회의 시작 실패", exc_info=True)

    await websocket.send_json({"type": "ready", "message": "STT ready"})

    chunk_count = 0
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            chunk_count += 1
            if chunk_count <= 3 or chunk_count % 50 == 0:
                import numpy as np
                samples = np.frombuffer(audio_chunk, dtype=np.float32)
                rms = float(np.sqrt(np.mean(samples ** 2)))
                logger.info(
                    "Audio chunk #%d: %d bytes, %d samples, rms=%.4f",
                    chunk_count, len(audio_chunk), len(samples), rms,
                )
            try:
                utterance = await pipe.stt.transcribe_chunk(audio_chunk)
                if utterance:
                    logger.info(
                        "STT result: final=%s speaker=%s text='%s'",
                        utterance.is_final, utterance.speaker, utterance.text,
                    )
                    if utterance.is_final:
                        await pipe.on_utterance(utterance)
                    state = pipe.state
                    await websocket.send_json({
                        "type": "transcript",
                        "utterance": _serialize(utterance),
                        "topics": _serialize(state.topics),
                        "interventions": _serialize(state.interventions[-3:]),
                    })
            except Exception as e:
                logger.error("오디오 처리 오류: %s", e, exc_info=True)
                await websocket.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket 오류: %s", e, exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/ws/updates")
async def updates_stream(websocket: WebSocket):
    """분석 결과 업데이트를 실시간 푸시.

    서버 → 클라이언트: 토픽 변경, 쟁점 업데이트, 개입 알림 등
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keepalive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
