"""Art publication gate: lets a world snapshot see a still art store.

Every step that changes a file under ``ART_STORE_ROOT`` while the server runs
(publishing a generated image together with its record transition, deleting
a superseded output, unlinking a removed gallery card) holds
:func:`publishing`. A world snapshot (``server.saves.snapshot``) holds
:func:`paused` across its database backup and art mirror, so no art file is
written or removed mid-snapshot and the saved database and saved art agree.

``paused`` also raises a flag that turns ``ArtDrainScript`` ticks and manual
drains into no-ops, which is how the snapshot pauses the drain: Evennia's
Script pause manipulates a Twisted ``LoopingCall`` and is not safe to call
from the Django request thread a snapshot runs on.

Lock order: the gate is always taken BEFORE ``queue_lock`` or
``gallery_lock``, never while holding either (gallery card unlinks run after
``gallery_lock`` is released; the worker's settle already holds the gate when
it reaches them, and the gate is reentrant), so a snapshot never blocks a
reactor-thread queue user and can never deadlock with one. Generation itself
(the long sd-webui wait) is outside the gate; only the short publication
step waits.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

_gate = threading.RLock()
_paused = threading.Event()


def is_paused() -> bool:
    """True while a snapshot holds the art store still."""
    return _paused.is_set()


@contextmanager
def publishing() -> Iterator[None]:
    """Hold the gate around one art-store file change."""
    with _gate:
        yield


@contextmanager
def publishing_within(timeout: float) -> Iterator[bool]:
    """Hold the gate if it frees within ``timeout`` seconds; yield whether it did.

    For reactor-thread deletions that must not freeze the game behind a long
    snapshot: a caller that gets ``False`` skips its unlink, leaving an
    unreferenced file that the startup orphan prune reclaims.
    """
    acquired = _gate.acquire(timeout=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            _gate.release()


@contextmanager
def paused() -> Iterator[None]:
    """Stop drains and wait out any in-flight publication; resume on exit."""
    _paused.set()
    try:
        with _gate:
            yield
    finally:
        _paused.clear()
