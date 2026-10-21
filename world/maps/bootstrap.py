"""Idempotent grid and wilderness bootstrap: converge the sparse settlements,
bridge them to Limbo with one-way registry gates, and provision the wilderness
layer and one grid-side gate exit per registered gate (map-wilderness,
wilderness-anchor-footprint, limbo-one-way-gates).

``sync_grid()`` synchronizes the authored sparse graphs. Stable node identities
are the matching authority: a coordinate change moves the existing room, its
occupants and every reference in place instead of deleting and recreating it.
The ASCII map data is only registered for the contrib's display/builder
surfaces; it is never the spawn input."""

import hashlib
from dataclasses import dataclass, field

from django.db import transaction
from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid
from evennia.contrib.grid.xyzgrid.xyzroom import (
    MAP_X_TAG_CATEGORY,
    MAP_XDEST_TAG_CATEGORY,
    MAP_Y_TAG_CATEGORY,
    MAP_YDEST_TAG_CATEGORY,
    MAP_Z_TAG_CATEGORY,
    MAP_ZDEST_TAG_CATEGORY,
    XYZExit,
)
from evennia.prototypes import spawner as prototype_spawner
from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.utils import class_from_module

from world.observability import log_info, log_warn
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom, Room
from world.lore.wilderness_entry import OPPOSITE_DIRECTION, WILDERNESS_ENTRY_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.sparse_graph import SparseGraphError, SparseSettlementGraph, exit_spawn_names
from world.maps.city_gates import CITY_GATE_REGISTRY
from world.maps.instance import register_instance_reclamation
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)
from world.maps.room_art import (
    GRID_NODE_SCENE_ARCHETYPES,
    PLACE_SCENE_ARCHETYPES,
    grid_scene_identity,
    place_scene_identity,
)
from world.maps.wilderness_provider import (
    LONG_DIRECTIONS,
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)

# No gate coordinates live here (limbo-one-way-gates D1: the registries are the
# sole authored source): every consumer resolves a city gate through
# CITY_GATE_REGISTRY and a wilderness gate through WILDERNESS_ENTRY_REGISTRY,
# so bootstrap owns no gate surface of its own.

# The hard-gate starting-room typeclass (limbo-one-way-gates D4). Referenced
# by module path so bootstrap never imports typeclasses.rooms' subclasses.
LIMBO_ROOM_TYPECLASS = "typeclasses.rooms.LimboRoom"

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


def _apply_room_art(room, *, scene_archetype, room_art_key, scene_identity):
    """Write one room's authored scene facts (idempotent, map-owned).

    Re-assigned unconditionally on every sync so a boot converges a room whose
    stored metadata drifted (an older boot, a manual edit) onto the authored
    declaration. The values come only from the authored tables in
    ``world.maps.room_art``; nothing here infers a key from a name or id.
    """
    for field_name, value in (
        ("scene_archetype", scene_archetype),
        ("room_art_key", room_art_key),
        ("scene_identity", scene_identity),
    ):
        if getattr(room, field_name) != value:
            setattr(room, field_name, value)


def _ensure_interior_doorways(interior, exterior, interior_key, interior_aliases):
    """Create the four directed doorway exits between interior and exterior."""
    _ensure_doorway(exterior, interior, interior_key, interior_aliases)
    _ensure_doorway(interior, exterior, "外", ["out", "leave"])


