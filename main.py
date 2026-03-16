"""MeetingMind — 음성 회의 어시스턴트."""

from fastapi import FastAPI

from api.routes import router as api_router
from api.websocket import router as ws_router
from config import settings

app = FastAPI(title="MeetingMind", version="0.1.0")

app.include_router(api_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
