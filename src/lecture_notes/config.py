"""Configuration: paths, courses and the weekly timetable, read from a TOML file."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True)
class Slot:
    weekday: int  # 0 = Monday
    start: str  # "HH:MM"
    end: str
    course: str


@dataclass
class Course:
    name: str  # folder name and recording prefix, e.g. "Economia Aziendale"
    aliases: list[str] = field(default_factory=list)
    notebook: str | None = None  # NotebookLM notebook title; defaults to the course name


@dataclass
class Config:
    recordings_dir: Path
    courses_dir: Path
    work_dir: Path
    notes_file: str
    courses: dict[str, Course]
    timetable: list[Slot]
    telegram_inbox: Path | None = None
    tolerance_minutes: int = 20
    summary_heading: str = r"schema riassuntivo"  # final chapter that must stay last
    language: str = "it"
    whisper_model: str = "large-v3"  # fallback transcription when NotebookLM refuses an audio
    mml2omml_xsl: Path | None = None  # Office's MathML -> OMML stylesheet, for EQ: lines (found by itself on Windows)

    def course(self, name: str) -> Course:
        key = name.strip().lower()
        for c in self.courses.values():
            if key == c.name.lower() or key in (a.lower() for a in c.aliases):
                return c
        known = ", ".join(sorted(self.courses))
        raise SystemExit(f"Unknown course {name!r}. Known courses: {known}")

    def notes_path(self, course: Course) -> Path:
        return self.courses_dir / course.name / self.notes_file


def _path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def default_config_path() -> Path:
    env = os.environ.get("LECTURE_NOTES_CONFIG")
    return _path(env) if env else Path.home() / ".lecture-notes" / "config.toml"


def load(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        raise SystemExit(f"Config not found: {path}. Copy config.example.toml there and edit it.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    p = data["paths"]
    courses = {
        name: Course(name=name, aliases=c.get("aliases", []), notebook=c.get("notebook"))
        for name, c in data.get("courses", {}).items()
    }
    timetable = [Slot(DAYS[s["day"].lower()[:3]], s["start"], s["end"], s["course"])
                 for s in data.get("timetable", [])]
    opts = data.get("options", {})
    return Config(
        recordings_dir=_path(p["recordings"]),
        courses_dir=_path(p["courses"]),
        work_dir=_path(p.get("work", "~/.lecture-notes/work")),
        notes_file=p.get("notes_file", "TEORIA.docx"),
        telegram_inbox=_path(p["telegram_inbox"]) if p.get("telegram_inbox") else None,
        courses=courses,
        timetable=timetable,
        tolerance_minutes=opts.get("tolerance_minutes", 20),
        summary_heading=opts.get("summary_heading", r"schema riassuntivo"),
        language=opts.get("language", "it"),
        whisper_model=opts.get("whisper_model", "large-v3"),
        mml2omml_xsl=_path(opts["mml2omml_xsl"]) if opts.get("mml2omml_xsl") else None,
    )