def sync_service_interiors() -> None:
    """Create every registered place's permanent interior idempotently.

    The grid street topology is unchanged: these rooms are not xyzgrid nodes.
    Places are grouped by settlement so each exterior resolves in its own
    settlement's coordinate space (the z derives from the settlement record,
    never a code-side constant). Each interior is tagged by its place key so
    repeated startup reuses the same room rather than duplicating it, and
    every authored description is updated in place on every sync. A place
    whose exterior cannot be resolved is warned (naming the row) and skipped;
    the remaining places still synchronize.
    """
    from collections import defaultdict

    by_settlement: dict[str, list] = defaultdict(list)
    for place in PLACE_REGISTRY.values():
        by_settlement[place.settlement_key].append(place)

    for settlement_key, places in by_settlement.items():
        zcoord = SETTLEMENT_REGISTRY[settlement_key].zcoord
        for place in places:
            exterior_xyz = (*place.exterior_xy, zcoord)
            exterior = _find_exterior(exterior_xyz)
            if exterior is None:
                log_warn(
                    "bootstrap_service_exterior_missing",
                    context={
                        "place": place.key,
                        "exterior_xyz": exterior_xyz,
                        "action": "skip_place",
                    },
                )
                continue
            interior = _ensure_interior(
                place.room_name_zh,
                place.key,
                place.room_desc_zh,
            )
            scene_archetype = PLACE_SCENE_ARCHETYPES.get(place.key)
            if scene_archetype is None:
                # The import-time contract guarantees every authored place is
                # declared; a runtime-patched registry (a test seam) that adds
                # an undeclared row is reported rather than silently left
                # without scene art.
                log_warn(
                    "bootstrap_interior_scene_missing",
                    context={"place": place.key, "action": "skip_scene_metadata"},
                )
            else:
                _apply_room_art(
                    interior,
                    scene_archetype=scene_archetype,
                    room_art_key=place.key,
                    scene_identity=place_scene_identity(place.key),
                )
            _ensure_interior_doorways(
                interior,
                exterior,
                place.doorway_key_zh,
                list(place.doorway_aliases),
            )


