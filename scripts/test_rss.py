import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from app.sources.rss import fetch_rss_posts

load_dotenv()

feed_url = os.environ.get("BLOG_RSS_URL", "https://brokerfreecapital.ai/?feed=content_radar")
posts = fetch_rss_posts(feed_url, limit=5)

print(f"✅ Fetched {len(posts)} items from {feed_url}\n")
for i, p in enumerate(posts, start=1):
    print(f"{i}) {p['published']} — {p['title']}")
    print(f"   {p['link']}")
    if p["summary_text"]:
        print(f"   Summary: {p['summary_text'][:180]}{'...' if len(p['summary_text']) > 180 else ''}")
    print("")
