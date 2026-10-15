"""Local transcription with faster-whisper, used when NotebookLM refuses an audio source.

Optional dependency: `pip install -e ".[whisper]"`. On an NVIDIA GPU, large-v3 transcribes a
three-hour lecture in about 7 minutes; without one it falls back to large-v3-turbo on the CPU.
"""
from __future__ import annotations

import sys
from pathlib import Path


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def paragraphs(segments, seconds: float = 60) -> str:
    """Join Whisper segments into one paragraph per `seconds` of audio."""
    out, current, start = [], [], 0.0
    for s in segments:
        current.append(s.text.strip())
        if s.end - start > seconds:
            out.append(" ".join(current))
            current, start = [], s.end
    if current:
        out.append(" ".join(current))
    return "\n\n".join(out) + "\n"


def transcribe(audio: Path, dest: Path, model: str = "large-v3", language: str = "it") -> Path:
    from faster_whisper import WhisperModel

    def run(name: str, device: str, compute_type: str) -> str:
        segments, _ = WhisperModel(name, device=device, compute_type=compute_type).transcribe(
            str(audio), language=language, vad_filter=True,
            condition_on_previous_text=False)  # avoids the repeated-sentence loops of long lectures
        return paragraphs(segments)

    try:
        text = run(model, "cuda", "float16")
    except Exception as e:  # no GPU, or CUDA libraries missing
        print(f"[no GPU ({type(e).__name__}), transcribing on the CPU]", file=sys.stderr)
        text = run("large-v3-turbo", "cpu", "int8")
    dest.write_text(text, encoding="utf-8")
    return dest
