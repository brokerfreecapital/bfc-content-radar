"""Write raw text artifacts to disk.

Used to keep a plain-text archive (e.g., blog posts, transcripts).
"""

from __future__ import annotations

import re
from pathlib import Path

RAW_DIR = Path("data") / "raw"


def _safe_filename(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "untitled"
    # Keep filenames portable: letters, numbers, dash, underscore, dot.
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value[:180].strip("._-") or "untitled"


def write_raw_text(source: str, external_id: str, text: str) -> Path:
    """Write raw UTF-8 text to `data/raw/<source>/<external_id>.txt`.

    Returns the path written.
    """
    src = _safe_filename(source)
    filename = _safe_filename(external_id) + ".txt"

    out_dir = RAW_DIR / src
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / filename
    out_path.write_text((text or "").strip() + "\n", encoding="utf-8")
    return out_path
