"""Incremental synchronization journey seed (change ``webclient-sync-functional-smoke``).

Installed only when ``ELOSERN_BROWSER_INCREMENTAL_SYNC=1``. The managed server's
own bootstrap already builds the grid map; this fixture moves the seeded
character onto the first registered city-gate room, where the committed
``exploration`` and ``local_map`` panels expose the four compass exits the
graphical same-area move needs, and brings the already-seeded monsters along so
the same room offers a real combat engagement.

Nothing here invents state a production owner would not: the rooms come from
the map owner's own sync, the relocation and the arrival knowledge ride the
same seams the map features use, and the monsters keep the traits the base seed
gave them.
"""

from __future__ import annotations

import os


def _incremental_sync_fixture(character) -> None:
    """Relocate the seeded character (and its monsters) onto the gate room."""
    if os.environ.get("ELOSERN_BROWSER_INCREMENTAL_SYNC") != "1":
        return
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
    from typeclasses.monsters import Monster

    from web.tests.browser.incremental_sync_fixture import first_gate_xyz
    from world.maps.bootstrap import sync_grid
    from world.rules.map_knowledge import record_arrival

    sync_grid()
    origin = character.location
    x, y, z_map = first_gate_xyz()
    gate = XYZRoom.objects.filter_xyz(xyz=(x, y, z_map)).first()
    if gate is None:
        raise AssertionError("the map owner did not build the fixture gate room")
    if origin is not None:
        # The base seed's living monsters travel with the character so the
        # gate room offers the same engagement the start room did.
        for monster in Monster.objects.filter(db_location=origin):
            monster.location = gate
            monster.save()
    character.location = gate
    record_arrival(character)
    print(f"seeded incremental-sync fixture: gate={gate.pk} monsters={Monster.objects.filter(db_location=gate).count()}")
