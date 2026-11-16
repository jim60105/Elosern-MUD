"""Start-room stub for activation tests (subrace-start-settlements D6).

Activation resolves its subrace's start room before any write. Tests that
activate a character without testing placement patch that resolution to one
plain synthetic room, so they need no materialized settlement.
"""

from __future__ import annotations

import unittest.mock
from typing import Any

STUB_START_ROOM_KEY = "t_start_room"


def _stub_resolve(subrace_key: str | None) -> Any:
    """Return the stub start room, creating it on first use."""

    from evennia.objects.models import ObjectDB
    from evennia.utils.create import create_object

    from typeclasses.rooms import Room

    for candidate in ObjectDB.objects.filter(db_key=STUB_START_ROOM_KEY):
        if isinstance(candidate, Room):
            return candidate
    return create_object(Room, key=STUB_START_ROOM_KEY, nohome=True)


def stub_start_room():
    """Patch start-room resolution to a plain synthetic room.

    For activation tests that do not test placement. Usable as a class or
    method decorator or with ``self.enterContext(stub_start_room())``. The
    room is found by key or created on first use inside the running test, so
    a per-test database rollback never leaves a stale object behind.
    """
    return unittest.mock.patch(
        "world.rules.start_location.resolve_start_room", new=_stub_resolve
    )


__all__ = ["STUB_START_ROOM_KEY", "stub_start_room"]
