---
name: exercises
description: Turn photos of handwritten exercises or notes (e.g. sent to a Telegram bot) into clean exercises appended to the course's Word notes, with T-accounts in the same format. Use when the user says "exercises <course>" or "/exercises <course>" after sending photos.
---

# /exercises — from handwritten photos to clean notes

1. `lecture-notes photos <course> [FILES…]` — without files it takes the photos received in the configured Telegram inbox in the last 6 hours and not used yet (`--hours N` to change). Tell the user how many photos were picked.
2. Subagent `scribe`: give it the course, the copied photos in order and `<folder>/exercises.md`. With more than 8 photos, split them across several scribes in parallel and merge their files in order.
3. Check: no `$`; calculations are `EQ: <LaTeX> || <comment>` lines (they become Word equations); T-accounts written as `MASTRINO:` / `DARE:` / `AVERE:` lines.
4. `lecture-notes photos-write <folder> <folder>/exercises.md` — backs up, appends before a final summary chapter, marks the photos as used.
5. Report: exercises added, unreadable spots, mistakes found in the maths.
