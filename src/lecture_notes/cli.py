"""lecture-notes: from lecture recordings and photos of handwritten exercises to Word notes.

  lecture-notes rename [--apply]                  name new recordings from the timetable
  lecture-notes prepare COURSE N [--slides PDF]   find audio and slides, create the work folder
  lecture-notes notebook COURSE N                 NotebookLM: upload, transcripts, draft
  lecture-notes slides COURSE N                   slide text, figure PNGs, course-wide slide text
  lecture-notes write COURSE N NOTES.md           append notes to the course's Word document
  lecture-notes photos COURSE [FILES...] [--hours H]   start an exercises folder from photos
  lecture-notes photos-write FOLDER NOTES.md      append transcribed exercises
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import docx_writer, notebooklm, photos, renamer, slides
from .config import Config, Course, load


def slug(text: str) -> str:
    return text.lower().replace(" ", "-")


def work_folder(cfg: Config, course: Course, n: int) -> Path:
    folder = cfg.work_dir / f"{slug(course.name)}-lecture-{n}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_state(folder: Path) -> dict:
    path = folder / "state.json"
    if not path.exists():
        raise SystemExit(f"No state.json in {folder}: run 'prepare' first.")
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(folder: Path, state: dict) -> None:
    (folder / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_rename(cfg: Config, args) -> None:
    plans = renamer.plan_renames(cfg)
    for p in plans:
        when = f"{p.start:%a %d/%m %H:%M}"
        if p.target:
            print(f"{'RENAME' if args.apply else 'WOULD RENAME'} {p.source.name} -> {p.target.name} (recorded {when})")
        else:
            print(f"SKIP {p.source.name}: {p.reason} ({when})")
    if args.apply:
        renamer.apply(plans)
    if not plans:
        print("No new recordings.")


def cmd_prepare(cfg: Config, args) -> None:
    course = cfg.course(args.course)
    audio = sorted(cfg.recordings_dir.glob(f"{course.name} - Lezione {args.n} - Parte *.*"))
    if not audio:
        raise SystemExit(f"No '{course.name} - Lezione {args.n} - Parte K' recordings in {cfg.recordings_dir}")
    course_dir = cfg.courses_dir / course.name
    if args.slides:
        pdf = Path(args.slides)
        pdf = pdf if pdf.is_absolute() else course_dir / pdf
    else:  # default: the most recently added deck in the course folder
        decks = [p for p in course_dir.glob("*.pdf") if not p.name.lower().startswith("scheda insegnamento")]
        pdf = max(decks, key=lambda p: p.stat().st_mtime) if decks else None
    folder = work_folder(cfg, course, args.n)
    state = {"course": course.name, "lecture": args.n, "audio": [str(a) for a in audio],
             "slides": str(pdf) if pdf and pdf.exists() else None,
             "notes": str(cfg.notes_path(course)), "folder": str(folder)}
    write_state(folder, state)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_notebook(cfg: Config, args) -> None:
    course = cfg.course(args.course)
    folder = work_folder(cfg, course, args.n)
    state = read_state(folder)
    nb = state.get("notebook_id") or notebooklm.find_or_create_notebook(course.notebook or course.name)
    state["notebook_id"] = nb
    sources = state.setdefault("sources", {})
    ready = notebooklm.ready_sources(nb)
    for f in state["audio"] + ([state["slides"]] if state.get("slides") else []):
        path = Path(f)
        if path.name in sources:
            continue
        if path.name in ready:
            print(f"{path.name} already in NotebookLM, reusing it.", flush=True)
            sources[path.name] = ready[path.name]
        else:
            print(f"Uploading {path.name} ...", flush=True)
            sources[path.name] = notebooklm.add_file(nb, path)
        write_state(folder, state)
    for title, sid in sources.items():
        print(f"Waiting for {title} ...", flush=True)
        notebooklm.wait(nb, sid)
    for title, sid in sources.items():
        if not title.lower().endswith(".pdf"):
            dest = folder / f"transcript - {Path(title).stem.split(' - ')[-1]}.txt"
            notebooklm.fulltext(nb, sid, dest)
            print(f"Transcript: {dest.name}")
    prompt = folder / "draft-prompt.txt"
    prompt.write_text(notebooklm.DRAFT_PROMPT_IT.format(n=args.n, course=course.name), encoding="utf-8")
    print("Generating the draft in NotebookLM ...", flush=True)
    notebooklm.draft(nb, list(sources.values()), prompt, folder / "draft.md", cfg.language)
    state["draft"] = str(folder / "draft.md")
    write_state(folder, state)
    print(f"Draft: {folder / 'draft.md'}")


def cmd_slides(cfg: Config, args) -> None:
    course = cfg.course(args.course)
    folder = work_folder(cfg, course, args.n)
    state = read_state(folder)
    if state.get("slides"):
        index = slides.extract(Path(state["slides"]), folder)
        print(f"{len(index)} slides, {sum(1 for i in index if i['png'])} figure candidates")
    pages = slides.course_text(cfg.courses_dir / course.name, folder / "all-slides.txt")
    notes = Path(state["notes"])
    if notes.exists():
        (folder / "notes-outline.txt").write_text("\n".join(docx_writer.outline(notes)), encoding="utf-8")
    print(f"{pages} pages of course slides indexed")


def _write(cfg: Config, notes: Path, md: Path, folder: Path) -> None:
    # Word's lock file: "~$" + the name, minus up to two leading characters depending on its length
    if any(notes.with_name("~$" + notes.name[k:]).exists() for k in (0, 1, 2)):
        raise SystemExit(f"{notes.name} is open in Word: close it and run again.")
    added = docx_writer.append_markdown(notes, md, backup_dir=folder, summary_heading=cfg.summary_heading)
    print(json.dumps(added, ensure_ascii=False, indent=2))


def cmd_write(cfg: Config, args) -> None:
    course = cfg.course(args.course)
    folder = work_folder(cfg, course, args.n)
    _write(cfg, Path(read_state(folder)["notes"]), Path(args.file), folder)


def cmd_photos(cfg: Config, args) -> None:
    course = cfg.course(args.course)
    used_file = cfg.work_dir / "used-photos.txt"
    used = set(used_file.read_text(encoding="utf-8").splitlines()) if used_file.exists() else set()
    if args.files:
        chosen = [Path(f) for f in args.files]
    else:
        if not cfg.telegram_inbox:
            raise SystemExit("No photos given and no telegram_inbox configured.")
        chosen = photos.recent_photos(cfg.telegram_inbox, args.hours, used)
    if not chosen:
        raise SystemExit("No new photos found.")
    folder = cfg.work_dir / f"{slug(course.name)}-exercises-{time.strftime('%Y%m%d-%H%M')}"
    copies = photos.copy_numbered(chosen, folder / "photos")
    notes = cfg.notes_path(course)
    if notes.exists():
        (folder / "notes-outline.txt").write_text("\n".join(docx_writer.outline(notes)), encoding="utf-8")
    state = {"course": course.name, "notes": str(notes), "folder": str(folder),
             "photos": [str(c) for c in copies], "origin": [str(c) for c in chosen]}
    write_state(folder, state)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_photos_write(cfg: Config, args) -> None:
    folder = Path(args.folder)
    state = read_state(folder)
    _write(cfg, Path(state["notes"]), Path(args.file), folder)
    with (cfg.work_dir / "used-photos.txt").open("a", encoding="utf-8") as f:
        f.writelines(o + "\n" for o in state.get("origin", []))


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="lecture-notes", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, help="config file (default: ~/.lecture-notes/config.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("rename"); s.add_argument("--apply", action="store_true"); s.set_defaults(fn=cmd_rename)
    s = sub.add_parser("prepare"); s.add_argument("course"); s.add_argument("n", type=int)
    s.add_argument("--slides"); s.set_defaults(fn=cmd_prepare)
    for name, fn in (("notebook", cmd_notebook), ("slides", cmd_slides)):
        s = sub.add_parser(name); s.add_argument("course"); s.add_argument("n", type=int); s.set_defaults(fn=fn)
    s = sub.add_parser("write"); s.add_argument("course"); s.add_argument("n", type=int); s.add_argument("file")
    s.set_defaults(fn=cmd_write)
    s = sub.add_parser("photos"); s.add_argument("course"); s.add_argument("files", nargs="*")
    s.add_argument("--hours", type=float, default=6); s.set_defaults(fn=cmd_photos)
    s = sub.add_parser("photos-write"); s.add_argument("folder"); s.add_argument("file")
    s.set_defaults(fn=cmd_photos_write)
    args = ap.parse_args(argv)
    args.fn(load(args.config), args)


if __name__ == "__main__":
    main()
