"""Slide text and images, so agents can grep instead of looking at every page."""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf

# A page is a figure candidate if it has a sizeable raster image or many vector drawings
# (charts, T-accounts and tables are drawn as vectors in most slide decks).
MIN_IMAGE_PIXELS = 200 * 150
MIN_DRAWINGS = 25


def extract(pdf: Path, out_dir: Path, dpi: int = 130) -> list[dict]:
    """Write slides.txt, a PNG for each figure candidate and slides/index.json."""
    img_dir = out_dir / "slides"
    img_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    index, text = [], []
    for i, page in enumerate(doc, start=1):
        big = 0
        for im in page.get_images(full=True):
            try:
                info = doc.extract_image(im[0])
            except (RuntimeError, ValueError):
                continue
            if info["width"] * info["height"] >= MIN_IMAGE_PIXELS:
                big += 1
        drawings = len(page.get_drawings())
        png = None
        if big or drawings >= MIN_DRAWINGS:
            png = img_dir / f"p{i:02d}.png"
            page.get_pixmap(dpi=dpi).save(png)
        index.append({"page": i, "images": big, "drawings": drawings, "png": png.name if png else None})
        text.append(f"=== Slide {i} ===\n{page.get_text().strip()}")
    (img_dir / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    (out_dir / "slides.txt").write_text("\n\n".join(text), encoding="utf-8")
    return index


def render_page(pdf: Path, page: int, dest: Path, dpi: int = 130) -> Path:
    pymupdf.open(pdf)[page - 1].get_pixmap(dpi=dpi).save(dest)
    return dest


def course_text(course_dir: Path, dest: Path, skip=("scheda insegnamento",), skip_dirs=("esercizi",)) -> int:
    """Text of every PDF in the course folder, used to spot topics with no slides at all."""
    parts = []
    for pdf in sorted(course_dir.rglob("*.pdf")):
        if pdf.name.lower().startswith(skip) or any(d in str(pdf.parent).lower() for d in skip_dirs):
            continue
        try:
            doc = pymupdf.open(pdf)
        except (RuntimeError, ValueError):
            continue
        parts += [f"=== {pdf.name} · Slide {i} ===\n{p.get_text().strip()}" for i, p in enumerate(doc, start=1)]
    dest.write_text("\n\n".join(parts), encoding="utf-8")
    return len(parts)
