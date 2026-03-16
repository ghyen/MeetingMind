"""WebSocket 핸들러 — 실시간 오디오 스트리밍 & 결과 푸시."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
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
    await manager.connect(websocket)
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            # TODO: pipeline.on_audio_chunk(audio_chunk) 호출
            # TODO: 결과를 websocket.send_json()으로 반환
    except WebSocketDisconnect:
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
