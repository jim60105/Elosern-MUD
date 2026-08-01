"""Idempotent grid and wilderness bootstrap: spawn the sample city, bridge it to
Limbo, and provision the wilderness layer and its one gate (map-wilderness)."""

from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.logger import log_warn
from evennia.utils.search import search_object

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom
from world.maps.altoria_capital import XYMAP_DATA_LIST
from world.maps.instance import register_instance_reclamation
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")
NORTH_GATE_XYZ = (2, 4, "capital_altoria")

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

    register_instance_reclamation()

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


GATE_EXIT = {
    "key": "荒野",
    "aliases": ["wilderness", "north", "n"],
    "anchor_key": "capital_altoria",
}


def sync_wilderness() -> None:
    """Provision the wilderness map and the one grid-side gate idempotently.

    ``create_wilderness()`` is itself a no-op if a ``WildernessScript`` keyed
    ``WILDERNESS_NAME`` already exists, so no extra guard is needed there. The
    gate exit is only created when the ``capital_altoria`` North Gate room
    exists; its ``db.anchor_key`` is set at creation time because
    ``WildernessGateExit.at_traverse`` reads it on first use -- a gate created
    without it would ``KeyError`` (design.md D-7).

    On every call we also re-run ``at_prepare_room()`` for each room already
    registered in the script's ``db.rooms``. This restores the deterministic
    ``ndb.active_desc``/``scene_archetype`` after a server restart, when the
    contrib's own ``at_server_start()`` restores only the non-persistent
    ``wildernessscript``/``active_coordinates`` links and the pickled
    ``mapprovider`` is no longer re-invoked (``create_wilderness`` no-ops).
    """

    create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())

    script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
    for coordinates, room in list(script.db.rooms.items()):
        script.mapprovider.at_prepare_room(coordinates, None, room)

    north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
    if north_gate is None:
        log_warn(
            f"sync_wilderness: North Gate room at {NORTH_GATE_XYZ} not found; "
            "skipping the gateway exit."
        )
        return

    gates = [exit_obj for exit_obj in north_gate.exits if isinstance(exit_obj, WildernessGateExit)]
    if gates:
        # Idempotent heal: the project's own gate exists; make sure it is
        # configured for this anchor and does not linger mis-keyed.
        for gate in gates:
            if gate.key == GATE_EXIT["key"]:
                gate.db.anchor_key = GATE_EXIT["anchor_key"]
        return

    if any(exit_obj.key == GATE_EXIT["key"] for exit_obj in north_gate.exits):
        # A non-project exit already occupies the gate key; do not create a
        # second ambiguous exit or claim provisioning succeeded.
        log_warn(
            f"sync_wilderness: an exit keyed {GATE_EXIT['key']!r} exists at the North Gate "
            "but is not a WildernessGateExit; leaving it in place."
        )
        return

    gate = create_object(
        WildernessGateExit,
        key=GATE_EXIT["key"],
        aliases=GATE_EXIT["aliases"],
        location=north_gate,
        destination=north_gate,
    )
    gate.db.anchor_key = GATE_EXIT["anchor_key"]