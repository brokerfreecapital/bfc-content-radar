"""Generate a daily content email using the local memory store.

Usage:
    python scripts/draft_daily_email.py --query "sba lending" --send

Without --send the email body is printed to stdout for review.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Dict, List, Tuple

from dotenv import load_dotenv

# Ensure repo root imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.email.gmail_sender import send_email
from app.memory.query import search_memory_grouped

CONTENT_JSONL = Path("data/content_records.jsonl")


def _load_content_index() -> Dict[Tuple[str, str], dict]:
    index: Dict[Tuple[str, str], dict] = {}
    if not CONTENT_JSONL.exists():
        return index
    with CONTENT_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (record.get("source"), record.get("external_id"))
            index[key] = record
    return index


def _format_entry(item: dict, record: dict | None) -> str:
    title = record.get("title") if record else None
    url = record.get("url") if record else None
    summary = record.get("summary") if record else None
    lines = []
    if title:
        lines.append(f"- {title}")
    else:
        lines.append(f"- {item['text_excerpt'][:100]}…")
    if url:
        lines.append(f"  {url}")
    if summary:
        lines.append(f"  {summary[:220]}…")
    excerpt = item.get("text_excerpt", "")
    if excerpt and (not summary or summary not in excerpt):
        lines.append(f"  Snippet: {excerpt[:240]}…")
    return "\n".join(lines)


def build_email_body(query: str, per_source: int) -> str:
    index = _load_content_index()
    results = search_memory_grouped(query=query, per_source=per_source)

    parts: List[str] = [f"Content Radar — query: '{query}'"]
    for source, items in results.items():
        if not items:
            continue
        parts.append("")
        parts.append(f"{source.title()} highlights ({len(items)})")
        for item in items:
            record = index.get((item.get("source"), item.get("external_id")))
            parts.append(_format_entry(item, record))
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft or send the daily content email")
    parser.add_argument("--query", required=True, help="Search query to drive the digest")
    parser.add_argument("--per-source", type=int, default=3, help="Items per source")
    parser.add_argument("--send", action="store_true", help="Send via Gmail instead of printing")
    args = parser.parse_args()

    load_dotenv()
    body = build_email_body(query=args.query, per_source=args.per_source)

    if args.send:
        to_addr = os.environ.get("EMAIL_TO")
        if not to_addr:
            raise RuntimeError("EMAIL_TO must be set in environment to send email")
        subject = f"Content Radar — {args.query}"
        send_email(to_addr, subject, body)
        print(f"Sent to {to_addr}")
    else:
        print(body)


if __name__ == "__main__":
    main()
