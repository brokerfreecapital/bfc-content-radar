"""Simple embedding search over the local content memory store."""

from __future__ import annotations

import json
import math
from typing import Iterable, List, Optional, Sequence, Tuple

from openai import OpenAI

from .models import EmbeddingRecord
from .storage import embedding_db


def _load_embeddings(sources: Optional[Sequence[str]] = None) -> List[EmbeddingRecord]:
    allowed = set(sources) if sources else None
    records: List[EmbeddingRecord] = []

    with embedding_db() as conn:
        query = "SELECT source, external_id, chunk_id, embedding, text_excerpt, token_count, similarity_hint FROM embeddings"
        params: Tuple = ()
        if allowed:
            placeholders = ",".join("?" for _ in allowed)
            query += f" WHERE source IN ({placeholders})"
            params = tuple(allowed)

        cursor = conn.execute(query, params)
        for row in cursor.fetchall():
            embedding_bytes = row[3]
            embedding = json.loads(bytes(embedding_bytes).decode("utf-8")) if embedding_bytes else []
            records.append(
                EmbeddingRecord(
                    source=row[0],
                    external_id=row[1],
                    chunk_id=row[2],
                    text_excerpt=row[4],
                    token_count=row[5],
                    embedding=embedding,
                    similarity_hint=row[6],
                )
            )
    return records


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_memory(query: str, sources: Optional[Sequence[str]] = None, top_k: int = 10) -> List[dict]:
    """Return top_k similar chunks for the query across selected sources."""
    client = OpenAI()
    query_embedding = (
        client.embeddings.create(model="text-embedding-3-large", input=query).data[0].embedding
    )

    records = _load_embeddings(sources)
    scored: List[Tuple[float, EmbeddingRecord]] = []

    for rec in records:
        score = _cosine_similarity(query_embedding, rec.embedding)
        scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[dict] = []
    for score, rec in scored[:top_k]:
        results.append(
            {
                "source": rec.source,
                "external_id": rec.external_id,
                "chunk_id": rec.chunk_id,
                "score": score,
                "text_excerpt": rec.text_excerpt,
                "similarity_hint": rec.similarity_hint,
                "token_count": rec.token_count,
            }
        )
    return results


def search_memory_grouped(query: str, sources: Optional[Sequence[str]] = None, per_source: int = 5) -> dict:
    """Return top matches grouped by source for balanced surfacing in emails."""
    all_results = search_memory(query, sources=sources, top_k=500)
    grouped: dict[str, List[dict]] = {}
    for item in all_results:
        grouped.setdefault(item["source"], []).append(item)

    trimmed: dict[str, List[dict]] = {}
    for source, items in grouped.items():
        trimmed[source] = items[:per_source]
    return trimmed


def find_connections(query: str, existing_sources: Sequence[str], new_sources: Sequence[str], per_source: int = 5) -> dict:
    """Compare matches between new/external vs existing/internal sources."""
    grouped = search_memory_grouped(query, sources=None, per_source=per_source * 3)
    out: dict[str, List[dict]] = {"new": [], "existing": []}
    for src, items in grouped.items():
        bucket = "new" if src in new_sources else "existing" if src in existing_sources else None
        if bucket:
            out[bucket].extend(items[:per_source])
    return out
