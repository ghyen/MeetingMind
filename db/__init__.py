"""SQLite 영구 저장 — aiosqlite 기반 비동기 CRUD."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import aiosqlite

from config import settings

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    audio_path TEXT,
    speaker_names TEXT
);

CREATE TABLE IF NOT EXISTS utterances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    time TEXT NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    topic_seq INTEGER NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT
);

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    issue_graph_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    trigger_type TEXT NOT NULL,
    message TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'info',
    topic_id INTEGER,
    time TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    query TEXT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT,
    url TEXT,
    relevance_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
    summary_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    topic_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


async def init_db() -> None:
    """테이블 자동 생성 (앱 시작 시 호출)."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(_SCHEMA)
        # idempotent migrations
        cur = await db.execute("PRAGMA table_info(interventions)")
        cols = {row[1] for row in await cur.fetchall()}
        if "time" not in cols:
            await db.execute("ALTER TABLE interventions ADD COLUMN time TEXT NOT NULL DEFAULT ''")
        cur = await db.execute("PRAGMA table_info(meetings)")
        cols = {row[1] for row in await cur.fetchall()}
        if "speaker_names" not in cols:
            await db.execute("ALTER TABLE meetings ADD COLUMN speaker_names TEXT")
        await db.commit()
    logger.info("DB 초기화 완료: %s", settings.db_path)


# ── 회의 ──────────────────────────────────────────────

async def create_meeting(title: str | None = None, audio_path: str | None = None) -> int:
    """새 회의 생성, meeting_id 반환."""
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO meetings (title, started_at, audio_path) VALUES (?, ?, ?)",
            (title, datetime.now().isoformat(), audio_path),
        )
        await db.commit()
        return cur.lastrowid


async def end_meeting(meeting_id: int) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE meetings SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), meeting_id),
        )
        await db.commit()


async def update_meeting_title(meeting_id: int, title: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE meetings SET title = ? WHERE id = ?",
            (title, meeting_id),
        )
        await db.commit()


async def update_speaker_names(meeting_id: int, speaker_names: dict) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE meetings SET speaker_names = ? WHERE id = ?",
            (json.dumps(speaker_names, ensure_ascii=False), meeting_id),
        )
        await db.commit()


async def get_meeting(meeting_id: int) -> dict | None:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        row = await cur.fetchone()
        if not row:
            return None
        m = dict(row)
        if m.get("speaker_names"):
            try:
                m["speaker_names"] = json.loads(m["speaker_names"])
            except Exception:
                m["speaker_names"] = {}
        else:
            m["speaker_names"] = {}
        return m


async def list_meetings() -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM meetings ORDER BY started_at DESC")
        return [dict(r) for r in await cur.fetchall()]


# ── 발화 ──────────────────────────────────────────────

async def save_utterance(meeting_id: int, time: str, speaker: str, text: str) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO utterances (meeting_id, time, speaker, text) VALUES (?, ?, ?, ?)",
            (meeting_id, time, speaker, text),
        )
        await db.commit()
        return cur.lastrowid


async def get_utterances(meeting_id: int) -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM utterances WHERE meeting_id = ? ORDER BY id", (meeting_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def update_utterance_text(meeting_id: int, time: str, speaker: str, text: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE utterances SET text = ? WHERE meeting_id = ? AND time = ? AND speaker = ?",
            (text, meeting_id, time, speaker),
        )
        await db.commit()


# ── 토픽 ──────────────────────────────────────────────

async def save_topic(meeting_id: int, topic_seq: int, title: str, start_time: str) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO topics (meeting_id, topic_seq, title, start_time) VALUES (?, ?, ?, ?)",
            (meeting_id, topic_seq, title, start_time),
        )
        await db.commit()
        return cur.lastrowid


async def update_topic_end_time(meeting_id: int, topic_seq: int, end_time: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE topics SET end_time = ? WHERE meeting_id = ? AND topic_seq = ?",
            (end_time, meeting_id, topic_seq),
        )
        await db.commit()


async def update_topic_title(meeting_id: int, topic_seq: int, title: str) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "UPDATE topics SET title = ? WHERE meeting_id = ? AND topic_seq = ?",
            (title, meeting_id, topic_seq),
        )
        await db.commit()


async def get_topics(meeting_id: int) -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM topics WHERE meeting_id = ? ORDER BY topic_seq", (meeting_id,)
        )
        rows = []
        for r in await cur.fetchall():
            d = dict(r)
            # UI는 topic.id로 issues를 매칭 → topic_seq를 id로 사용
            d["id"] = d.get("topic_seq", d.get("id"))
            rows.append(d)
        return rows


# ── 쟁점 ──────────────────────────────────────────────

