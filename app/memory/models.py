"""Data models for content memory records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ContentRecord:
    """Normalized representation of an internal content asset."""

    source: str  # "wordpress" | "tiktok"
    external_id: str  # slug or drive file id
    title: str
    url: Optional[str]
    published_at: Optional[datetime]
    summary: str
    text: str
    media_type: str  # "article", "video"
    extra: dict = field(default_factory=dict)


@dataclass
class EmbeddingRecord:
    """Embedding metadata persisted to the local index."""

    source: str
    external_id: str
    chunk_id: str
    text_excerpt: str
    token_count: int
    embedding: list[float] = field(default_factory=list)
    similarity_hint: Optional[str] = None