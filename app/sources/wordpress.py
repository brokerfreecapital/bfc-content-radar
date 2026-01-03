import re
import requests
from typing import List, Optional


def _strip_html(html: str) -> str:
    # Simple HTML tag stripper (good enough for excerpts/content)
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_wp_posts(
    base_url: str,
    per_page: int = 20,
    page: int = 1,
    timeout_s: int = 20,
) -> List[dict]:
    url = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts"
    params = {
        "per_page": per_page,
        "page": page,
        "_fields": "id,date,link,title,excerpt,content,slug",
        "status": "publish",
        "orderby": "date",
        "order": "desc",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    resp.raise_for_status()
    posts = resp.json()
    ...


    resp = requests.get(url, params=params, timeout=timeout_s)
    resp.raise_for_status()
    posts = resp.json()

    out: List[dict] = []
    for p in posts:
        title_html = (p.get("title") or {}).get("rendered", "")
        excerpt_html = (p.get("excerpt") or {}).get("rendered", "")
        content_html = (p.get("content") or {}).get("rendered", "")

        out.append({
            "id": p.get("id"),
            "date": p.get("date"),
            "slug": p.get("slug"),
            "title": _strip_html(title_html),
            "link": p.get("link"),
            "excerpt_text": _strip_html(excerpt_html),
            "content_text": _strip_html(content_html),
        })

    return out


def fetch_wp_posts_all(
    base_url: str,
    max_posts: int = 200,
    per_page: int = 50,
) -> List[dict]:
    """
    Paginate until we hit max_posts or run out.
    """
    out: List[dict] = []
    page = 1

    while len(out) < max_posts:
        batch = fetch_wp_posts(base_url=base_url, per_page=per_page, page=page)
        if not batch:
            break
        out.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return out[:max_posts]