async def save_issue(meeting_id: int, topic_id: int, issue_graph: dict) -> None:
    """IssueGraph를 JSON으로 저장 (upsert)."""
    graph_json = json.dumps(issue_graph, ensure_ascii=False)
    async with aiosqlite.connect(settings.db_path) as db:
        # topic_id 기준으로 기존 레코드가 있으면 업데이트
        cur = await db.execute(
            "SELECT id FROM issues WHERE meeting_id = ? AND topic_id = ?",
            (meeting_id, topic_id),
        )
        existing = await cur.fetchone()
        if existing:
            await db.execute(
                "UPDATE issues SET issue_graph_json = ? WHERE id = ?",
                (graph_json, existing[0]),
            )
        else:
            await db.execute(
                "INSERT INTO issues (meeting_id, topic_id, issue_graph_json) VALUES (?, ?, ?)",
                (meeting_id, topic_id, graph_json),
            )
        await db.commit()


async def get_issues(meeting_id: int) -> dict[int, dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM issues WHERE meeting_id = ? ORDER BY topic_id", (meeting_id,)
        )
        return {
            row["topic_id"]: json.loads(row["issue_graph_json"])
            for row in await cur.fetchall()
        }


# ── 개입 ──────────────────────────────────────────────

async def save_intervention(
    meeting_id: int, trigger_type: str, message: str, level: str,
    topic_id: int | None = None, time: str = "",
) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO interventions (meeting_id, trigger_type, message, level, topic_id, time) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (meeting_id, trigger_type, message, level, topic_id, time),
        )
        await db.commit()
        return cur.lastrowid


async def get_interventions(meeting_id: int) -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM interventions WHERE meeting_id = ? ORDER BY id", (meeting_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


# ── 참고 자료 ─────────────────────────────────────────

async def save_reference(
    meeting_id: int, query: str, source: str, title: str,
    snippet: str, url: str | None, relevance_score: float,
) -> int:
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO refs (meeting_id, query, source, title, snippet, url, relevance_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (meeting_id, query, source, title, snippet, url, relevance_score),
        )
        await db.commit()
        return cur.lastrowid


async def get_references(meeting_id: int) -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM refs WHERE meeting_id = ? ORDER BY relevance_score DESC",
            (meeting_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


# ── 회의록 요약 ──────────────────────────────────────


async def save_summary(meeting_id: int, summary: dict) -> None:
    summary_json = json.dumps(summary, ensure_ascii=False)
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "SELECT id FROM summaries WHERE meeting_id = ?", (meeting_id,),
        )
        existing = await cur.fetchone()
        if existing:
            await db.execute(
                "UPDATE summaries SET summary_json = ? WHERE id = ?",
                (summary_json, existing[0]),
            )
        else:
            await db.execute(
                "INSERT INTO summaries (meeting_id, summary_json) VALUES (?, ?)",
                (meeting_id, summary_json),
            )
        await db.commit()


async def get_summary(meeting_id: int) -> dict | None:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT summary_json FROM summaries WHERE meeting_id = ?", (meeting_id,),
        )
        row = await cur.fetchone()
        return json.loads(row["summary_json"]) if row else None


# ── 메모 ──────────────────────────────────────────────

async def save_note(meeting_id: int, topic_id: int, text: str) -> dict:
    created_at = datetime.now().isoformat()
    async with aiosqlite.connect(settings.db_path) as db:
        cur = await db.execute(
            "INSERT INTO notes (meeting_id, topic_id, text, created_at) VALUES (?, ?, ?, ?)",
            (meeting_id, topic_id, text, created_at),
        )
        await db.commit()
        return {"id": cur.lastrowid, "meeting_id": meeting_id, "topic_id": topic_id, "text": text, "created_at": created_at}


async def get_notes(meeting_id: int, topic_id: int | None = None) -> list[dict]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        if topic_id is None:
            cur = await db.execute(
                "SELECT * FROM notes WHERE meeting_id = ? ORDER BY id", (meeting_id,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM notes WHERE meeting_id = ? AND topic_id = ? ORDER BY id",
                (meeting_id, topic_id),
            )
        return [dict(r) for r in await cur.fetchall()]


# ── 전체 회의 데이터 복원 ─────────────────────────────

async def get_full_meeting(meeting_id: int) -> dict | None:
    """회의 전체 데이터 조회 (meeting + utterances + topics + issues + interventions + refs + notes)."""
    meeting = await get_meeting(meeting_id)
    if not meeting:
        return None
    return {
        "meeting": meeting,
        "utterances": await get_utterances(meeting_id),
        "topics": await get_topics(meeting_id),
        "issues": await get_issues(meeting_id),
        "interventions": await get_interventions(meeting_id),
        "references": await get_references(meeting_id),
        "summary": await get_summary(meeting_id),
        "notes": await get_notes(meeting_id),
    }
