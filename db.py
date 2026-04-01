"""데이터 영구 저장 — SQLite (aiosqlite).

TODO: Section 5에서 실제 구현 예정. 현재는 noop stub.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import aiosqlite

from config import settings

logger = logging.getLogger(__name__)

_db_path = settings.db_path


async def _get_db() -> aiosqlite.Connection:
    return await aiosqlite.connect(_db_path)


async def init_db() -> None:
    """테이블 자동 생성."""
    async with await _get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT,
                audio_path TEXT
            );
            CREATE TABLE IF NOT EXISTS utterances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                time TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                title TEXT,
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                issue_graph_json TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT DEFAULT 'info',
                topic_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
            CREATE TABLE IF NOT EXISTS refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                query TEXT,
                source TEXT,
                title TEXT,
                snippet TEXT,
                url TEXT,
                relevance_score REAL DEFAULT 0.0,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            );
        """)
        await db.commit()


async def create_meeting(title: str | None = None, audio_path: str | None = None) -> int:
    async with await _get_db() as db:
        cursor = await db.execute(
            "INSERT INTO meetings (title, audio_path) VALUES (?, ?)",
            (title, audio_path),
        )
        await db.commit()
        return cursor.lastrowid


async def end_meeting(meeting_id: int) -> None:
    async with await _get_db() as db:
        await db.execute(
            "UPDATE meetings SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), meeting_id),
        )
        await db.commit()


async def save_utterance(meeting_id: int, time: str, speaker: str, text: str) -> None:
    async with await _get_db() as db:
        await db.execute(
            "INSERT INTO utterances (meeting_id, time, speaker, text) VALUES (?, ?, ?, ?)",
            (meeting_id, time, speaker, text),
        )
        await db.commit()


async def save_topic(meeting_id: int, topic_id: int, title: str, start_time: str) -> None:
    async with await _get_db() as db:
        await db.execute(
            "INSERT INTO topics (meeting_id, topic_id, title, start_time) VALUES (?, ?, ?, ?)",
            (meeting_id, topic_id, title, start_time),
        )
        await db.commit()


async def update_topic_end_time(meeting_id: int, topic_id: int, end_time: str) -> None:
    async with await _get_db() as db:
        await db.execute(
            "UPDATE topics SET end_time = ? WHERE meeting_id = ? AND topic_id = ?",
            (end_time, meeting_id, topic_id),
        )
        await db.commit()


async def save_issue(meeting_id: int, topic_id: int, issue_dict: dict) -> None:
    async with await _get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO issues (meeting_id, topic_id, issue_graph_json) VALUES (?, ?, ?)",
            (meeting_id, topic_id, json.dumps(issue_dict, ensure_ascii=False)),
        )
        await db.commit()


async def save_intervention(
    meeting_id: int, trigger_type: str, message: str, level: str, topic_id: int | None,
) -> None:
    async with await _get_db() as db:
        await db.execute(
            "INSERT INTO interventions (meeting_id, trigger_type, message, level, topic_id) VALUES (?, ?, ?, ?, ?)",
            (meeting_id, trigger_type, message, level, topic_id),
        )
        await db.commit()


async def save_reference(
    meeting_id: int, query: str, source: str, title: str,
    snippet: str, url: str | None, relevance_score: float,
) -> None:
    async with await _get_db() as db:
        await db.execute(
            "INSERT INTO refs (meeting_id, query, source, title, snippet, url, relevance_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (meeting_id, query, source, title, snippet, url, relevance_score),
        )
        await db.commit()


async def update_utterance_text(
    meeting_id: int, time: str, speaker: str, text: str,
) -> None:
    """교정된 발화 텍스트를 DB에 업데이트."""
    async with await _get_db() as db:
        await db.execute(
            "UPDATE utterances SET text = ? WHERE meeting_id = ? AND time = ? AND speaker = ?",
            (text, meeting_id, time, speaker),
        )
        await db.commit()
