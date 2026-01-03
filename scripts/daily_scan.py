"""Daily scanner to fetch web content and refresh the memory index.

This pulls the configured RSS feed and WordPress API, normalizes posts,
updates embeddings, and optionally drafts the daily email.

Usage:
    python scripts/daily_scan.py --query "small business lending" --max-posts 120 --send

Without --send it will just ingest and print the email body.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure repo root imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.memory.ingest import store_content
from app.memory.models import ContentRecord
from app.memory.storage import known_content_keys
from app.memory.raw_text import write_raw_text
from app.sources.wordpress import fetch_wp_posts_all
from app.sources.rss import fetch_rss_posts
from app.sources.external_feeds import EXTERNAL_FEEDS
from app.sources.nyt import fetch_times_wire, fetch_article_search
from app.email.gmail_sender import send_email
from scripts.ingest_content import _summarize, _parse_iso8601  # reuse helpers
from scripts.draft_daily_email import build_email_body
from app.llm.idea_digest import build_content_ideas


def build_rss_records(feed_url: str, limit: int, source_label: str = "rss") -> list[ContentRecord]:
    entries = fetch_rss_posts(feed_url, limit=limit)
    records: list[ContentRecord] = []
    for e in entries:
        summary = (e.get("summary_text") or "").strip()
        text = summary or (e.get("title") or "")
        if not text:
            continue
        records.append(
            ContentRecord(
                source=source_label,
                external_id=e.get("link") or e.get("title") or "unknown",
                title=e.get("title") or "",
                url=e.get("link"),
                published_at=None,
                summary=_summarize(text),
                text=text,
                media_type="article",
                extra={"published": e.get("published")},
            )
        )
    return records


def build_nyt_records(api_key: str, query: str, wire_limit: int = 15, search_limit: int = 20) -> list[ContentRecord]:
    records: list[ContentRecord] = []
    seen: set[str] = set()

    def _add(item: dict, source_type: str) -> None:
        text = (item.get("text") or item.get("summary") or item.get("title") or "").strip()
        if not text:
            return
        key = item.get("url") or f"nyt::{source_type}::{item.get('title','')[:40]}"
        if key in seen:
            return
        seen.add(key)
        records.append(
            ContentRecord(
                source="nyt",
                external_id=key,
                title=item.get("title") or "",
                url=item.get("url"),
                published_at=_parse_iso8601(item.get("published")),
                summary=_summarize(text),
                text=text,
                media_type="article",
                extra={
                    "section": item.get("section"),
                    "subsection": item.get("subsection"),
                    "paywalled": item.get("paywalled", True),
                    "nyt_source": source_type,
                },
            )
        )

    times_wire_items = fetch_times_wire(api_key, section="business", limit=wire_limit)
    for item in times_wire_items:
        _add(item, "times_wire")

    article_search_items = fetch_article_search(api_key, query=query, section_filter="Business", limit=search_limit)
    for item in article_search_items:
        _add(item, "article_search")
    return records


def build_wordpress_records(base_url: str, max_posts: int) -> list[ContentRecord]:
    posts = fetch_wp_posts_all(base_url=base_url, max_posts=max_posts)
    records: list[ContentRecord] = []
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
                extra={"wordpress_id": post.get("id")},
            )
        )
    return records


def daily_scan(query: str, max_posts: int, send: bool) -> None:
    load_dotenv()

    rss_url = os.environ.get("BLOG_RSS_URL")
    base_url = os.environ.get("BLOG_WP_BASE_URL")
    nyt_api_key = os.environ.get("NYT_API_KEY")

    records: list[ContentRecord] = []

    if rss_url:
        records.extend(build_rss_records(rss_url, limit=50, source_label="rss"))
    # External public feeds
    for label, feed_url in EXTERNAL_FEEDS:
        records.extend(build_rss_records(feed_url, limit=50, source_label=label))
    if base_url:
        records.extend(build_wordpress_records(base_url, max_posts=max_posts))
    if nyt_api_key:
        records.extend(build_nyt_records(nyt_api_key, query=query))

    if not records:
        print("No content fetched.")
        ideas = build_content_ideas([], query)
        body = build_email_body(query=query, per_source=3)
        body = body + "\n\n---\nContent ideas (GPT)\n" + ideas
        if send:
            to_addr = os.environ.get("EMAIL_TO")
            if not to_addr:
                raise RuntimeError("EMAIL_TO must be set to send email")
            subject = f"Content Radar — {query}"
            send_email(to_addr, subject, body)
            print(f"Sent digest to {to_addr}")
        else:
            print(body)
        return

    known = known_content_keys()
    new_records = [r for r in records if (r.source, r.external_id) not in known]

    if new_records:
        # Persist raw .txt artifacts for blog posts (WordPress).
        for rec in new_records:
            if rec.source == "wordpress" and rec.text:
                write_raw_text("wordpress", rec.external_id, rec.text)

        print(f"Ingesting {len(new_records)} new record(s) from RSS/WordPress/NYT...")
        store_content(new_records)
    else:
        print("No new content to ingest (all items already indexed).")

    ideas = build_content_ideas([r.__dict__ for r in new_records] if new_records else [], query)
    body = build_email_body(query=query, per_source=3)
    body = body + "\n\n---\nContent ideas (GPT)\n" + ideas

    if send:
        to_addr = os.environ.get("EMAIL_TO")
        if not to_addr:
            raise RuntimeError("EMAIL_TO must be set to send email")
        subject = f"Content Radar — {query}"
        send_email(to_addr, subject, body)
        print(f"Sent digest to {to_addr}")
    else:
        print(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily scan + digest")
    parser.add_argument("--query", required=True, help="Search query for the digest")
    parser.add_argument("--max-posts", type=int, default=120, help="Max WordPress posts to fetch")
    parser.add_argument("--send", action="store_true", help="Send email instead of printing")
    args = parser.parse_args()

    daily_scan(query=args.query, max_posts=args.max_posts, send=args.send)


if __name__ == "__main__":
    main()
