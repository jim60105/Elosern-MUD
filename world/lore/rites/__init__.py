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
    "load_published",
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


def load_published(
    path: Path | None = None, *, district_keys: frozenset[str] | None = None
) -> RiteSnapshot:
    """Load the shipped document against the published districts and install it.

    ``path`` defaults to :data:`CONTENT_PATH`; ``district_keys`` defaults to the
    districts of the published map world, which must already be installed when
    ``district_keys`` is omitted; an uninstalled world raises
    :class:`world.lore.map_districts.DistrictNotLoaded`, not
    :class:`world.lore.rites.loader.RiteContentError`. Every failure
    propagates: a rejected or unreadable document installs nothing and a
    previously installed snapshot stays current. Each call re-reads the
    document and replaces the installed snapshot; startup calls it once per
    process, after the map world is adopted, so a snapshot installed against an
    earlier district world becomes stale rather than invalid.
    """

    from world.lore.rites.loader import load_rites

    source = CONTENT_PATH if path is None else Path(path)
    if district_keys is None:
        from world.lore.map_districts import current as published_districts

        district_keys = frozenset(published_districts().districts)
    return install(load_rites(source, district_keys=district_keys))


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