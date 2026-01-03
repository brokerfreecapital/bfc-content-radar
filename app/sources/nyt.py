"""NYT helpers for Times Wire and Article Search.

This module intentionally does NOT attempt to scrape full paywalled article
text. It uses only the NYT APIs and returns reliable metadata: headline,
abstract/snippet, and link.
"""

from __future__ import annotations

import httpx

TIMES_WIRE_URL = "https://api.nytimes.com/svc/news/v3/content/all/{section}.json"
ARTICLE_SEARCH_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"


def fetch_times_wire(api_key: str, section: str = "business", limit: int = 20) -> list[dict]:
    params = {
        "api-key": api_key,
        "limit": limit,
    }
    url = TIMES_WIRE_URL.format(section=section)
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    out: list[dict] = []
    for item in data.get("results", [])[:limit]:
        abstract = item.get("abstract") or ""
        out.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url"),
                "published": item.get("published_date"),
                "summary": abstract,
                "text": abstract,
                "section": item.get("section"),
                "subsection": item.get("subsection"),
                "source_type": "times_wire",
                "paywalled": True,
            }
        )
    return out


def fetch_article_search(
    api_key: str,
    query: str,
    section_filter: str | None = "Business",
    limit: int = 20,
) -> list[dict]:
    params = {
        "api-key": api_key,
        "q": query,
        "sort": "newest",
        "page": 0,
    }
    if section_filter:
        params["fq"] = f'section_name:("{section_filter}")'

    out: list[dict] = []
    with httpx.Client(timeout=15) as client:
        while len(out) < limit:
            params["page"] = len(out) // 10  # NYT paginates 10 per page
            resp = client.get(ARTICLE_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            docs = (data.get("response") or {}).get("docs") or []
            if not docs:
                break
            for doc in docs:
                summary = doc.get("abstract") or (doc.get("snippet") or "")
                text = doc.get("lead_paragraph") or summary
                out.append(
                    {
                        "title": (doc.get("headline") or {}).get("main", ""),
                        "url": doc.get("web_url"),
                        "published": doc.get("pub_date"),
                        "summary": summary,
                        "text": text,
                        "section": doc.get("section_name"),
                        "subsection": doc.get("subsection_name"),
                        "source_type": "article_search",
                        "paywalled": True,
                    }
                )
                if len(out) >= limit:
                    break
            # Stop if fewer than 10 returned (end of results)
            if len(docs) < 10:
                break
    return out
