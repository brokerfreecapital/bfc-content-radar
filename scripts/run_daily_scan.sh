#!/usr/bin/env bash
set -euo pipefail

# Change to repo root
cd "$(dirname "$0")/.."

PYTHON_BIN=${PYTHON_BIN:-".venv/bin/python"}
QUERY=${QUERY:-"small business finance"}
MAX_POSTS=${MAX_POSTS:-120}
# Default prompt file (can override via env)
export IDEA_SYSTEM_PROMPT_PATH=${IDEA_SYSTEM_PROMPT_PATH:-"app/llm/prompts/content_radar_system.md"}

# Ensure .env is picked up by the Python script (load_dotenv runs inside)
"${PYTHON_BIN}" scripts/daily_scan.py --query "$QUERY" --max-posts "$MAX_POSTS" --send
