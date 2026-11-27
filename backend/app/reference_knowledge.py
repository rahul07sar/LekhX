"""SQLite FTS5 indexing and retrieval for LekhX templates and office documentation."""

from __future__ import annotations

import json
from pathlib import Path
import re

from .config import REFERENCE_DATA_DIR, ROOT_DIR
from .db import get_connection

WORD_RE = re.compile(r"\w+", re.UNICODE)


def _fts_query(raw_query: str) -> str:
    tokens = [token for token in WORD_RE.findall(raw_query) if len(token) >= 2]
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in tokens[:10])


def ingest_reference_datasets() -> dict[str, int]:
    """Load bundled JSONL catalogs and Markdown docs into SQLite FTS5."""

    rows: list[tuple[str, str, str, str, str, str]] = []

    templates_file = REFERENCE_DATA_DIR / "lekhx-office-templates.jsonl"
    if templates_file.is_file():
        for idx, line in enumerate(templates_file.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            rows.append(
                (
                    f"tpl:{item.get('id', idx)}",
                    "template-catalog",
                    "multi",
                    ",".join(item.get("formats", [])),
                    str(item.get("name", "")),
                    f"{item.get('description', '')} {' '.join(item.get('tags', []))}",
                )
            )

    docs_dir: Path = ROOT_DIR / "docs"
    if docs_dir.is_dir():
        for doc_path in sorted(docs_dir.glob("*.md")):
            text = doc_path.read_text(encoding="utf-8")
            rows.append(
                (
                    f"doc:{doc_path.stem}",
                    f"docs/{doc_path.name}",
                    "en",
                    "notes",
                    doc_path.stem.replace("-", " ").title(),
                    text,
                )
            )

    with get_connection() as connection:
        connection.execute("DELETE FROM knowledge_chunks")
        connection.executemany(
            """
            INSERT INTO knowledge_chunks (chunk_id, source, language, format, title, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return {"indexed_chunks": len(rows)}


def search_knowledge(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Query the local SQLite FTS5 reference index."""

    fts = _fts_query(query)
    if not fts:
        return []
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT chunk_id, source, language, format, title, snippet(knowledge_chunks, 5, '[', ']', '...', 18) AS snippet
            FROM knowledge_chunks
            WHERE knowledge_chunks MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts, max(1, min(limit, 20))),
        ).fetchall()
    return [dict(row) for row in rows]
