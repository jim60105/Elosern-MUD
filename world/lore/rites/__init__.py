"""Process-wide holder of the validated landmark rite snapshot.

The rite document is loaded once and installed by the process that needs it; a
read-only consumer calls :func:`current` and never triggers a load. Tests supply
a synthetic snapshot through :func:`installed`, the one scoped seam, so no
snapshot leaks between tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from world.lore.rites.shape import RiteSnapshot

__all__ = [
    "CONTENT_PATH",
    "RitesNotLoaded",
    "current",
    "install",
    "installed",
    "uninstall",
]

#: The shipped rite document (authored by ``landmark-rite-content``).
CONTENT_PATH = Path(__file__).resolve().parent / "content" / "landmark_rites.yaml"


class RitesNotLoaded(RuntimeError):
    """A consumer read the rite domain before any snapshot was installed."""


_INSTALLED: RiteSnapshot | None = None


def current() -> RiteSnapshot:
    """The installed rite snapshot.

    Raises :class:`RitesNotLoaded` instead of loading implicitly: nothing here
    reads the document, so a process that never installed a snapshot fails
    loudly rather than inventing content.
    """

    snapshot = _INSTALLED
    if snapshot is None:
        raise RitesNotLoaded(
            "landmark rites are not loaded; install a snapshot before reading rite content"
        )
    return snapshot


def install(snapshot: RiteSnapshot) -> RiteSnapshot:
    """Bind one validated snapshot as this process's rite world."""

    global _INSTALLED
    if not isinstance(snapshot, RiteSnapshot):
        raise TypeError("install() requires a RiteSnapshot")
    _INSTALLED = snapshot
    return snapshot


def uninstall() -> None:
    """Forget the installed snapshot (a later :func:`current` raises again)."""

    global _INSTALLED
    _INSTALLED = None


@contextmanager
def installed(snapshot: RiteSnapshot) -> Iterator[RiteSnapshot]:
    """Install ``snapshot`` for the scope and restore the previous value on exit."""

    previous = _INSTALLED
    install(snapshot)
    try:
        yield snapshot
    finally:
        if previous is None:
            uninstall()
        else:
            install(previous)