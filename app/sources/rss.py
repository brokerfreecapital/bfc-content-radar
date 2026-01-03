import re
from typing import List, Set
import feedparser


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_rss_posts(feed_url: str, limit: int = 20) -> List[dict]:
    """
    Returns list of dicts: title, link, published, summary_text.
    Basic de-duplication removes repeated entries based on title/link.
    """
    d = feedparser.parse(
        feed_url,
        request_headers={
            "User-Agent": "Mozilla/5.0 (compatible; BFC-Content-Radar/1.0; +https://brokerfreecapital.ai)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        },
    )

    if getattr(d, "status", 200) >= 400:
        raise RuntimeError(f"RSS fetch failed with status {getattr(d, 'status', 'unknown')} for {feed_url}")

    out: List[dict] = []
    seen: Set[str] = set()

    for e in d.entries or []:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()

        if not title and not link:
            continue

        dedupe_key = "::".join([title.lower(), link.lower()])
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        out.append({
            "title": title,
            "link": link,
            "published": e.get("published") or e.get("updated") or "",
            "summary_text": _strip_html(e.get("summary", "")),
        })

        if len(out) >= limit:
            break

    return out
