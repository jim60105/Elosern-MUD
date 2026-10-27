"""Read-only canonical resolution of accepted commission destinations.

The area and world map presenters share this one interpretation of where an
accepted commission points (world-map drawer design §5.4). Each resolved
destination carries two separate facts:

- ``world_cell``: the continental wilderness cell used for world display and
  for bearings. ANCHOR and GRID destinations deliberately use their
  settlement's anchor cell rather than applying an arbitrary local offset.
- ``map_key`` / ``node_id``: the canonical local node identity
  (``grid:<map>:<x>:<y>`` or ``wild:elosern:<x>:<y>``) an area map marks when
  the destination lies on the map being viewed.

Supported families: ANCHOR locators, GRID locators, bound instances, regional
species hunts (the legal cell of the target terrain region nearest the player)
and authored monster sites. Every other objective (tier hunts, acquire,
deliver, rendezvous escorts) and every destination whose canonical source is
missing resolves to nothing: no node or coordinate is ever invented.

This module is server-only. It reads the quest log, lore registries and the
terrain classifier; it never writes quests, knowledge, rooms or the clock, and
it never serializes exact positions to a browser. Precision filtering (for
example the world map's 50 km rounding) belongs to the consuming panel.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
from world.lore.monster_placement import MONSTER_SITE_REGISTRY
from world.maps import wilderness_provider
from world.maps.map_data import settlement_graph
from world.maps.wilderness_provider import (
    REGION_SEARCH_BOXES,
    WILDERNESS_NAME,
    is_valid_wilderness_cell,
    region_for_coordinates,
)
from world.observability import log_warn
from world.quests.definitions import DestinationKind, ObjectiveKind
from world.quests.runtime import (
    QuestState,
    definition_for,
    from_storage,
    validate_record_runtime,
)
from world.rules.map_knowledge import NodeIDError, encode_grid, encode_room, encode_wild


class DestinationFamily(StrEnum):
    """The closed set of destination families this resolver supports."""

    ANCHOR = "anchor"
    GRID = "grid"
    BOUND_INSTANCE = "bound_instance"
    SPECIES_HUNT = "species_hunt"
    MONSTER_SITE = "monster_site"


@dataclass(frozen=True, slots=True)
class QuestDestination:
    """One accepted commission's resolved destination (server-internal).

    ``world_cell`` is present when the destination has a continental position.
    A bound instance can have none (its origin room is gone or has no world
    cell), so the field is optional. ``map_key``/``node_id`` name the
    canonical local node when one exists; an ANCHOR whose anchor has no built
    settlement node keeps only its world cell.
    """

    quest_id: str
    definition_key: str
    family: DestinationFamily
    world_cell: tuple[int, int] | None
    map_key: str | None
    node_id: str | None


#: The edge length, in cells, of one search tile of the nearest-cell search.
SEARCH_BLOCK_CELLS = 16

_BLOCK_UNKNOWN = 0
_BLOCK_EMPTY = 1
_BLOCK_OCCUPIED = 2

#: Per (region, window, tile size) occupancy memo of the production terrain
#: classifier, which is a pure integer function of the coordinates: whether a
#: tile holds any cell of a region never changes. Any other classifier (a
#: synthetic test fixture or a patched provider) is never memoized, and
#: legality (which reads the live footprint registry) is never cached.
_OCCUPANCY: dict[tuple[str, tuple[int, int, int, int], int], bytearray] = {}


def clear_search_memo() -> None:
    """Forget every remembered tile occupancy (tests and data reloads)."""
    _OCCUPANCY.clear()


def _tile_lower_bound(origin: tuple[int, int], rect: tuple[int, int, int, int]) -> int:
    """Squared distance from ``origin`` to the nearest cell of ``rect``."""
    ox, oy = origin
    x0, x1, y0, y1 = rect
    dx = x0 - ox if ox < x0 else (ox - x1 if ox > x1 else 0)
    dy = y0 - oy if oy < y0 else (oy - y1 if oy > y1 else 0)
    return dx * dx + dy * dy


def nearest_region_cell(
    origin: tuple[int, int],
    region_key: str,
    *,
    classify: Callable[[int, int], str],
    is_legal: Callable[[tuple[int, int]], bool],
    bounds: tuple[int, int, int, int],
    block: int = SEARCH_BLOCK_CELLS,
) -> tuple[int, int] | None:
    """The legal cell of ``region_key`` nearest ``origin``, or ``None``.

    ``bounds`` is the region's inclusive ``(x_min, x_max, y_min, y_max)``
    search window, a superset of its cells. The order is the smallest squared
    Euclidean cell distance, then the smallest ``x``, then the smallest ``y``,
    so equal-distance candidates always resolve to the same cell.

    The window is tiled; tiles are visited in increasing lower-bound distance
    and the search stops once no remaining tile can hold a cell at least as
    near as the best found (ties included). Tiles without any region cell are
    remembered, so repeated map views do not rescan them.
    """
    x_min, x_max, y_min, y_max = bounds
    if x_min > x_max or y_min > y_max:
        return None
    columns = (x_max - x_min) // block + 1
    rows = (y_max - y_min) // block + 1
    if classify is wilderness_provider.region_for_coordinates:
        memo_key = (region_key, (x_min, x_max, y_min, y_max), block)
        occupancy = _OCCUPANCY.get(memo_key)
        if occupancy is None:
            occupancy = bytearray(columns * rows)
            _OCCUPANCY[memo_key] = occupancy
    else:
        occupancy = bytearray(columns * rows)

    tiles = []
    for column in range(columns):
        tx0 = x_min + column * block
        tx1 = min(tx0 + block - 1, x_max)
        for row in range(rows):
            ty0 = y_min + row * block
            ty1 = min(ty0 + block - 1, y_max)
            rect = (tx0, tx1, ty0, ty1)
            tiles.append((_tile_lower_bound(origin, rect), column * rows + row, rect))
    tiles.sort()

    ox, oy = origin
    best: tuple[int, int, int] | None = None
    for lower_bound, index, (tx0, tx1, ty0, ty1) in tiles:
        if best is not None and lower_bound > best[0]:
            break
        state = occupancy[index]
        if state == _BLOCK_EMPTY:
            continue
        occupied = False
        for x in range(tx0, tx1 + 1):
            for y in range(ty0, ty1 + 1):
                if classify(x, y) != region_key:
                    continue
                occupied = True
                candidate = ((x - ox) ** 2 + (y - oy) ** 2, x, y)
                if best is not None and candidate >= best:
                    continue
                if is_legal((x, y)):
                    best = candidate
        if state == _BLOCK_UNKNOWN:
            occupancy[index] = _BLOCK_OCCUPIED if occupied else _BLOCK_EMPTY
    return None if best is None else (best[1], best[2])


def _settlement_anchor_cell(map_key: str) -> tuple[int, int] | None:
    """The wilderness anchor cell of the settlement built on ``map_key``."""
    for placement in ANCHOR_PLACEMENT_REGISTRY.values():
        if placement.zcoord == map_key:
            geography = ANCHOR_GEOGRAPHY_REGISTRY.get(placement.anchor_key)
            return None if geography is None else tuple(geography.cell)
    return None


def _grid_node(map_key: str, x: int, y: int) -> str | None:
    """The canonical node ID of an existing settlement node, or ``None``."""
    graph = settlement_graph(map_key)
    if graph is None or graph.node_at((x, y)) is None:
        return None
    try:
        return encode_grid(map_key, x, y)
    except NodeIDError:  # observability: ignore R2: an out-of-grammar position is simply not a markable node; the caller omits the identity
        return None


def _wild_node(cell: tuple[int, int]) -> str | None:
    try:
        return encode_wild(WILDERNESS_NAME, cell[0], cell[1])
    except NodeIDError:  # observability: ignore R2: an out-of-grammar position is simply not a markable node; the caller omits the identity
        return None


def enclosing_anchor_cell(room: Any) -> tuple[int, int] | None:
    """Read the unique registered enclosing anchor of a coordinate-free room."""
    from typeclasses.rooms import Room
    from world.lore.settlements.places import PLACE_REGISTRY

    if not isinstance(room, Room):
        return None
    tags = set(room.tags.all())
    anchors = {place.settlement_key for key, place in PLACE_REGISTRY.items() if key in tags}
    if len(anchors) != 1:
        return None
    geography = ANCHOR_GEOGRAPHY_REGISTRY.get(next(iter(anchors)))
    return None if geography is None else tuple(geography.cell)


def instance_origin(room: Any) -> Any:
    """Unwrap one instance origin without creating a persistent Attribute."""
    from typeclasses.rooms import InstanceRoom

    if isinstance(room, InstanceRoom):
        room = room.attributes.get("origin_room")
        if isinstance(room, InstanceRoom):
            return None
    return room


def _room_world_cell(room: Any) -> tuple[int, int] | None:
    """The continental cell a room is reached from, or ``None`` when unknown."""
    from typeclasses.rooms import GridRoom, TerrainRoom

    room = instance_origin(room)
    if isinstance(room, TerrainRoom):
        coordinates = getattr(room, "coordinates", None)
        if coordinates is None:
            return None
        return (int(coordinates[0]), int(coordinates[1]))
    if isinstance(room, GridRoom):
        xyz = getattr(room, "xyz", None)
        if not xyz or len(xyz) != 3:
            return None
        return _settlement_anchor_cell(str(xyz[2]))
    return enclosing_anchor_cell(room)


def _bound_instance_destination(record) -> QuestDestination | None:
    """Resolve the accepted record's canonical bound ``InstanceRoom`` identity.

    The room dbref is the persisted stage binding; a missing or non-instance
    room resolves to nothing rather than inventing an identity. The origin
    world cell is only used for a bearing when the destination is not on the
    displayed instance map.
    """
    room_id = record.stage_room_id
    if isinstance(room_id, bool) or not isinstance(room_id, int) or room_id <= 0:
        return None
    from evennia.objects.models import ObjectDB
    from typeclasses.rooms import InstanceRoom

    room = ObjectDB.objects.filter(id=room_id).first()
    if room is None or not isinstance(room, InstanceRoom):
        return None
    try:
        node_id = encode_room(int(room.pk))
    except NodeIDError:  # observability: ignore R2: an impossible dbref cannot be a markable node
        return None
    return QuestDestination(
        record.quest_id,
        record.definition_key,
        DestinationFamily.BOUND_INSTANCE,
        _room_world_cell(room),
        None,
        node_id,
    )


def _resolve_locator(record, definition, locator) -> QuestDestination | None:
    if locator is None:
        return None
    if locator.kind is DestinationKind.ANCHOR:
        geography = ANCHOR_GEOGRAPHY_REGISTRY.get(locator.anchor_key)
        if geography is None:
            return None
        placement = ANCHOR_PLACEMENT_REGISTRY.get(locator.anchor_key)
        node_id = None
        if placement is not None:
            from world.maps.static_references import settlement_node_xy

            node_id = _grid_node(
                placement.zcoord,
                *settlement_node_xy(
                    placement.node, source=f"anchor placement {placement.anchor_key}"
                ),
            )
        return QuestDestination(
            record.quest_id,
            record.definition_key,
            DestinationFamily.ANCHOR,
            tuple(geography.cell),
            placement.zcoord if node_id is not None else None,
            node_id,
        )
    if locator.kind is DestinationKind.GRID:
        if locator.xyz is None:
            return None
        x, y, map_key = locator.xyz
        world_cell = _settlement_anchor_cell(map_key)
        if world_cell is None:
            return None
        # As for ANCHOR: the settlement's anchor cell is canonical even when
        # the locator names no built node; the local identity is then absent.
        node_id = _grid_node(map_key, x, y)
        return QuestDestination(
            record.quest_id,
            record.definition_key,
            DestinationFamily.GRID,
            world_cell,
            map_key if node_id is not None else None,
            node_id,
        )
    if locator.kind is DestinationKind.BOUND_INSTANCE:
        return _bound_instance_destination(record)
    # Anything else carries no static map position.
    return None


def _wild_destination(record, family, cell) -> QuestDestination | None:
    if not is_valid_wilderness_cell((cell[0], cell[1])):
        return None
    node_id = _wild_node(cell)
    if node_id is None:
        return None
    return QuestDestination(
        record.quest_id,
        record.definition_key,
        family,
        (cell[0], cell[1]),
        WILDERNESS_NAME,
        node_id,
    )


def resolve_record_destination(
    record, definition, *, origin_cell: tuple[int, int] | None
) -> QuestDestination | None:
    """Resolve one accepted record's current-stage destination, or ``None``.

    ``origin_cell`` is the player's wilderness cell; a species hunt needs it
    and resolves to nothing without one.
    """
    if record.state is not QuestState.IN_PROGRESS:
        return None
    objective = definition.stages[record.stage_index].objective
    if objective.kind in (ObjectiveKind.REACH, ObjectiveKind.ESCORT):
        return _resolve_locator(record, definition, objective.destination)
    if objective.kind is not ObjectiveKind.DEFEAT:
        return None
    if objective.site_key is not None:
        site = MONSTER_SITE_REGISTRY.get(objective.site_key)
        if site is None:
            return None
        return _wild_destination(record, DestinationFamily.MONSTER_SITE, site.coordinates)
    if objective.region_key is not None:
        bounds = REGION_SEARCH_BOXES.get(objective.region_key)
        if origin_cell is None or bounds is None:
            return None
        cell = nearest_region_cell(
            origin_cell,
            objective.region_key,
            classify=region_for_coordinates,
            is_legal=is_valid_wilderness_cell,
            bounds=bounds,
        )
        if cell is None:
            return None
        return _wild_destination(record, DestinationFamily.SPECIES_HUNT, cell)
    return None


def resolve_accepted_destinations(
    quest_source: Any,
    *,
    origin_cell: tuple[int, int] | None,
    tracked: set[str] | None = None,
) -> tuple[QuestDestination, ...]:
    """Every resolvable accepted destination of ``quest_source``'s quest log.

    Each entry is read and validated on its own, so a commission that cannot
    be read or resolved is skipped (and logged) while every other accepted
    destination remains available. Reading writes nothing. When ``tracked``
    is a set, the quest IDs of tracked in-progress records from this same
    read are added to it, so a panel's tracking flags never come from a
    second, possibly different, read of the log.
    """
    destinations: list[QuestDestination] = []
    entries = getattr(getattr(quest_source, "db", None), "quest_log", None)
    if not isinstance(entries, (list, tuple)):
        # Evennia serves a stored list as a ``_SaverList``; anything that is
        # not a sequence has nothing a map could show.
        try:
            entries = list(entries or ())
        except TypeError as error:
            log_warn("map_quest_destination_unresolved", exc=error, context={"quest": None})
            return ()
    for entry in entries:
        quest_id = None
        definition_key = None
        try:
            if hasattr(entry, "get"):
                quest_id = entry.get("quest_id")
                definition_key = entry.get("definition_key")
            record = from_storage(dict(entry))
            validate_record_runtime(record)
            if record.state is not QuestState.IN_PROGRESS:
                continue
            if tracked is not None and record.tracked:
                tracked.add(record.quest_id)
            definition = definition_for(record)
            destination = resolve_record_destination(
                record, definition, origin_cell=origin_cell
            )
        except Exception as error:  # one unreadable commission never hides the others
            log_warn(
                "map_quest_destination_unresolved",
                exc=error,
                context={"quest": quest_id, "definition": definition_key},
            )
            continue
        if destination is not None:
            destinations.append(destination)
    return tuple(destinations)


def actor_world_cell(actor: Any) -> tuple[int, int] | None:
    """The wilderness cell the actor stands in, or ``None`` when unknown.

    A wilderness room gives its own cell and a settlement grid room its
    settlement's anchor cell. An instance room has no coordinates of its own
    and uses the room it was entered from. Registered ordinary interiors use
    their unique enclosing anchor; unknown interiors resolve to nothing.
    """
    location = getattr(actor, "location", None)
    if location is None:
        return None
    return _room_world_cell(location)


def _quest_source(actor: Any) -> Any:
    """The quest-log holder for ``actor``: a possessing puppet's owner."""
    quest_source = actor
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    if possessed_by is not None:
        from world.rules.possession import _resolve_live_object

        owner = _resolve_live_object(int(possessed_by))
        if owner is not None:
            quest_source = owner
    return quest_source


def accepted_destinations_for(actor: Any) -> tuple[QuestDestination, ...]:
    """The accepted destinations a map panel shows for ``actor``.

    A possessing puppet reads its owner's quest log (as the objectives panel
    does); the nearest-hunt origin is the puppet's own position.
    """
    return resolve_accepted_destinations(_quest_source(actor), origin_cell=actor_world_cell(actor))


def accepted_destinations_with_tracking(
    actor: Any,
) -> tuple[tuple[QuestDestination, ...], frozenset[str]]:
    """``accepted_destinations_for`` plus the tracked quest IDs of the same read."""
    tracked: set[str] = set()
    destinations = resolve_accepted_destinations(
        _quest_source(actor), origin_cell=actor_world_cell(actor), tracked=tracked
    )
    return destinations, frozenset(tracked)


__all__ = [
    "SEARCH_BLOCK_CELLS",
    "DestinationFamily",
    "QuestDestination",
    "accepted_destinations_for",
    "accepted_destinations_with_tracking",
    "actor_world_cell",
    "clear_search_memo",
    "nearest_region_cell",
    "resolve_accepted_destinations",
    "resolve_record_destination",
]
