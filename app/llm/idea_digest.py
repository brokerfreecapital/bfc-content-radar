"""Generate content ideas from newly ingested items."""

from __future__ import annotations

import os
from typing import Iterable, List

from openai import OpenAI

DEFAULT_PROMPT = """
You are a sharp content strategist. Read the new items and propose concise ideas for tweets, blog posts, and TikTok hooks. Keep tone clear and actionable, avoid fluff, and include links when provided.
""".strip()


def _load_system_prompt() -> str:
    path = os.environ.get("IDEA_SYSTEM_PROMPT_PATH")
    if path and os.path.exists(path):
        try:
            return open(path, "r", encoding="utf-8").read().strip() or DEFAULT_PROMPT
        except OSError:
            pass
    env_prompt = os.environ.get("IDEA_SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt.strip()
    return DEFAULT_PROMPT


def _format_items(new_items: Iterable[dict], limit: int = 12) -> str:
    lines: List[str] = []
    for idx, rec in enumerate(new_items):
        if idx >= limit:
            break
        title = (rec.get("title") or rec.get("summary") or rec.get("text") or "").strip()
        title = title[:280]
        url = rec.get("url") or ""
        src = rec.get("source") or ""
        lines.append(f"- [{src}] {title}{' ' + url if url else ''}")
    if not lines:
        return "(no new items today; pull ideas from evergreen content)"
    return "\n".join(lines)


def build_content_ideas(new_items: List[dict], query: str) -> str:
    prompt = _load_system_prompt()
    items_text = _format_items(new_items)
    model = os.environ.get("IDEA_MODEL", "gpt-5.2")

    client = OpenAI()
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Topic focus: " + query + "\n\n"
                "New items (most recent first):\n" + items_text + "\n\n"
                "Return concise bullets:\n"
                "- 3 tweet ideas (one line each, include links when useful)\n"
                "- 2 blog post ideas (titles + 1-line angle)\n"
                "- 2 TikTok hooks (short hook + angle)\n"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.6,
        max_completion_tokens=700,
    )

    return response.choices[0].message.content.strip() if response.choices else ""
