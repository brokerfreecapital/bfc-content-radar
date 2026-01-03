"""Ingest WordPress posts and TikTok transcripts into the local memory index."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

# Ensure repo root is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.memory.ingest import store_content
from app.memory.models import ContentRecord
from app.memory.storage import known_content_keys
from app.memory.raw_text import write_raw_text
from app.sources.drive import load_transcripts_from_root
from app.sources.wordpress import fetch_wp_posts_all


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _summarize(text: str, max_chars: int = 320) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rsplit(" ", 1)[0] + "…"


def build_wordpress_records(base_url: str, max_posts: int) -> List[ContentRecord]:
    posts = fetch_wp_posts_all(base_url=base_url, max_posts=max_posts)
    records: List[ContentRecord] = []

    for post in posts:
        text = (post.get("content_text") or "").strip()
        excerpt = (post.get("excerpt_text") or "").strip()
        summary = excerpt or _summarize(text)
        if not text:
            text = summary
        if not text:
            continue
        records.append(
            ContentRecord(
                source="wordpress",
                external_id=str(post.get("slug") or post.get("id")),
                title=(post.get("title") or "").strip(),
                url=post.get("link"),
                published_at=_parse_iso8601(post.get("date")),
                summary=summary,
                text=text,
                media_type="article",
                extra={
                    "wordpress_id": post.get("id"),
                },
            )
        )
    return records


def build_tiktok_records(root_folder_id: str, transcripts_folder_name: str) -> List[ContentRecord]:
    transcripts = load_transcripts_from_root(root_folder_id, transcripts_folder_name)
    records: List[ContentRecord] = []

    for item in transcripts:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        summary = _summarize(text)
        records.append(
            ContentRecord(
                source="tiktok",
                external_id=item["id"],
                title=item.get("name", "").strip(),
                url=None,
                published_at=_parse_iso8601(item.get("modifiedTime")),
                summary=summary,
                text=text,
                media_type="video",
                extra={
                    "drive_file_name": item.get("name"),
                },
            )
        )
    return records


def ingest_content(max_wordpress_posts: int) -> None:
    load_dotenv()

    base_url = os.environ["BLOG_WP_BASE_URL"]
    root_folder_id = os.environ["ROOT_DRIVE_FOLDER_ID"]
    transcripts_folder_name = os.environ.get(
        "TIKTOK_TRANSCRIPTS_FOLDER_NAME", "BFC_TikTok_Transcripts"
    )

    wordpress_records = build_wordpress_records(base_url, max_wordpress_posts)
    tiktok_records = build_tiktok_records(root_folder_id, transcripts_folder_name)

    records: List[ContentRecord] = [*wordpress_records, *tiktok_records]
    if not records:
        print("No content fetched.")
        return

    known = known_content_keys()
    new_records = [r for r in records if (r.source, r.external_id) not in known]

    if not new_records:
        print("No new content to ingest (all items already indexed).")
        return

    for rec in new_records:
        if rec.source in {"wordpress", "tiktok"} and rec.text:
            write_raw_text(rec.source, rec.external_id, rec.text)

    print(f"Ingesting {len(new_records)} new content record(s)...")
    store_content(new_records)
    print("Ingestion complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local embedding memory store")
    parser.add_argument(
        "--max-wordpress-posts",
        type=int,
        default=200,
        help="Maximum number of WordPress posts to fetch",
    )
    args = parser.parse_args()

    ingest_content(max_wordpress_posts=args.max_wordpress_posts)


if __name__ == "__main__":
    main()
