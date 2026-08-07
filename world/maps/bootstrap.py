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
from typeclasses.rooms import GridRoom, Room
from world.maps.altoria_capital import XYMAP_DATA_LIST
from world.maps.instance import register_instance_reclamation
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")
NORTH_GATE_XYZ = (2, 4, "capital_altoria")

# Permanent service interiors (guild-economy D-9). They are ordinary permanent
# rooms OUTSIDE the xyzgrid node count, linked bidirectionally to their
# documented exterior grid rooms, and are not coordinates on the grid.
GUILD_HALL_KEY = "altoria_guild_hall"
GENERAL_STORE_KEY = "altoria_general_store"
GUILD_HALL_EXTERIOR_XYZ = (3, 1, "capital_altoria")  # 冒險者公會外
GENERAL_STORE_EXTERIOR_XYZ = (1, 2, "capital_altoria")  # 市場街
GUILD_HALL_TAG = GUILD_HALL_KEY
GENERAL_STORE_TAG = GENERAL_STORE_KEY
GUILD_HALL_DESC = "The guild hall of 阿爾托利亞, with a grand board and a training ring (guild-economy D-9)."
GENERAL_STORE_DESC = "The general store of 阿爾托利亞, its shelves waiting for the next caravan (guild-economy D-9)."


def _find_exterior(xyz):
    return GridRoom.objects.filter_xyz(xyz=xyz).first()


def _ensure_doorway(location, destination, key, aliases):
    """Create ``key``/``aliases`` exit from ``location`` to ``destination`` if missing."""
    _ensure_exit(location, destination, key, aliases)


def _ensure_interior(key, tag, desc):
    """Create one tagged permanent interior room and return it."""
    from evennia.utils.search import search_object_by_tag

    rooms = search_object_by_tag(tag)
    if rooms:
        room = rooms[0]
    else:
        room = create_object(
            Room,
            key=key,
            tags=[tag],
            location=None,
        )
    room.db.desc = desc
    return room


def _ensure_interior_doorways(interior, exterior, interior_key, interior_aliases):
    """Create the four directed doorway exits between interior and exterior."""
    _ensure_doorway(exterior, interior, interior_key, interior_aliases)
    _ensure_doorway(interior, exterior, "外", ["out", "leave"])


def sync_service_interiors() -> None:
    """Create the two permanent guild-economy interiors idempotently.

    The grid street topology is unchanged: these rooms are not xyzgrid nodes.
    Each interior is tagged by stable key so repeated startup reuses the same
    room rather than duplicating it, and every authored description is updated
    in place on every sync.
    """
    guild_exterior = _find_exterior(GUILD_HALL_EXTERIOR_XYZ)
    store_exterior = _find_exterior(GENERAL_STORE_EXTERIOR_XYZ)
    if guild_exterior is None or store_exterior is None:
        log_warn(
            "sync_service_interiors: an exterior grid room is missing; "
            "skipping service interiors."
        )
        return

    guild_hall = _ensure_interior(
        "阿爾托利亞冒險者公會大廳",
        GUILD_HALL_TAG,
        GUILD_HALL_DESC,
    )
    general_store = _ensure_interior(
        "阿爾托利亞雜貨店",
        GENERAL_STORE_TAG,
        GENERAL_STORE_DESC,
    )

    _ensure_interior_doorways(
        guild_hall,
        guild_exterior,
        "冒險者公會大廳",
        ["guild hall", "hall"],
    )
    _ensure_interior_doorways(
        general_store,
        store_exterior,
        "雜貨店",
        ["general store", "store", "shop"],
    )

EXIT_TO_CITY = {
    "key": "南門",
    "aliases": ["王都", "城門"],
}
EXIT_TO_LIMBO = {
    "key": "離開王都",
    "aliases": ["回虛境"],
}


def sync_limbo() -> None:
    """Converge the starting room (Limbo) onto its zh-tw identity idempotently.

    Runs on every server start before ``sync_grid()`` (localize-limbo-zhtw
    D-2). Mirrors the in-place description rewrite of ``sync_service_
    interiors()``: the authored zh-tw key, alias, and description are
    re-affirmed on every call. A legacy English-keyed room (as created by
    Evennia's first-boot setup) is renamed in place so existing developer
    databases converge without a wipe. When both a canonical and a legacy room
    exist, the canonical room wins and the legacy room is left untouched with
    a warning -- never a silent arbitrary pick. A missing room degrades to a
    warning, never a raise.

    The canonical lookup is restricted to the ``Room`` typeclass by ``db_key``
    (never the alias-inclusive ``search_object``), so a non-room object that
    happens to share the key or the ``limbo`` alias can never be rewritten or
    bridged.
    """

    limbo = Room.objects.filter(db_key=LIMBO_KEY)
    # Legacy lookup matches the db_key exactly: Evennia's alias-inclusive
    # search would also match the canonical room through its ``limbo`` alias.
    legacy = Room.objects.filter(db_key=LIMBO_LEGACY_KEY)
    if not limbo:
        if not legacy:
            log_warn(
                f"sync_limbo: no starting room keyed {LIMBO_KEY!r} found; "
                "skipping the starting-room sync."
            )
            return
        room = legacy[0]
        room.key = LIMBO_KEY
    else:
        room = limbo[0]
        if len(limbo) > 1:
            log_warn(
                f"sync_limbo: {len(limbo)} rooms keyed {LIMBO_KEY!r} exist; "
                f"using dbref #{room.id} as the starting room."
            )
        if legacy:
            log_warn(
                f"sync_limbo: a legacy room keyed {LIMBO_LEGACY_KEY!r} coexists with the "
                f"canonical {LIMBO_KEY!r} room; leaving the legacy room in place."
            )
    room.aliases.add(LIMBO_ALIAS)
    room.db.desc = LIMBO_DESC
    room.save()


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
    """Create or reconcile ``key``/``aliases`` exit from ``location`` to ``destination``.

    When the exit already exists, its key and aliases are rewritten in place
    to the authored values on every call, so a pre-existing exit converges on
    the zh-tw bridge surface without being rebuilt (localize-limbo-zhtw D-3).
    """

    exit_obj = _existing_exit(location, destination)
    if exit_obj is None:
        create_object(
            Exit,
            key=key,
            aliases=aliases,
            location=location,
            destination=destination,
        )
        return
    if exit_obj.key != key or set(exit_obj.aliases.all()) != set(aliases):
        exit_obj.key = key
        exit_obj.aliases.clear()
        exit_obj.aliases.add(*aliases)
        exit_obj.save()


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

    limbo = Room.objects.filter(db_key=LIMBO_KEY)
    if not limbo:
        log_warn(f"sync_grid: no room keyed {LIMBO_KEY!r} found; skipping the bridging exits.")
        return
    limbo = limbo[0]

    south_gate = grid.get_room(SOUTH_GATE_XYZ).first()
    if south_gate is None:
        log_warn(
            f"sync_grid: South Gate room at {SOUTH_GATE_XYZ} not found; "
            "skipping the bridging exits."
        )
        return

    _ensure_exit(limbo, south_gate, **EXIT_TO_CITY)
    _ensure_exit(south_gate, limbo, **EXIT_TO_LIMBO)


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