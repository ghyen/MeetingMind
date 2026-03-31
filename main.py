"""MeetingMind — 음성 회의 어시스턴트."""

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: DB 초기화
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    import db
    await db.init_db()
    yield


app = FastAPI(title="MeetingMind", version="0.1.0", lifespan=lifespan)

# 공유 Pipeline 인스턴스
pipeline = Pipeline()


def _serialize(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
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
