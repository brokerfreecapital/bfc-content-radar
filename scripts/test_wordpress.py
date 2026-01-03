import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
from dotenv import load_dotenv

from app.sources.wordpress import fetch_wp_posts

load_dotenv()

BASE_URL = os.environ.get("BLOG_WP_BASE_URL", "https://brokerfreecapital.ai")

posts = fetch_wp_posts(BASE_URL, per_page=5, page=1)
print(f"✅ Fetched {len(posts)} posts from {BASE_URL}\n")

for i, p in enumerate(posts, start=1):
    print(f"{i}) {p['date']} — {p['title']}")
    print(f"   {p['link']}")
    if p["excerpt_text"]:
        print(f"   Excerpt: {p['excerpt_text'][:180]}{'...' if len(p['excerpt_text']) > 180 else ''}")
    print("")
