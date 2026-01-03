## Environment

Required env vars (see `.env`):
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- `OPENAI_API_KEY`
- `BLOG_WP_BASE_URL`, `BLOG_RSS_URL`
- `ROOT_DRIVE_FOLDER_ID`, `TIKTOK_TRANSCRIPTS_FOLDER_NAME`
- `EMAIL_TO`
- `NYT_API_KEY` (for Times Wire and Article Search)
- `IDEA_MODEL` (optional, default `gpt-5.2`)
- `IDEA_SYSTEM_PROMPT` or `IDEA_SYSTEM_PROMPT_PATH` (optional; e.g., `app/llm/prompts/content_radar_system.md`)

Note: NYT ingestion uses API metadata only (headline/abstract/link).

## Daily scan

Run a daily pull + digest:
```
/Users/jasonfleming/bfc-content-radar/.venv/bin/python scripts/daily_scan.py --query "small business lending" --max-posts 120
```
Add `--send` to email via Gmail API.

What it does now:
- Fetches RSS (main + external feeds), WordPress, and NYT (metadata only).
- Only ingests new `(source, external_id)` items; skips ones already indexed.
- Saves raw `.txt` for WordPress posts (and TikTok transcripts when using `scripts/ingest_content.py`) under `data/raw/<source>/`.
- Writes normalized records to `data/content_records.jsonl` and embeddings to `data/content_memory.sqlite`.
- Builds a digest from the memory search and appends a GPT-generated "Content ideas" section (tweets, blog ideas, TikTok hooks). Customize the system prompt with `IDEA_SYSTEM_PROMPT` or a file path.

Schedule at 8:00 AM US/Eastern via cron (server uses UTC):
```
# Runs 13:00 UTC = 08:00 ET (adjust for DST as needed)
0 13 * * * cd /Users/jasonfleming/bfc-content-radar && ./scripts/run_daily_scan.sh
```
You can override defaults via env in the crontab line, e.g.:
```
QUERY="technology" MAX_POSTS=80 IDEA_SYSTEM_PROMPT_PATH="app/llm/prompts/content_radar_system.md" 0 13 * * * cd /Users/jasonfleming/bfc-content-radar && ./scripts/run_daily_scan.sh
```
For GitHub Actions, set a cron like `0 13 * * *` and export your env vars as secrets.
