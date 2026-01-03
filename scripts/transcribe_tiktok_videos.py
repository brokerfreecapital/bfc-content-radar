"""Download TikTok videos from Google Drive and create transcripts.

This script looks for MP4 files in the TikTok videos folder, sends them to
OpenAI's transcription API, and uploads resulting .txt files into the TikTok
transcripts folder. Requires:

- Environment variables:
  * ROOT_DRIVE_FOLDER_ID
  * TIKTOK_VIDEOS_FOLDER_NAME (defaults to "BFC_TikTok_Videos")
  * TIKTOK_TRANSCRIPTS_FOLDER_NAME (defaults to "BFC_TikTok_Transcripts")
  * OPENAI_API_KEY
- Dependencies from requirements.txt (google api clients, openai, python-dotenv)

Usage:
    python scripts/transcribe_tiktok_videos.py [--limit 3] [--force]

By default, already-transcribed videos are skipped (matching on base filename).
Use --force to regenerate transcripts.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

from dotenv import load_dotenv

# Ensure repo root is on path when running as script
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openai import OpenAI

from app.sources.drive import (
    download_file,
    list_child_folders,
    list_files,
    upload_text_file,
)

VIDEO_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
]
TRANSCRIPT_MIME_TYPES = ["text/plain"]


def _normalize_name(filename: str) -> str:
    return Path(filename).stem.strip().lower()


def gather_drive_folder_id(root_folder_id: str, folder_name: str) -> str:
    folders = list_child_folders(root_folder_id)
    normalized = folder_name.strip().strip("/")
    if normalized not in folders:
        raise RuntimeError(
            f"Folder '{folder_name}' not found under Drive root {root_folder_id}."
            f" Available: {list(folders.keys())}"
        )
    return folders[normalized]


def transcribe_videos(limit: int | None, force: bool) -> None:
    load_dotenv()

    root_folder_id = os.environ["ROOT_DRIVE_FOLDER_ID"]
    videos_folder_name = os.environ.get("TIKTOK_VIDEOS_FOLDER_NAME", "BFC_TikTok_Videos")
    transcripts_folder_name = os.environ.get(
        "TIKTOK_TRANSCRIPTS_FOLDER_NAME",
        "BFC_TikTok_Transcripts",
    )

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for transcription.")

    videos_folder_id = gather_drive_folder_id(root_folder_id, videos_folder_name)
    transcripts_folder_id = gather_drive_folder_id(root_folder_id, transcripts_folder_name)

    video_files = list_files(videos_folder_id, mime_types=VIDEO_MIME_TYPES)
    transcript_files = list_files(transcripts_folder_id, mime_types=TRANSCRIPT_MIME_TYPES)

    existing_transcripts = {
        _normalize_name(f["name"]): f for f in transcript_files
    }

    client = OpenAI()

    pending = []
    for video in video_files:
        base = _normalize_name(video["name"])
        if not force and base in existing_transcripts:
            continue
        pending.append(video)
        if limit and len(pending) >= limit:
            break

    if not pending:
        print("✅ No videos to transcribe. All caught up!")
        return

    print(f"Transcribing {len(pending)} video(s)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        for video in pending:
            base = _normalize_name(video["name"])
            local_path = tmpdir_path / video["name"]
            print(f"⬇️  Downloading {video['name']} ({video['id']})...")
            download_file(video["id"], str(local_path))

            print("🎙️  Sending to OpenAI transcription API...")
            with open(local_path, "rb") as file_handle:
                response = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=file_handle,
                )

            transcript_text = (response.text or "").strip()
            if not transcript_text:
                print(f"⚠️  Empty transcript returned for {video['name']}. Skipping upload.")
                continue

            transcript_filename = f"{base}.txt"
            print(f"☁️  Uploading transcript as {transcript_filename}...")
            upload_text_file(transcripts_folder_id, transcript_filename, transcript_text)
            print(f"✅ Completed {video['name']}")

    print("✨ Done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe TikTok videos from Drive")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to process")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if a transcript already exists",
    )
    args = parser.parse_args()

    transcribe_videos(limit=args.limit, force=args.force)


if __name__ == "__main__":
    main()
