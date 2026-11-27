"""SQLite initialization, FTS5 knowledge indexing, and history persistence."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from typing import Iterator

from .config import DATA_DIR, DATABASE_PATH, EXPORTS_DIR, USER_TEMPLATES_DIR


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()


def initialize_database() -> None:
    """Create SQLite tables, indexes, and workspace directories if missing."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH, timeout=30) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'en',
                default_format TEXT NOT NULL DEFAULT 'doc',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                document_id TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generated_documents (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES chat_sessions(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                format TEXT NOT NULL,
                language TEXT NOT NULL,
                template_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks USING fts5(
                chunk_id UNINDEXED,
                source UNINDEXED,
                language UNINDEXED,
                format UNINDEXED,
                title,
                content
            );
            """
        )


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield an initialized SQLite connection using Row objects."""

    initialize_database()
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    """Read a persisted setting key from SQLite."""

    with get_connection() as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: str) -> None:
    """Upsert a setting value inside SQLite."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, utc_now()),
        )


def save_generated_document(
    *,
    doc_id: str,
    session_id: str | None,
    title: str,
    fmt: str,
    language: str,
    template_id: str,
    filename: str,
    relative_path: str,
    size_bytes: int,
    sha256: str,
    plan: dict[str, object],
) -> None:
    """Record a generated office document artifact in SQLite."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO generated_documents (
                id, session_id, title, format, language, template_id,
                filename, relative_path, size_bytes, sha256, plan_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                session_id,
                title,
                fmt,
                language,
                template_id,
                filename,
                relative_path,
                size_bytes,
                sha256,
                json.dumps(plan, ensure_ascii=False),
                utc_now(),
            ),
        )


def list_generated_documents(limit: int = 50) -> list[dict[str, object]]:
    """Return recent generated document records newest-first."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, title, format, language, template_id,
                   filename, relative_path, size_bytes, sha256, plan_json, created_at
            FROM generated_documents
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (max(1, min(limit, 200)),),
        ).fetchall()
    items: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["plan"] = json.loads(str(item.pop("plan_json")))
        items.append(item)
    return items


def get_generated_document(doc_id: str) -> dict[str, object] | None:
    """Fetch one generated document row by its identifier."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, session_id, title, format, language, template_id,
                   filename, relative_path, size_bytes, sha256, plan_json, created_at
            FROM generated_documents
            WHERE id = ?
            """,
            (doc_id,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["plan"] = json.loads(str(item.pop("plan_json")))
    return item
