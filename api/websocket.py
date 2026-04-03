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
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    """오디오 청크 → faster-whisper 실시간 STT + 화자 식별.

    클라이언트 → 서버: 오디오 청크 (float32 PCM bytes, 0.5초 단위)
    서버 → 클라이언트: {"type":"transcript", ...} + {"type":"analysis", ...}
    """
    import asyncio
    from stt.whisper_stt import WhisperSTT

    pipe = _get_pipeline()
    await manager.connect(websocket)
    ws_open = True

    async def safe_send(data):
        if ws_open and websocket in manager.active_connections:
            try:
                await websocket.send_json(data)
            except Exception:
                pass

    whisper = WhisperSTT()
    try:
        await asyncio.to_thread(whisper.load_model)
    except Exception as e:
        logger.error("STT 모델 로드 실패: %s", e, exc_info=True)
        await safe_send({"error": f"STT 모델 로드 실패: {e}"})
        manager.disconnect(websocket)
        return

    if not pipe.meeting_id:
        try:
            await pipe.start_meeting(title="실시간 회의")
        except Exception:
            logger.warning("회의 시작 실패", exc_info=True)

    await safe_send({"type": "ready", "message": "STT ready"})

    async def _bg_analysis(utt):
        """백그라운드 태스크: 발화를 파이프라인에 전달 → 분석 결과를 같은 WebSocket에 push.
        asyncio.create_task()로 실행되어 다음 오디오 청크 수신을 블로킹하지 않음.
        """
        try:
            await pipe.on_utterance(utt)
            state = pipe.state
            msg = {
                "type": "analysis",
                "topics": _serialize(state.topics),
                "issues": {str(k): _serialize(v) for k, v in state.issues.items()},
                "interventions": _serialize(state.latest_interventions),
                "references": _serialize(state.references[-5:]),
            }
            if state.latest_corrections:
                msg["corrections"] = _serialize(state.latest_corrections)
            await safe_send(msg)
            # 분석 완료 알림 → 클라이언트가 "Analyzing..." 해제
            await safe_send({"type": "status", "state": "done"})
        except Exception as e:
            logger.warning("파이프라인 분석 실패: %s", e)
            await safe_send({"type": "status", "state": "done"})

    try:
        while True:
            msg = await websocket.receive()
            # 텍스트 명령 처리
            if msg.get("text"):
                cmd = msg["text"].strip()
                if cmd.startswith("calibrate:"):
                    # 클라이언트에서 측정한 threshold 적용
                    try:
                        val = float(cmd.split(":")[1])
                        whisper._vad_threshold = val
                        whisper._noise_floor = val / whisper._vad_multiplier
                        logger.info("캘리브레이션 적용: threshold=%.4f", val)
                    except ValueError:
                        pass
                elif cmd == "calibrate":
                    whisper.start_calibration()
                    await safe_send({"type": "calibrating"})
                continue
            audio_chunk = msg.get("bytes")
            if not audio_chunk:
                continue
            try:
                was_calibrating = whisper._calibrating
                utterance = await asyncio.to_thread(whisper.feed_chunk, audio_chunk)
                if was_calibrating and not whisper._calibrating:
                    await safe_send({"type": "calibrated", "threshold": whisper._vad_threshold})

                # 청크 처리 후 상태 push — 클라이언트가 진행 상황을 알 수 있도록
                buf_samples = sum(len(b) for b in whisper._buffer)
                if not utterance and buf_samples > 0:
                    # 음성 감지됨, 버퍼에 오디오 축적 중
                    await safe_send({
                        "type": "status",
                        "state": "buffering",
                        "buffer_sec": round(buf_samples / 16000, 1),
                        "chunks": whisper._chunk_count,
                    })

                if utterance:
                    logger.info("STT: [%s] %s: %s", utterance.time, utterance.speaker, utterance.text)
                    await safe_send({
                        "type": "transcript",
                        "utterance": _serialize(utterance),
                    })
                    # 분석 시작 알림 → 클라이언트에서 "Analyzing..." 표시
                    await safe_send({"type": "status", "state": "analyzing", "chunks": whisper._chunk_count})
                    asyncio.create_task(_bg_analysis(utterance))
            except Exception as e:
                logger.error("오디오 처리 오류: %s", e)
    except WebSocketDisconnect:
        ws_open = False
        utt = whisper.flush()
        if utt:
            try:
                await pipe.on_utterance(utt)
            except Exception:
                pass
        manager.disconnect(websocket)
    except Exception as e:
        ws_open = False
        logger.error("WebSocket 오류: %s", e)
        manager.disconnect(websocket)


