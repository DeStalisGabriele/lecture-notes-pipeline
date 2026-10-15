"""Thin wrapper around the notebooklm-py CLI (unofficial NotebookLM API).

NotebookLM does the expensive part for free on a student plan: the word-for-word transcript of
each recording (the "fulltext" of an audio source) and a first draft of the notes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DRAFT_PROMPT_IT = """Scrivi in italiano gli appunti completi della lezione {n} di {course}, usando SOLO le fonti selezionate (registrazione della lezione e slide).
Regole:
- Segui l'ordine in cui il docente spiega gli argomenti.
- Titoli: "# Titolo argomento" per ogni argomento principale e "## Titolo" per i sottoargomenti. Niente numeri nei titoli.
- Spiega in modo completo e chiaro, come appunti da studiare: definizioni precise, formule, passaggi dei calcoli, esempi ed esercizi svolti a voce dal docente, casi reali citati.
- Segnala con "**Attenzione:**" le cose che il docente dice importanti per l'esame.
- Quando un concetto si riferisce a una slide con un grafico, una tabella o uno schema, scrivi su una riga a parte: [FIGURA: "titolo della slide copiato esattamente com'è scritto nella slide" | breve descrizione]. Non indicare numeri di pagina.
- Non inventare nulla che non sia nelle fonti. Niente introduzioni o conclusioni generiche.
"""


class NotebookLMError(RuntimeError):
    pass


def run(*args: str, timeout: int = 900) -> str:
    cmd = [sys.executable, "-m", "lecture_notes._nlm", *args]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if out.returncode != 0:
        raise NotebookLMError(f"notebooklm {' '.join(args[:2])}: {(out.stderr or out.stdout).strip()[-2000:]}")
    return out.stdout


def run_json(*args: str, timeout: int = 900):
    text = run(*args, "--json", timeout=timeout)
    return json.loads(text[min(i for i in (text.find("{"), text.find("[")) if i >= 0):])


def auth_status() -> tuple[bool, str]:
    """(signed in?, message). The Google session expires every few weeks; a server can't sign in again
    by itself (no browser), so this is meant for a daily check that warns the user."""
    try:
        notebooks = run_json("list", timeout=120).get("notebooks", [])
    except (NotebookLMError, ValueError) as e:
        expired = "auth" in str(e).lower()
        return False, "NotebookLM session expired: run `notebooklm login`." if expired else str(e)
    return True, f"Signed in to NotebookLM ({len(notebooks)} notebooks)."


def find_or_create_notebook(title: str) -> str:
    for nb in run_json("list").get("notebooks", []):
        if (nb.get("title") or "").strip().lower() == title.lower():
            return nb["id"]
    created = run_json("create", title)
    return (created.get("notebook") or created)["id"]


def ready_sources(notebook_id: str) -> dict[str, str]:
    """title -> id of the sources that finished processing (half-uploaded ones are ignored)."""
    sources = run_json("source", "list", "-n", notebook_id).get("sources", [])
    return {s["title"]: s["id"] for s in sources if s.get("status") == "ready"}


def add_file(notebook_id: str, path: Path, title: str | None = None) -> str:
    res = run_json("source", "add", str(path), "-n", notebook_id, "--title", title or path.name,
                   "--request-timeout", "900", timeout=1200)
    return (res.get("source") or res)["id"]


def delete(notebook_id: str, source_id: str) -> None:
    run("source", "delete", source_id, "-n", notebook_id, "-y")


def wait(notebook_id: str, source_id: str) -> None:
    run("source", "wait", source_id, "-n", notebook_id, timeout=3600)


def fulltext(notebook_id: str, source_id: str, dest: Path) -> None:
    run("source", "fulltext", source_id, "-n", notebook_id, "-o", str(dest), "--force")


def draft(notebook_id: str, source_ids: list[str], prompt_file: Path, dest: Path, language: str) -> None:
    scope = [arg for sid in source_ids for arg in ("-s", sid)]
    run("generate", "report", "--format", "custom", "--prompt-file", str(prompt_file), "-n", notebook_id,
        *scope, "--language", language, "--wait", "--timeout", "1200", timeout=1500)
    run("download", "report", str(dest), "-n", notebook_id, "--latest", "--force")
