"""Exclusive lock around the static Storybook showcase build.

The Evennia test runner is parallel (``--parallel 4`` in CI): multiple
worker processes share one checkout, and more than one worker may need the
``.storybook-out`` build — the B1 evidence class rebuilds it unconditionally
as its gate evidence, while the B2 action-dock class builds it on demand.
Two concurrent ``storybook build -o`` runs into the same output directory
can interleave file writes (a partially written ``index.json`` is not
parseable), so every showcase build — and every read of build outputs —
runs under one process-wide exclusive ``fcntl`` lock.
"""

from __future__ import annotations

import contextlib
import fcntl
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = REPO_ROOT / ".storybook-out" / ".build.lock"


@contextlib.contextmanager
def showcase_build_lock() -> Iterator[None]:
    """Hold the exclusive showcase build lock for the ``with`` block."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
