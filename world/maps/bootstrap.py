"""Idempotent grid bootstrap: spawn the sample city and bridge it to Limbo."""

from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.utils.create import create_object
from evennia.utils.logger import log_warn
from evennia.utils.search import search_object

from typeclasses.exits import Exit
from world.maps.altoria_capital import XYMAP_DATA_LIST

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")

EXIT_TO_CITY = {
    "key": "南門",
    "aliases": ["south gate", "altoria"],
}
EXIT_TO_LIMBO = {
    "key": "離開王都",
    "aliases": ["leave", "limbo"],
}


def _existing_exit(location, destination):
    """Return the exit at ``location`` leading to ``destination``, if any.

    Matches by location and destination, not by key, to tolerate a future
    rename of the bridging exits.
    """

    for exit_obj in location.exits:
        if exit_obj.destination == destination:
            return exit_obj
    return None


def _ensure_exit(location, destination, key, aliases):
    """Create ``key``/``aliases`` exit from ``location`` to ``destination`` if missing."""

    if _existing_exit(location, destination):
        return
    create_object(
        Exit,
        key=key,
        aliases=aliases,
        location=location,
        destination=destination,
    )


def sync_grid() -> None:
    """Spawn every declared grid map and bridge the sample city to Limbo.

    Mirrors ``world.lore.sync.sync_all()`` in being idempotent and called on
    every server start, but instantiates real walkable rooms/exits (via the
    xyzgrid contrib's coordinate-existence check) instead of ``LoreRecord``
    Scripts. ``add_maps()`` must be followed by ``reload()`` and then
    ``spawn()`` in the same process -- without ``reload()`` the first boot
    would spawn nothing (design.md D-5).
    """

    grid = get_xyzgrid()
    grid.add_maps(*XYMAP_DATA_LIST)
    grid.reload()
    grid.spawn()

    limbo = search_object("Limbo", exact=True)
    if not limbo:
        log_warn("sync_grid: no room keyed 'Limbo' found; skipping the bridging exits.")
        return

    south_gate = grid.get_room(SOUTH_GATE_XYZ).first()
    if south_gate is None:
        log_warn(
            f"sync_grid: South Gate room at {SOUTH_GATE_XYZ} not found; "
            "skipping the bridging exits."
        )
        return

    _ensure_exit(limbo[0], south_gate, **EXIT_TO_CITY)
    _ensure_exit(south_gate, limbo[0], **EXIT_TO_LIMBO)