"""Collect photos of handwritten exercises (e.g. sent to a Telegram bot) into a work folder."""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def recent_photos(inbox: Path, hours: float, used: set[str]) -> list[Path]:
    since = datetime.now() - timedelta(hours=hours)
    return [p for p in sorted(inbox.glob("*"), key=lambda p: p.stat().st_mtime)
            if p.suffix.lower() in PHOTO_EXT and str(p) not in used
            and datetime.fromtimestamp(p.stat().st_mtime) >= since]


def copy_numbered(photos: list[Path], dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    copies = []
    for i, src in enumerate(photos, start=1):
        target = dest / f"photo-{i:02d}{src.suffix.lower()}"
        shutil.copy2(src, target)
        copies.append(target)
    return copies
