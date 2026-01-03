"""Content ingestion and embedding helpers."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable, List, Sequence
from openai import OpenAI

from .models import ContentRecord, EmbeddingRecord
from .storage import append_jsonl, upsert_embeddings

EMBED_MODEL = "text-embedding-3-large"
MAX_WORDS = 450
CHUNK_OVERLAP = 80


def record_to_json(record: ContentRecord) -> dict:
    payload = {
        "source": record.source,
        "external_id": record.external_id,
        "title": record.title,
        "url": record.url,
        "published_at": record.published_at.isoformat() if record.published_at else None,
        "summary": record.summary,
        "text": record.text,
        "media_type": record.media_type,
        "extra": record.extra,
    }
    return payload


def chunk_text(text: str) -> List[str]:
    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    overlap = max(CHUNK_OVERLAP, int(MAX_WORDS * 0.15))
    start = 0

    while start < len(words):
        end = min(len(words), start + MAX_WORDS)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = max(0, end - overlap)

    return chunks


def build_embedding_records(records: Sequence[ContentRecord]) -> List[EmbeddingRecord]:
    embedding_records: List[EmbeddingRecord] = []

    for record in records:
        chunks = chunk_text(record.text) or [record.summary]
        for idx, chunk in enumerate(chunks):
            chunk_id = hashlib.sha1(f"{record.external_id}:{idx}".encode("utf-8")).hexdigest()[:12]
            embedding_records.append(
                EmbeddingRecord(
                    source=record.source,
                    external_id=record.external_id,
                    chunk_id=chunk_id,
                    embedding=[],
                    text_excerpt=chunk,
                    token_count=len(chunk.split()),
                    similarity_hint=record.summary,
                )
            )
    return embedding_records


def fetch_embeddings(records: List[EmbeddingRecord]) -> None:
    client = OpenAI()
    # Group chunks by source to avoid huge single calls
    batches = defaultdict(list)
    for rec in records:
        batches[(rec.source, rec.external_id)].append(rec)

    for key, recs in batches.items():
        texts = [rec.text_excerpt for rec in recs]
        response = client.embeddings.create(model=EMBED_MODEL, input=texts)
        for rec, embedding in zip(recs, response.data):
            rec.embedding = embedding.embedding


def store_content(records: Iterable[ContentRecord]) -> None:
    records = list(records)
    if not records:
        return
    append_jsonl(record_to_json(rec) for rec in records)
    embedding_records = build_embedding_records(records)
    fetch_embeddings(embedding_records)
    upsert_embeddings(embedding_records)