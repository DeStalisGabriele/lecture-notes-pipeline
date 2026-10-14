"""Run the notebooklm-py CLI with Windows' default asyncio loop.

The CLI switches Windows to WindowsSelectorEventLoopPolicy (a workaround for an IOCP hang in
some sandboxes). With that loop, uploading a large file dies with
"AssertionError: Data should not be empty" in _SelectorSocketTransport._write_send, and the
source stays in "preparing" forever. Lecture recordings are 80-130 MB, so every upload failed.
Ignoring the policy change keeps the Proactor loop, and the same uploads go through.
"""
import asyncio
import sys

asyncio.set_event_loop_policy = lambda *args, **kwargs: None

from notebooklm.notebooklm_cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
