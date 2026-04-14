"""MeetingMind — 음성 회의 어시스턴트."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import dataclasses

from api.routes import router as api_router
from api.websocket import router as ws_router, manager
from config import settings
from pipeline import Pipeline

logger = logging.getLogger(__name__)


# ── WebSocket 로그 핸들러 — 서버 로그를 브라우저 로그 패널에 실시간 전달 ──

_LOG_PREFIXES = ("pipeline", "analysis", "stt", "search", "db", "api", "__main__")


class _WSLogHandler(logging.Handler):
    """MeetingMind 모듈 로그를 WebSocket 클라이언트에 broadcast."""

    def __init__(self):
        super().__init__(logging.INFO)
        self._loop: asyncio.AbstractEventLoop | None = None
        self.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s | %(message)s", datefmt="%H:%M:%S",
        ))

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        if not any(record.name.startswith(p) for p in _LOG_PREFIXES):
            return
        if not self._loop or not manager.active_connections:
            return
        try:
            msg = {"type": "log", "level": record.levelname.lower(), "message": self.format(record)}
            self._loop.call_soon_threadsafe(asyncio.ensure_future, manager.broadcast(msg))
        except Exception:
            pass


_ws_log_handler = _WSLogHandler()
logging.getLogger().addHandler(_ws_log_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ws_log_handler.set_loop(asyncio.get_running_loop())
    # 시작: DB 초기화
    logger.info("[STT] Whisper 모델 크기: %s", settings.stt_model_size)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    import db
    await db.init_db()
    yield


app = FastAPI(title="MeetingMind", version="0.1.0", lifespan=lifespan)

# 공유 Pipeline 인스턴스
pipeline = Pipeline()


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


async def _broadcast_event(event_type: str, data=None):
    """Pipeline 이벤트 → WebSocket /ws/updates 클라이언트에 broadcast."""
    if not manager.active_connections:
        return
    await manager.broadcast({
        "type": event_type,
        "data": _serialize(data),
    })


pipeline.add_listener(_broadcast_event)

@app.get("/")
async def root():
    return RedirectResponse("/static/index.html")

app.include_router(api_router)
app.include_router(ws_router)

# 정적 파일 서빙 (테스트 페이지)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
