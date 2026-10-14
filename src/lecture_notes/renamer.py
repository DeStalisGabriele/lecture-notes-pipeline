"""Name raw recordings "<Course> - Lezione N - Parte K" from the time they were recorded.

The recorder gives files generic names. Instead of transcribing a few minutes to guess the
course (slow, and it costs tokens), the recording time is matched against the weekly timetable:
start = file modification time - audio duration, and the slot that contains the midpoint wins.
Phone recorders that put the timestamp in the name ("Voce 261013_132552") are read from the
name, because a file received from someone else carries the download time.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config, Slot

LECTURE_NAME = re.compile(r"^(?P<course>.+) - Lezione (?P<n>\d+) - Parte (?P<part>\d+)$")
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".opus", ".webm"}
PHONE_STAMP = re.compile(r"(\d{6})_(\d{6})")


@dataclass
class Plan:
    source: Path
    target: Path | None
    start: datetime
    end: datetime
    reason: str = ""


def audio_duration(path: Path) -> float | None:
    """Duration in seconds via ffprobe, or None if ffprobe is missing or fails."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def recording_window(path: Path, duration: float | None) -> tuple[datetime, datetime]:
    if m := PHONE_STAMP.search(path.stem):
        start = datetime.strptime(m[1] + m[2], "%y%m%d%H%M%S")
        return start, start + timedelta(seconds=duration or 0)
    end = datetime.fromtimestamp(path.stat().st_mtime)
    start = end - timedelta(seconds=duration) if duration else datetime.fromtimestamp(path.stat().st_ctime)
    return start, end


def course_at(moment: datetime, timetable: list[Slot], tolerance_minutes: int = 20) -> str | None:
    """Course whose slot contains `moment` (with some tolerance for early or late starts)."""
    tol = timedelta(minutes=tolerance_minutes)
    for slot in timetable:
        if slot.weekday != moment.weekday():
            continue
        (h0, m0), (h1, m1) = (map(int, slot.start.split(":")), map(int, slot.end.split(":")))
        t0 = moment.replace(hour=h0, minute=m0, second=0, microsecond=0)
        t1 = moment.replace(hour=h1, minute=m1, second=0, microsecond=0)
        if t0 - tol <= moment <= t1 + tol:
            return slot.course
    return None


def plan_renames(cfg: Config, now: datetime | None = None, settle_minutes: int = 3,
                 duration=audio_duration) -> list[Plan]:
    """Work out the new names without touching any file."""
    now = now or datetime.now()
    files = [p for p in cfg.recordings_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT]

    # lecture number already used by each (course, day)
    done: dict[str, dict] = {}
    for p in files:
        if m := LECTURE_NAME.match(p.stem):
            day = datetime.fromtimestamp(p.stat().st_mtime).date()
            done.setdefault(m["course"], {})[day] = int(m["n"])

    taken = {p.name for p in files}
    plans = []
    for p in sorted((f for f in files if not LECTURE_NAME.match(f.stem)), key=lambda f: f.stat().st_mtime):
        start, end = recording_window(p, duration(p))
        if now - datetime.fromtimestamp(p.stat().st_mtime) < timedelta(minutes=settle_minutes):
            plans.append(Plan(p, None, start, end, "modified moments ago, probably still recording"))
            continue
        course = course_at(start + (end - start) / 2, cfg.timetable, cfg.tolerance_minutes)
        if not course:
            plans.append(Plan(p, None, start, end, "outside the timetable"))
            continue
        per_course = done.setdefault(course, {})
        n = per_course.get(end.date()) or max(per_course.values(), default=0) + 1
        per_course[end.date()] = n
        part = 1
        while f"{course} - Lezione {n} - Parte {part}{p.suffix}" in taken:
            part += 1
        name = f"{course} - Lezione {n} - Parte {part}{p.suffix}"
        taken.add(name)
        plans.append(Plan(p, p.with_name(name), start, end))
    return plans


def apply(plans: list[Plan]) -> None:
    for plan in plans:
        if plan.target is None:
            continue
        plan.source.rename(plan.target)
        # file time = end of recording, so later lecture numbering stays right
        os.utime(plan.target, (plan.end.timestamp(), plan.end.timestamp()))
