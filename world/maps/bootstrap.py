"""Idempotent grid and wilderness bootstrap: spawn the sample city, bridge it to
Limbo, and provision the wilderness layer and one grid-side gate exit per
registered gate (map-wilderness, wilderness-anchor-footprint)."""

from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.search import search_object

from world.observability import log_warn
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom, Room
from world.lore.wilderness_entry import OPPOSITE_DIRECTION, WILDERNESS_ENTRY_REGISTRY
from world.maps.altoria_capital import XYMAP_DATA_LIST
from world.maps.instance import register_instance_reclamation
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)
from world.maps.wilderness_provider import (
    LONG_DIRECTIONS,
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
            "bootstrap_service_exterior_missing",
            context={
                "guild_hall_exterior": GUILD_HALL_EXTERIOR_XYZ,
                "general_store_exterior": GENERAL_STORE_EXTERIOR_XYZ,
                "action": "skip_service_interiors",
            },
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
                "bootstrap_limbo_room_missing",
                context={"room_key": LIMBO_KEY, "action": "skip_starting_room_sync"},
            )
            return
        room = legacy[0]
        room.key = LIMBO_KEY
    else:
        room = limbo[0]
        if len(limbo) > 1:
            log_warn(
                "bootstrap_limbo_duplicate_rooms",
                context={
                    "room_key": LIMBO_KEY,
                    "room_count": len(limbo),
                    "chosen_dbref": room.id,
                },
            )
        if legacy:
            log_warn(
                "bootstrap_limbo_legacy_room_coexists",
                context={
                    "legacy_room_key": LIMBO_LEGACY_KEY,
                    "canonical_room_key": LIMBO_KEY,
                    "action": "leave_legacy_room_in_place",
                },
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
        log_warn(
            "bootstrap_grid_limbo_room_missing",
            context={"room_key": LIMBO_KEY, "action": "skip_bridging_exits"},
        )
        return
    limbo = limbo[0]

    south_gate = grid.get_room(SOUTH_GATE_XYZ).first()
    if south_gate is None:
        log_warn(
            "bootstrap_grid_south_gate_missing",
            context={"xyz": SOUTH_GATE_XYZ, "action": "skip_bridging_exits"},
        )
        return

    _ensure_exit(limbo, south_gate, **EXIT_TO_CITY)
    _ensure_exit(south_gate, limbo, **EXIT_TO_LIMBO)


# Wilderness-side gate exits all share this key on DIFFERENT rooms; gateway
# resolution matches room + direction, never key aliases, and grid-side
# resolution reads db.anchor_key/db.gate_direction off the exit object.
GATE_EXIT_KEY = "荒野"


def sync_wilderness() -> None:
    """Provision the wilderness map and one grid-side gate per registered gate.

    ``create_wilderness()`` is itself a no-op if a ``WildernessScript`` keyed
    ``WILDERNESS_NAME`` already exists, so no extra guard is needed there. For
    every gate of every ``WILDERNESS_ENTRY_REGISTRY`` entry whose destination
    ``GridRoom`` exists, exactly one ``WildernessGateExit`` is ensured on that
    room with ``db.anchor_key`` and ``db.gate_direction`` set -- the exit is
    unusable (fails closed) without them, so they are part of provisioning,
    not decoration. A gate whose destination room is missing logs a warning
    and is skipped; other gates still provision.

    On every call we also re-run ``at_prepare_room()`` for each room already
    registered in the script's ``db.rooms``. This restores the deterministic
    ``ndb.active_desc``/``scene_archetype`` after a server restart, when the
    contrib's own ``at_server_start()`` restores only the non-persistent
    ``wildernessscript``/``active_coordinates`` links and the pickled
    ``mapprovider`` is no longer re-invoked (``create_wilderness`` no-ops) --
    and with them any gate-face exit locks the provider hook owns on active
    approach cells. Grid-side gate-exit provisioning is independent of that
    refresh pass.
    """

    create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())

    script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
    for coordinates, room in list(script.db.rooms.items()):
        script.mapprovider.at_prepare_room(coordinates, None, room)

    for entry in WILDERNESS_ENTRY_REGISTRY.values():
        for gate in entry.gates:
            _provision_gate_exit(entry.anchor_key, gate)


def _provision_gate_exit(anchor_key: str, gate) -> None:
    """Ensure the one gate exit for ``(anchor_key, gate)`` on its destination room."""
    gate_room = GridRoom.objects.filter_xyz((*gate.grid_xy, gate.z_map_key)).first()
    if gate_room is None:
        log_warn(
            "bootstrap_gate_destination_room_missing",
            context={
                "xyz": (*gate.grid_xy, gate.z_map_key),
                "gate_direction": gate.return_direction,
                "anchor_key": anchor_key,
                "action": "skip_gate_exit",
            },
        )
        return

    gate_exits = [
        exit_obj for exit_obj in gate_room.exits if isinstance(exit_obj, WildernessGateExit)
    ]
    if len(gate_exits) > 1:
        # Multiple WildernessGateExit rows on one room are ambiguous; never
        # guess which one to heal.
        log_warn(
            "bootstrap_gate_ambiguous_exits",
            context={
                "room_key": gate_room.key,
                "gate_direction": gate.return_direction,
                "action": "leave_exits_in_place",
            },
        )
        return
    if gate_exits:
        # Idempotent heal: the room's single WildernessGateExit IS this
        # room's gate slot (validated registries never put two gates on one
        # room), so its attributes converge on the authored pair in place --
        # a wrong db.anchor_key/db.gate_direction is corrected with no second
        # exit spawned.
        gate_exits[0].db.anchor_key = anchor_key
        gate_exits[0].db.gate_direction = gate.return_direction
        return

    if any(exit_obj.key == GATE_EXIT_KEY for exit_obj in gate_room.exits):
        # A non-project exit already occupies the gate key; do not create a
        # second ambiguous exit or claim provisioning succeeded.
        log_warn(
            "bootstrap_gate_key_occupied_by_other_exit",
            context={
                "exit_key": GATE_EXIT_KEY,
                "room_key": gate_room.key,
                "action": "leave_exit_in_place",
            },
        )
        return

    # Outward direction from the city is the gate's face -- opposite of the
    # wilderness-side return_direction: leaving 北門 toward the wild is north.
    face = OPPOSITE_DIRECTION[gate.return_direction]
    gate_exit = create_object(
        WildernessGateExit,
        key=GATE_EXIT_KEY,
        aliases=["wilderness", LONG_DIRECTIONS[face], face],
        location=gate_room,
        destination=gate_room,
    )
    gate_exit.db.anchor_key = anchor_key
    gate_exit.db.gate_direction = gate.return_direction