def resolve_residence_route(home_key: str, guild_key: str) -> dict:
    """Resolve materialized place/grid identities, rejecting disconnected routes."""
    from evennia.utils.search import search_object_by_tag

    home_place = PLACE_REGISTRY[home_key]
    guild_place = PLACE_REGISTRY[guild_key]
    if (
        home_place.settlement_key != guild_place.settlement_key
        or home_place.exterior_xy != guild_place.exterior_xy
    ):
        raise ValueError(f"residence {home_key!r} and guild {guild_key!r} need one frontage")
    rooms = {}
    for role, key in (("home", home_key), ("guild", guild_key)):
        matches = [obj for obj in search_object_by_tag(key) if isinstance(obj, Room)]
        if len(matches) != 1:
            raise ValueError(f"place {key!r} resolves to {len(matches)} rooms")
        rooms[role] = matches[0]
    zcoord = SETTLEMENT_REGISTRY[home_place.settlement_key].zcoord
    frontage = list(GridRoom.objects.filter_xyz(xyz=(*home_place.exterior_xy, zcoord)))
    if len(frontage) != 1:
        raise ValueError(f"residence {home_key!r} frontage resolves to {len(frontage)} rooms")
    rooms["frontage"] = frontage[0]
    for source, target in (("home", "frontage"), ("frontage", "guild"),
                           ("guild", "frontage"), ("frontage", "home")):
        if not any(exit_obj.destination == rooms[target] for exit_obj in rooms[source].exits):
            raise ValueError(f"residence {home_key!r} route lacks {source}->{target} Exit")
    return rooms


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

    The call also declaratively converges the room's typeclass onto the
    hard-gate ``LimboRoom`` (limbo-one-way-gates D4): an unconverged room is
    swapped in place without clearing attributes, an already-converged room
    is left as-is, so the convergence is idempotent and never a migration.
    """

    limbo = find_starting_rooms(LIMBO_KEY)
    # Legacy lookup matches the db_key exactly: Evennia's alias-inclusive
    # search would also match the canonical room through its ``limbo`` alias.
    legacy = find_starting_rooms(LIMBO_LEGACY_KEY)
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
    # Layer-2 one-way gate (limbo-one-way-gates D4): declaratively converge
    # the typeclass in place. clean_attributes=False keeps the authored
    # identity; no_default=True suppresses creation-hook churn; the guard
    # makes every run after the first a no-op.
    if room.typeclass_path != LIMBO_ROOM_TYPECLASS:
        room.swap_typeclass(LIMBO_ROOM_TYPECLASS, clean_attributes=False, no_default=True)


def find_starting_rooms(db_key: str) -> list:
    """Return the ``Room``-family objects whose db key is exactly ``db_key``.

    The lookup runs at the unscoped ``ObjectDB`` level because Evennia's
    ``TypeclassManager`` filters pin to the manager's exact typeclass path,
    which would blind a plain ``Room`` query to the starting room once
    ``sync_limbo()`` has converged it onto ``LimboRoom`` (which subclasses
    ``Room``). Evennia's manager converts each row to its own stored
    typeclass, so the ``isinstance`` gate below still rejects any non-room
    object that happens to share the key.
    """

    return [
        obj
        for obj in ObjectDB.objects.filter(db_key=db_key)
        if isinstance(obj, Room)
    ]


def _ensure_exit(location, destination, key, aliases):
    """Create or reconcile exactly one ``key``/``aliases`` exit toward ``destination``.

    When one exit already exists, its key and aliases are rewritten in place
    to the authored values on every call, so a pre-existing exit converges on
    the zh-tw bridge surface without being rebuilt (localize-limbo-zhtw D-3).
    Duplicate pre-existing exits toward the same destination are declaratively
    pruned (the lowest dbid is the stable keeper), so "exactly one" forward
    exit per registry row holds regardless of database history
    (limbo-one-way-gates D3's convergence discipline).
    """

    existing = sorted(
        (exit_obj for exit_obj in location.exits if exit_obj.destination == destination),
        key=lambda exit_obj: exit_obj.id,
    )
    if not existing:
        create_object(
            Exit,
            key=key,
            aliases=aliases,
            location=location,
            destination=destination,
        )
        return
    keep = existing[0]
    for duplicate in existing[1:]:
        log_info(
            "bootstrap_grid_exit_pruned",
            context={
                "exit_key": duplicate.key,
                "exit_dbref": duplicate.dbref,
                "source_room_key": location.key,
                "action": "collapse_duplicate_gate_exit",
            },
        )
        duplicate.delete()
    if keep.key != key or set(keep.aliases.all()) != set(aliases):
        keep.key = key
        keep.aliases.clear()
        # TagHandler.add takes ONE key or an iterable (``add(a, b)`` would
        # read ``b`` as a category); pass the authored list as one iterable.
        keep.aliases.add(list(aliases))
        keep.save()


#: Tag categories owned by the sparse synchronizer. They identify the authored
#: object independently of its coordinate, so a moved node keeps its room.
NODE_IDENTITY_TAG_CATEGORY = "sparse_node_identity"
ROAD_IDENTITY_TAG_CATEGORY = "sparse_road_identity"

#: Attribute carrying the hash of the applied authored prototype. A repeat
#: synchronization whose authored data is unchanged performs no prototype write
#: (the second-run no-op contract), while an authored edit still converges.
PROTOTYPE_FINGERPRINT_ATTR = "sparse_prototype_fingerprint"


@dataclass(frozen=True, slots=True)
class SyncReport:
    """How many managed rooms/exits one synchronization changed."""

    created: int = 0
    updated: int = 0
    deleted: int = 0

    def __add__(self, other: "SyncReport") -> "SyncReport":
        return SyncReport(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            deleted=self.deleted + other.deleted,
        )


@dataclass
class _NodeBinding:
    node: object
    room: object | None


@dataclass
class _RoadBinding:
    edge: object
    exit_obj: object | None = None


@dataclass
class _GraphPlan:
    graph: SparseSettlementGraph
    nodes: list[_NodeBinding] = field(default_factory=list)
    roads: list[_RoadBinding] = field(default_factory=list)
    stale_rooms: list = field(default_factory=list)
    stale_exits: list = field(default_factory=list)
    # old coordinate -> new coordinate for every node this plan relocates.
    remapped_coordinates: dict[tuple[int, int], tuple[int, int]] = field(
        default_factory=dict
    )


def _node_tag(graph: SparseSettlementGraph, node) -> str:
    return f"{graph.map_id}:{node.node_id}"


def _road_tag(graph: SparseSettlementGraph, edge) -> str:
    return f"{graph.map_id}:{edge.road.road_id}"


def _fingerprint(prototype: dict) -> str:
    payload = repr(sorted((str(key), repr(value)) for key, value in prototype.items()))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _flatten(prototype, prototype_key: str, default_typeclass: str) -> dict:
    prepared = dict(prototype)
    prepared["prototype_key"] = prototype_key
    flattened = prototype_spawner.flatten_prototype(prepared, no_db=True)
    if not prototype.get("typeclass") and not prototype.get("prototype_parent"):
        # ``flatten_prototype`` supplies the global base object typeclass when
        # the authored prototype names none. A sparse node/road still creates
        # a coordinate-aware object, so pin the owning default instead.
        flattened["typeclass"] = default_typeclass
    return flattened


def _object_identity_tag(obj, category: str) -> str | None:
    return obj.tags.get(category=category, return_list=False)


def _set_coordinate_tags(obj, source_xyz, destination_xyz=None) -> bool:
    """Converge XYZ tags in place and drop cached coordinate projections."""

    updates = [
        (MAP_X_TAG_CATEGORY, source_xyz[0]),
        (MAP_Y_TAG_CATEGORY, source_xyz[1]),
        (MAP_Z_TAG_CATEGORY, source_xyz[2]),
    ]
    if destination_xyz is not None:
        updates.extend(
            [
                (MAP_XDEST_TAG_CATEGORY, destination_xyz[0]),
                (MAP_YDEST_TAG_CATEGORY, destination_xyz[1]),
                (MAP_ZDEST_TAG_CATEGORY, destination_xyz[2]),
            ]
        )
    changed = False
    for category, value in updates:
        current = obj.tags.get(category=category, return_list=False)
        if current == str(value):
            continue
        if current is not None:
            obj.tags.remove(current, category=category)
        obj.tags.add(str(value), category=category)
        changed = True
    for cache in ("_xyz", "_xyz_destination", "_xymap"):
        if hasattr(obj, cache):
            delattr(obj, cache)
    return changed


def _apply_prototype(obj, prototype: dict) -> bool:
    """Apply an authored prototype only when it actually changed."""

    fingerprint = _fingerprint(prototype)
    if obj.attributes.get(PROTOTYPE_FINGERPRINT_ATTR) == fingerprint:
        return False
    prototype_spawner.batch_update_objects_with_prototype(
        prototype, objects=[obj], exact=False
    )
    obj.attributes.add(PROTOTYPE_FINGERPRINT_ATTR, fingerprint)
    return True


def _plan_settlement_graph(graph: SparseSettlementGraph) -> _GraphPlan:
    """Resolve room/exit bindings read-only, refusing conflicts before mutation."""

    plan = _GraphPlan(graph=graph)
    rooms = list(GridRoom.objects.filter_xyz(xyz=("*", "*", graph.map_id)))
    by_identity: dict[str, list] = {}
    unbound: list = []
    for room in rooms:
        identity = _object_identity_tag(room, NODE_IDENTITY_TAG_CATEGORY)
        if identity:
            by_identity.setdefault(identity, []).append(room)
        else:
            unbound.append(room)
    for identity, bound in by_identity.items():
        if len(bound) > 1:
            raise SparseGraphError(
                f"map {graph.map_id!r} has {len(bound)} rooms bound to identity {identity!r}"
            )

    claimed: set[int] = set()
    for node in graph.nodes.values():
        tag = _node_tag(graph, node)
        bound = by_identity.get(tag)
        room = bound[0] if bound else None
        if room is None:
            candidates = [candidate for candidate in unbound if candidate.xyz[:2] == node.coordinate]
            if len(candidates) > 1:
                raise SparseGraphError(
                    f"map {graph.map_id!r} cannot bind node {node.node_id!r}: "
                    f"{len(candidates)} unbound rooms occupy {node.coordinate}"
                )
            if candidates:
                room = candidates[0]
                unbound.remove(room)
        elif any(candidate.xyz[:2] == node.coordinate for candidate in unbound):
            # A moved identity may not silently land on and delete an
            # unbound legacy room; that is an ambiguous binding. Refuse.
            raise SparseGraphError(
                f"map {graph.map_id!r} cannot move node {node.node_id!r} to "
                f"{node.coordinate}: an unbound room already occupies it"
            )
        if room is not None:
            if int(room.id) in claimed:
                raise SparseGraphError(
                    f"map {graph.map_id!r} binds room #{room.id} to more than one node"
                )
            claimed.add(int(room.id))
            try:
                old_coordinate = (int(room.xyz[0]), int(room.xyz[1]))
            except (TypeError, ValueError):
                old_coordinate = None
            if old_coordinate is not None and old_coordinate != node.coordinate:
                plan.remapped_coordinates[old_coordinate] = node.coordinate
        plan.nodes.append(_NodeBinding(node=node, room=room))

    plan.stale_rooms = [
        room for room in rooms if int(room.id) not in claimed
    ]
    # A coordinate move never deletes-or-recreates an occupied or referenced
    # room. An unbound legacy room that would be pruned while something still
    # points at it is an ambiguous binding, refused before any write.
    for room in plan.stale_rooms:
        if _room_is_referenced(room):
            raise SparseGraphError(
                f"map {graph.map_id!r} cannot prune referenced unbound room "
                f"#{room.id} at {room.xyz}"
            )

    source_rooms = {
        binding.node.node_id: binding.room
        for binding in plan.nodes
        if binding.room is not None
    }
    exits = list(XYZExit.objects.filter_xyz(xyz=("*", "*", graph.map_id)))
    by_road: dict[str, list] = {}
    unbound_exits: list = []
    for exit_obj in exits:
        identity = _object_identity_tag(exit_obj, ROAD_IDENTITY_TAG_CATEGORY)
        if identity:
            by_road.setdefault(identity, []).append(exit_obj)
        else:
            unbound_exits.append(exit_obj)
    for identity, bound in by_road.items():
        if len(bound) > 1:
            raise SparseGraphError(
                f"map {graph.map_id!r} has {len(bound)} exits bound to road {identity!r}"
            )

    used_exits: set[int] = set()
    for edge in graph.edges:
        tag = _road_tag(graph, edge)
        bound = by_road.get(tag)
        exit_obj = bound[0] if bound else None
        if exit_obj is None:
            source_room = source_rooms.get(edge.source.node_id)
            exit_key = exit_spawn_names(edge.direction)[0]
            candidates = [
                candidate
                for candidate in unbound_exits
                if source_room is not None
                and candidate.db_location_id == source_room.id
                and candidate.key.lower() == exit_key
            ]
            if len(candidates) > 1:
                raise SparseGraphError(
                    f"map {graph.map_id!r} cannot bind road {edge.road.road_id!r}: "
                    f"{len(candidates)} legacy exits match {exit_key!r} from "
                    f"{edge.source.node_id!r}"
                )
            if candidates:
                exit_obj = candidates[0]
                unbound_exits.remove(exit_obj)
        if exit_obj is not None:
            if int(exit_obj.id) in used_exits:
                raise SparseGraphError(
                    f"map {graph.map_id!r} binds exit #{exit_obj.id} to more than one road"
                )
            used_exits.add(int(exit_obj.id))
        plan.roads.append(_RoadBinding(edge=edge, exit_obj=exit_obj))

    plan.stale_exits = [
        exit_obj for exit_obj in exits if int(exit_obj.id) not in used_exits
    ]
    return plan


def _room_is_referenced(room) -> bool:
    """Whether anything still depends on ``room`` (occupants, homes, exits)."""

    if room.contents:
        return True
    if ObjectDB.objects.filter(db_destination=room.id).exists():
        return True
    if ObjectDB.objects.filter(db_home=room.id).exists():
        return True
    return False


def _apply_node_binding(plan: _GraphPlan, binding: _NodeBinding) -> SyncReport:
    graph = plan.graph
    node = binding.node
    prototype = _flatten(
        dict(node.prototype),
        f"sparse_room_{graph.map_id}_{node.node_id}",
        "typeclasses.rooms.GridRoom",
    )
    room = binding.room
    created = updated = 0
    if room is None:
        typeclass_path = prototype.get("typeclass") or "typeclasses.rooms.GridRoom"
        room, errors = class_from_module(typeclass_path).create(
            prototype.get("key") or node.key,
            xyz=(node.x, node.y, graph.map_id),
        )
        if errors or room is None:
            raise SparseGraphError(
                f"map {graph.map_id!r} could not create room {node.node_id!r}: {errors}"
            )
        binding.room = room
        created = 1
    else:
        if _set_coordinate_tags(room, (node.x, node.y, graph.map_id)):
            updated = 1
    if room.sparse_node_id != node.node_id:
        room.sparse_node_id = node.node_id
        if not created:
            updated = 1
    identity_tag = _node_tag(graph, node)
    current_tags = room.tags.get(
        category=NODE_IDENTITY_TAG_CATEGORY, return_list=True
    )
    if identity_tag not in current_tags:
        room.tags.add(identity_tag, category=NODE_IDENTITY_TAG_CATEGORY)
    stale_tags = [tag for tag in current_tags if tag != identity_tag]
    for tag in stale_tags:
        room.tags.remove(tag, category=NODE_IDENTITY_TAG_CATEGORY)
    if _apply_prototype(room, prototype) and not created:
        updated = 1
    return SyncReport(created=created, updated=updated)


def _apply_road_binding(plan: _GraphPlan, binding: _RoadBinding) -> SyncReport:
    graph = plan.graph
    edge = binding.edge
    source_room = next(
        item.room for item in plan.nodes if item.node.node_id == edge.source.node_id
    )
    destination_room = next(
        item.room for item in plan.nodes if item.node.node_id == edge.destination.node_id
    )
    key, *aliases = exit_spawn_names(edge.direction)
    prototype = _flatten(
        dict(graph.exit_prototype),
        f"sparse_exit_{graph.map_id}_{edge.road.road_id}",
        "evennia.contrib.grid.xyzgrid.xyzroom.XYZExit",
    )
    exit_obj = binding.exit_obj
    created = updated = 0
    if exit_obj is None:
        typeclass_path = prototype.get("typeclass") or (
            "evennia.contrib.grid.xyzgrid.xyzroom.XYZExit"
        )
        exit_obj, errors = class_from_module(typeclass_path).create(
            key,
            xyz=(edge.source.x, edge.source.y, graph.map_id),
            xyz_destination=(edge.destination.x, edge.destination.y, graph.map_id),
            aliases=aliases,
        )
        if errors or exit_obj is None:
            raise SparseGraphError(
                f"map {graph.map_id!r} could not create road "
                f"{edge.road.road_id!r}: {errors}"
            )
        binding.exit_obj = exit_obj
        created = 1
    else:
        changed = False
        if exit_obj.db_location_id != source_room.id:
            exit_obj.location = source_room
            changed = True
        if exit_obj.db_destination_id != destination_room.id:
            exit_obj.destination = destination_room
            changed = True
        if changed:
            exit_obj.save()
        if exit_obj.key != key or set(exit_obj.aliases.all()) != set(aliases):
            exit_obj.key = key
            exit_obj.aliases.clear()
            exit_obj.aliases.add(list(aliases))
            exit_obj.save()
            changed = True
        if _set_coordinate_tags(
            exit_obj,
            (edge.source.x, edge.source.y, graph.map_id),
            (edge.destination.x, edge.destination.y, graph.map_id),
        ):
            changed = True
        if changed:
            updated = 1
    identity_tag = _road_tag(graph, edge)
    current_tags = exit_obj.tags.get(
        category=ROAD_IDENTITY_TAG_CATEGORY, return_list=True
    )
    if identity_tag not in current_tags:
        exit_obj.tags.add(identity_tag, category=ROAD_IDENTITY_TAG_CATEGORY)
    stale_tags = [tag for tag in current_tags if tag != identity_tag]
    for tag in stale_tags:
        exit_obj.tags.remove(tag, category=ROAD_IDENTITY_TAG_CATEGORY)
    if _apply_prototype(exit_obj, prototype) and not created:
        updated = 1
    return SyncReport(created=created, updated=updated)


def _apply_graph_plan(plan: _GraphPlan, knowledge_journal=None) -> SyncReport:
    report = SyncReport()
    for binding in plan.nodes:
        report += _apply_node_binding(plan, binding)
    for binding in plan.roads:
        report += _apply_road_binding(plan, binding)
    if plan.remapped_coordinates:
        # The knowledge owner rewrites the stored node identity of every moved
        # room inside this transaction, so observations keep their ticks and
        # are never re-recorded as a fresh arrival (map-knowledge cutover).
        from world.rules.map_knowledge import remap_grid_identities

        remap_grid_identities(
            plan.graph.map_id,
            plan.remapped_coordinates,
            journal=knowledge_journal,
        )
    for room in plan.stale_rooms:
        log_info(
            "settlement_graph_node_pruned",
            context={
                "map_id": plan.graph.map_id,
                "room_key": room.key,
                "room_dbref": room.dbref,
            },
        )
        room.delete()
        report += SyncReport(deleted=1)
    for exit_obj in plan.stale_exits:
        log_info(
            "settlement_graph_road_pruned",
            context={
                "map_id": plan.graph.map_id,
                "exit_key": exit_obj.key,
                "exit_dbref": exit_obj.dbref,
            },
        )
        exit_obj.delete()
        report += SyncReport(deleted=1)
    return report


def _invalidate_plan_caches(plans, characters=()) -> None:
    """Restore touched objects and drop their process-local projections.

    A database rollback does not undo Evennia's tag/attribute/alias handler
    caches or the loaded object's field values, so a failed convergence reloads
    each surviving object and resets those caches before the coordinate
    projections are dropped. Objects created inside the rolled-back transaction
    no longer exist; their reload is ignored and they are never referenced
    again by the caller.
    """

    for character in characters:
        for handler_name in ("attributes",):
            reset = getattr(getattr(character, handler_name, None), "reset_cache", None)
            if reset is not None:
                try:
                    reset()
                except Exception:  # observability: ignore R2: handler cache reset is best-effort after rollback
                    continue
    for plan in plans:
        objects = [
            *(binding.room for binding in plan.nodes if binding.room is not None),
            *(binding.exit_obj for binding in plan.roads if binding.exit_obj is not None),
        ]
        for obj in objects:
            try:
                obj.refresh_from_db()
            except Exception:  # observability: ignore R2: rolled-back creations no longer exist
                pass
            for handler_name in ("tags", "aliases", "attributes", "locks"):
                reset = getattr(getattr(obj, handler_name, None), "reset_cache", None)
                if reset is not None:
                    try:
                        reset()
                    except Exception:  # observability: ignore R2: handler cache reset is best-effort after rollback
                        continue
            for cache in ("_xyz", "_xyz_destination", "_xymap"):
                try:
                    if hasattr(obj, cache):
                        delattr(obj, cache)
                except Exception:  # observability: ignore R2: cache invalidation is best-effort after rollback
                    continue


def sync_settlement_graph(graph: SparseSettlementGraph) -> SyncReport:
    """Converge one sparse settlement graph and return what changed."""

    plan = _plan_settlement_graph(graph)
    knowledge_journal: list = []
    try:
        with transaction.atomic():
            report = _apply_graph_plan(plan, knowledge_journal)
    except Exception:
        _invalidate_plan_caches([plan], knowledge_journal)
        raise
    if report.created or report.updated or report.deleted:
        log_info(
            "settlement_graph_synchronized",
            context={
                "map_id": graph.map_id,
                "created": report.created,
                "updated": report.updated,
                "deleted": report.deleted,
            },
        )
    return report


def _clear_grid_display_maps() -> None:
    """Drop the retired ASCII registrations of every declared settlement.

    The meter cutover removed the ASCII authoring/display source. A database
    that booted an older version still carries those declarations in the
    contrib script, so convergence removes exactly the declared settlement
    ids and drops the process-local projection. Synthetic/builder maps are
    untouched, and no room or exit is deleted here.
    """

    grid = XYZGrid.objects.all().first()
    if grid is None:
        return
    stored = grid.db.map_data or {}
    stale = [zcoord for zcoord in stored if zcoord in SETTLEMENT_GRAPHS]
    if not stale:
        return
    for zcoord in stale:
        stored.pop(zcoord)
    grid.db.map_data = stored
    # The contrib caches the parsed maps in ndb; a later display reads the
    # restored db declaration and reloads from it instead of the retired one.
    grid.ndb.grid = None
    grid.ndb.loaded = False
    log_info(
        "settlement_grid_display_retired",
        context={"maps": len(stale), "action": "remove_ascii_registration"},
    )


def sync_grid() -> SyncReport:
    """Converge every declared sparse settlement and bridge Limbo to its gates.

    Every graph is planned read-only before the first write, so a conflicting
    binding refuses with no room, tag, reference or cached coordinate changed.
    The whole convergence then applies in one transaction: stable node
    identities keep rooms, occupants, homes and inbound references across a
    coordinate change, and a second run over unchanged authored data performs
    no managed writes.

    The bridge is one-way (limbo-one-way-gates): one forward exit per
    ``CITY_GATE_REGISTRY`` row, then a prune pass deleting every persisted
    exit that points back into the starting room. A registry row whose gate
    room is missing warns and is skipped; other rows still converge.
    """

    graphs = tuple(SETTLEMENT_GRAPHS.values())
    plans = tuple(_plan_settlement_graph(graph) for graph in graphs)
    report = SyncReport()
    knowledge_journal: list = []
    try:
        with transaction.atomic():
            _clear_grid_display_maps()
            for plan in plans:
                report += _apply_graph_plan(plan, knowledge_journal)

            _sync_grid_room_art()

            register_instance_reclamation()

            limbo = find_starting_rooms(LIMBO_KEY)
            if not limbo:
                log_warn(
                    "bootstrap_grid_limbo_room_missing",
                    context={"room_key": LIMBO_KEY, "action": "skip_bridging_exits"},
                )
                return report
            limbo = limbo[0]

            for row in CITY_GATE_REGISTRY.values():
                gate = GridRoom.objects.filter_xyz(xyz=row.gate_xyz).first()
                if gate is None:
                    log_warn(
                        "bootstrap_grid_gate_missing",
                        context={
                            "map_id": row.map_id,
                            "xyz": row.gate_xyz,
                            "action": "skip_gate_row",
                        },
                    )
                    continue
                _ensure_exit(limbo, gate, key=row.exit_key, aliases=list(row.exit_aliases))

            _prune_exits_into(limbo)
    except Exception:
        _invalidate_plan_caches(plans, knowledge_journal)
        raise
    if report.created or report.updated or report.deleted:
        log_info(
            "settlement_graphs_synchronized",
            context={
                "maps": len(graphs),
                "created": report.created,
                "updated": report.updated,
                "deleted": report.deleted,
            },
        )
    return report


def _sync_grid_room_art() -> None:
    """Converge every authored grid node onto its declared scene facts.

    A boot re-applies the authored table to the real rooms (an already-spawned
    node is never re-created by the contrib), so startup is idempotent. A node
    with no materialized room warns naming the coordinate and is skipped; the
    remaining nodes still converge. Every ``scene_archetype`` written here is a
    registered scene archetype, every ``room_art_key`` is cleared (authored
    grid nodes declare none), and the identity is the authored coordinate.
    """
    for (map_key, x, y), scene_archetype in GRID_NODE_SCENE_ARCHETYPES.items():
        room = GridRoom.objects.filter_xyz((x, y, map_key)).first()
        if room is None:
            log_warn(
                "bootstrap_grid_room_art_missing_room",
                context={
                    "map_id": map_key,
                    "xyz": (x, y, map_key),
                    "action": "skip_grid_node",
                },
            )
            continue
        _apply_room_art(
            room,
            scene_archetype=scene_archetype,
            room_art_key=None,
            scene_identity=grid_scene_identity(map_key, x, y),
        )


def _prune_exits_into(limbo) -> None:
    """Delete every persisted exit whose destination is ``limbo``.

    The synchronizer's declarative convergence over its own exit surface
    (limbo-one-way-gates D3): legacy 「離開王都」/「回虛境」 exits and any
    later reverse object converge away on the next start, no migration. The
    query runs on the indexed ``db_destination`` FK at the unscoped
    ``ObjectDB`` level so every Exit subclass is caught, while the
    ``isinstance`` gate keeps non-exit objects (items with a destination)
    untouched. On a converged database this deletes and logs nothing.
    """

    for exit_obj in ObjectDB.objects.filter(db_destination=limbo.id):
        if not isinstance(exit_obj, Exit):
            continue
        source = exit_obj.location
        log_info(
            "bootstrap_grid_exit_pruned",
            context={
                "exit_key": exit_obj.key,
                "exit_dbref": exit_obj.dbref,
                "source_room_key": source.key if source else None,
                "action": "enforce_one_way_gates",
            },
        )
        exit_obj.delete()


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
    # wilderness-side return_direction: leaving the 東門 (return_direction "w")
    # toward the wild is east.
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