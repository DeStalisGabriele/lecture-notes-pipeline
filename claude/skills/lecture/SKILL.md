---
name: lecture
description: Turn a lecture recording into notes appended to the course's Word document. Use when the user says "lecture N <course>", "/lecture N <course>" or just "lecture done". NotebookLM transcribes and drafts (free), the slide-scout picks figures and reports missing slides, the editor writes the notes.
---

# /lecture — from recordings to notes

Arguments: lecture number and course, in any order. Optional: `slides <file>` when the lecture's deck is not the newest PDF in the course folder. With no arguments, use the lecture just named in step 0.

All commands are `lecture-notes …` (see `config.example.toml`). Work folder: `<work>/<course>-lecture-<n>/`.

**Goal: few Claude tokens.** NotebookLM writes the word-for-word transcript and the draft; mechanical steps are scripts; agents read the draft and grep the rest.

0. `lecture-notes rename --apply` — names new recordings from the timetable. "SKIP … outside the timetable" lines: ask the user which lecture it is.
1. `lecture-notes prepare <course> <n>` — show which slide deck was picked.
2. In parallel, scripts only:
   - `lecture-notes notebook <course> <n>` **in the background** (5-30 min): uploads recordings and slides to the course notebook (reusing sources already there), downloads `transcript - Parte K.txt` and `draft.md`.
   - `lecture-notes slides <course> <n>`: `slides.txt`, `slides/pNN.png`, `all-slides.txt`, `notes-outline.txt`.
3. When `draft.md` exists, two subagents in parallel, in the background: `slide-scout` and `editor`, each given the work folder.
4. Merge: swap figure references in `notes.md` for the ones in `figures.json`; check there is no `$` (LaTeX) and that every PNG exists. Then `lecture-notes write <course> <n> <folder>/notes.md` (backs up the document, keeps a final summary chapter last, continues numbering, builds T-accounts).
5. Report: chapters added, figures inserted and **missing slides**, so the user can download them.

## When something fails
- `notebook` fails with an auth error (check with `lecture-notes auth`): the Google session expired. Ask the user to sign in again (`notebooklm login`, or `scripts/login-and-push.ps1` when you run on a server), then run `notebook` again: sources already uploaded are reused. Never type credentials for them.
- `notebook` fails with `Source processing failed` on a recording (type `unknown`): NotebookLM refused the audio upload. With the `[whisper]` extra installed, `notebook` already handles it: it transcribes the recording locally with Whisper, uploads the text under the same title and goes on, so just run `notebook` again if it stopped. Without the extra, tell the user to install it (`pip install -e ".[whisper]"`), ideally on a machine with an NVIDIA GPU.
- `write` says the document is open in Word: ask the user to close it, then run `write` again.
- On a server, recordings arrive through Syncthing: before `prepare`, check that their size has stopped growing.
