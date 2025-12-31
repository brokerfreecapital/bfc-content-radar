import sys
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
from dotenv import load_dotenv

from app.sources.drive import list_child_folders, list_txt_files, download_text

load_dotenv()

root = os.environ["ROOT_DRIVE_FOLDER_ID"]
folders = list_child_folders(root)

from app.sources.drive import get_file_metadata

meta = get_file_metadata(root)
print("✅ Root folder metadata:", meta)


print("✅ Child folders under root:")
for name, fid in folders.items():
    print(f" - {name}: {fid}")

target_name = os.environ.get("TIKTOK_TRANSCRIPTS_FOLDER_NAME", "BFC_TikTok_Transcripts").strip().strip("/")
target_id = folders.get(target_name)

if not target_id:
    raise SystemExit(f"\n❌ Could not find '{target_name}'. Found: {list(folders.keys())}")

files = list_txt_files(target_id)
print(f"\n✅ Found {len(files)} .txt transcript files in {target_name}")

if files:
    newest = files[0]
    print(f"\n--- Newest: {newest['name']} ({newest['id']}) ---")
    text = download_text(newest["id"])
    print(text[:800])
    print("\n--- (truncated) ---")
else:
    print("\n(No transcripts yet. Drop a .txt into the Drive folder and rerun.)")
