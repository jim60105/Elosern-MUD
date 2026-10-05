"""No-follow file-open primitives shared by every external-content walker.

Two external directories are read by the game — the operator-supplied bulk
seed folder (``world/art/gallery_seed.py``, ``ART_SEED_ROOT``) and the
operator-prepared official-artwork folder (``world/art/official.py``,
``ART_OFFICIAL_ROOT``) — and both are mounted directories the game does not
own. Classification alone is never the boundary there: a check-then-pathname-
open is swappable in between, so traversal descends from one ``O_NOFOLLOW``
directory fd and every content file is opened RELATIVE to its verified parent
fd with ``O_NOFOLLOW`` and re-verified by ``fstat`` AFTER the open.

That discipline is defined exactly once, here, so the two walkers cannot drift
into two definitions of "a real, confined, bounded file". The primitives take
their size cap from the caller (each root has its own documented bound) and
stay stdlib-only: no Django settings, no Evennia, no logging, and no
``world.art`` import, so any walker may depend on them without closing an
import cycle or picking up a heavier surface.
"""

import os
from stat import S_ISREG


class RejectedFile(Exception):
    """An opened file failed post-open verification (the internal refusal signal).

    Raised (never logged) by :func:`open_file_bytes`: not a regular file,
    hard-linked, or past the caller's size cap. Callers map it to their own
    bounded diagnostic.
    """


def open_dir_fd(name: str, *, dir_fd: int | None = None) -> int:
    """Open a directory no-follow (``O_NOFOLLOW``), raising ``OSError`` on refusal.

    With ``dir_fd`` the name is resolved relative to an already-verified
    parent directory fd, so no intermediate component of a walk is ever
    re-resolved through a swappable pathname.
    """
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)


def open_nofollow(name: str, *, dir_fd: int, flags: int) -> int:
    """``openat``-style open of the final component with ``O_NOFOLLOW``."""
    return os.open(name, flags | os.O_NOFOLLOW, dir_fd=dir_fd)


def open_file_bytes(name: str, *, dir_fd: int, max_bytes: int) -> bytes:
    """Read a no-follow regular single-link file relative to a verified fd.

    Raises ``FileNotFoundError`` when the name is absent, ``OSError`` when it
    cannot be opened (a planted symlink answers ``ELOOP`` at open), and
    :class:`RejectedFile` when post-open verification fails: not a regular
    file, hard-linked (``st_nlink != 1``, so two names can never alias the
    bytes we classify), or past ``max_bytes`` (checked on the ``fstat`` size
    before reading, so a hostile giant is never buffered).
    """
    fd = open_nofollow(name, dir_fd=dir_fd, flags=os.O_RDONLY)
    try:
        stat_result = os.fstat(fd)
        if not S_ISREG(stat_result.st_mode) or stat_result.st_nlink != 1:
            raise RejectedFile(name)
        if stat_result.st_size > max_bytes:
            raise RejectedFile(name)
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1 << 20))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
    finally:
        os.close(fd)
    if len(payload) > max_bytes:
        raise RejectedFile(name)
    return payload
