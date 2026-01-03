"""Local storage helpers for content memory."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from .models import EmbeddingRecord

DATA_DIR = Path("data")
EMBED_DB_PATH = DATA_DIR / "content_memory.sqlite"
CONTENT_JSONL = DATA_DIR / "content_records.jsonl"

# Handle cases where "data" is a symlink or preexisting mount path.
if not DATA_DIR.exists() and not DATA_DIR.is_symlink():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_jsonl(records: Iterable[dict]) -> None:
    with CONTENT_JSONL.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


@contextmanager
def embedding_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(EMBED_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            embedding BLOB NOT NULL,
            text_excerpt TEXT NOT NULL,
            token_count INTEGER,
            similarity_hint TEXT,
            PRIMARY KEY (source, external_id, chunk_id)
        )
        """
    )
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_embeddings(records: Iterable[EmbeddingRecord]) -> None:
    with embedding_db() as conn:
        conn.executemany(
            """
            INSERT INTO embeddings (source, external_id, chunk_id, embedding, text_excerpt, token_count, similarity_hint)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id, chunk_id) DO UPDATE SET
                embedding=excluded.embedding,
                text_excerpt=excluded.text_excerpt,
                token_count=excluded.token_count,
                similarity_hint=excluded.similarity_hint
            """,
            [
                (
                    rec.source,
                    rec.external_id,
                    rec.chunk_id,
                    memoryview(bytearray(json.dumps(rec.embedding), "utf-8")),
                    rec.text_excerpt,
                    rec.token_count,
                    rec.similarity_hint,
                )
                for rec in records
            ],
        )


def known_content_keys() -> set[tuple[str, str]]:
    """Return all known (source, external_id) pairs from the embeddings DB."""
    with embedding_db() as conn:
        rows = conn.execute("SELECT DISTINCT source, external_id FROM embeddings").fetchall()
    return {(r[0], r[1]) for r in rows}