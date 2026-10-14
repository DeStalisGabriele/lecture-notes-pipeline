import os
from datetime import datetime
from pathlib import Path

from lecture_notes.config import Config, Course, Slot
from lecture_notes.renamer import course_at, plan_renames, recording_window

TIMETABLE = [
    Slot(0, "08:30", "11:30", "Sistema Economico"),
    Slot(0, "11:30", "14:30", "Sistemi Informativi Aziendali"),
    Slot(1, "13:00", "16:00", "Sistema Economico"),
    Slot(1, "16:00", "19:00", "Economia Aziendale"),
]


def cfg_for(folder: Path) -> Config:
    return Config(recordings_dir=folder, courses_dir=folder, work_dir=folder, notes_file="TEORIA.docx",
                  courses={c: Course(c) for c in {s.course for s in TIMETABLE}}, timetable=TIMETABLE)


def touch(path: Path, end: datetime) -> Path:
    path.write_bytes(b"")
    os.utime(path, (end.timestamp(), end.timestamp()))
    return path


def test_course_at_picks_the_slot_containing_the_moment():
    assert course_at(datetime(2026, 10, 12, 10, 0), TIMETABLE) == "Sistema Economico"      # Monday
    assert course_at(datetime(2026, 10, 12, 13, 0), TIMETABLE) == "Sistemi Informativi Aziendali"
    assert course_at(datetime(2026, 10, 13, 17, 30), TIMETABLE) == "Economia Aziendale"    # Tuesday


def test_course_at_tolerance_and_free_days():
    assert course_at(datetime(2026, 10, 13, 12, 45), TIMETABLE) == "Sistema Economico"  # 15 min early
    assert course_at(datetime(2026, 10, 13, 12, 0), TIMETABLE) is None
    assert course_at(datetime(2026, 10, 14, 10, 0), TIMETABLE) is None  # Wednesday: no lectures


def test_phone_recorder_timestamp_wins_over_file_time(tmp_path):
    f = touch(tmp_path / "Voce 261013_132552.m4a", datetime(2026, 10, 14, 9, 9))  # downloaded the day after
    start, end = recording_window(f, 2779.8)
    assert start == datetime(2026, 10, 13, 13, 25, 52)
    assert (end - start).total_seconds() == 2779.8


def test_plan_continues_numbering_and_parts(tmp_path):
    touch(tmp_path / "Sistema Economico - Lezione 7 - Parte 1.m4a", datetime(2026, 10, 12, 9, 40))
    touch(tmp_path / "Sistema Economico - Lezione 7 - Parte 2.m4a", datetime(2026, 10, 12, 11, 0))
    a = touch(tmp_path / "Registrazione (1).m4a", datetime(2026, 10, 13, 14, 12))
    b = touch(tmp_path / "Registrazione (2).m4a", datetime(2026, 10, 13, 15, 38))
    durations = {a: 2780.0, b: 3658.0}
    plans = plan_renames(cfg_for(tmp_path), now=datetime(2026, 10, 14, 9, 0), duration=lambda p: durations[p])
    names = [p.target.name for p in plans]
    assert names == ["Sistema Economico - Lezione 8 - Parte 1.m4a", "Sistema Economico - Lezione 8 - Parte 2.m4a"]


def test_plan_skips_files_still_being_recorded_and_out_of_timetable(tmp_path):
    touch(tmp_path / "Registrazione (3).m4a", datetime(2026, 10, 14, 10, 0))  # Wednesday
    touch(tmp_path / "Registrazione (4).m4a", datetime(2026, 10, 14, 11, 59))  # just saved
    plans = plan_renames(cfg_for(tmp_path), now=datetime(2026, 10, 14, 12, 0), duration=lambda p: 1800.0)
    reasons = sorted(p.reason for p in plans)
    assert all(p.target is None for p in plans)
    assert reasons == ["modified moments ago, probably still recording", "outside the timetable"]