@router.websocket("/ws/speaker")
async def speaker_stream(websocket: WebSocket):
    """오디오 청크 → 화자 식별만 수행 (STT는 브라우저 Web Speech API 사용).

    클라이언트 → 서버: 오디오 청크 (float32 PCM bytes)
    서버 → 클라이언트: {"speaker": "Speaker 1"} or {"speaker": "Speaker 2"} ...
    """
    import numpy as np
    from stt.speaker import SpeakerIdentifier
    from config import settings

    await websocket.accept()

    speaker_id = SpeakerIdentifier()
    if settings.diarization_enabled:
        try:
            speaker_id.load()
        except Exception as e:
            logger.error("화자 식별 모델 로드 실패: %s", e, exc_info=True)
            await websocket.send_json({"error": f"화자 모델 로드 실패: {e}"})
            await websocket.close()
            return

    await websocket.send_json({"type": "ready"})

    # 오디오 샘플 축적 (발화 단위로 화자 식별)
    utterance_samples: list[np.ndarray] = []
    sample_count = 0

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            samples = np.frombuffer(audio_chunk, dtype=np.float32)
            utterance_samples.append(samples)
            sample_count += len(samples)

            # "identify" 텍스트 메시지를 받으면 축적된 오디오로 화자 식별
            # 또는 일정량 축적 시 자동 식별은 하지 않음 — 클라이언트가 요청할 때만
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Speaker WS 오류: %s", e, exc_info=True)


@router.websocket("/ws/speaker-id")
async def speaker_id_stream(websocket: WebSocket):
    """화자 식별 — 오디오 청크 축적 + 텍스트 명령으로 제어.

    클라이언트 → 서버:
      - bytes: 오디오 청크 (축적)
      - text "identify": 축적된 오디오로 화자 식별 후 초기화
      - text "reset": 축적 버퍼 초기화
    서버 → 클라이언트:
      - {"type":"ready"}
      - {"type":"speaker", "speaker":"Speaker 1"}
    """
    import numpy as np
    from stt.speaker import SpeakerIdentifier
    from config import settings

    await websocket.accept()

    speaker_id = SpeakerIdentifier()
    if settings.diarization_enabled:
        try:
            speaker_id.load()
        except Exception as e:
            logger.error("화자 식별 모델 로드 실패: %s", e, exc_info=True)
            await websocket.send_json({"error": f"화자 모델 로드 실패: {e}"})
            await websocket.close()
            return

    await websocket.send_json({"type": "ready"})

    utterance_samples: list[np.ndarray] = []

    try:
        while True:
            msg = await websocket.receive()
            if msg.get("bytes"):
                # 오디오 청크 축적
                samples = np.frombuffer(msg["bytes"], dtype=np.float32)
                utterance_samples.append(samples)
            elif msg.get("text"):
                cmd = msg["text"].strip()
                if cmd == "identify" and utterance_samples:
                    all_samples = np.concatenate(utterance_samples)
                    speaker = speaker_id.identify(all_samples)
                    utterance_samples = []
                    await websocket.send_json({"type": "speaker", "speaker": speaker})
                elif cmd == "reset":
                    utterance_samples = []
                    await websocket.send_json({"type": "reset", "speaker": "Speaker 1"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("SpeakerID WS 오류: %s", e, exc_info=True)


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
