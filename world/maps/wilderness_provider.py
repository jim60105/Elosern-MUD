"""Deterministic wilderness terrain model and map provider (map-wilderness).

The runtime wilderness is the virtual 2700 by 2700 one-kilometre frame declared
by ``world.lore.wilderness_regions`` (world-map-scale design §5-§6): cells are
logical areas, never materialized in bulk, and every validity/lookup query is
bounded local work over integer arithmetic plus the ten-vertex mainland
polygon. Sea, the cliff-walled central ridge and the authored inland waterways
are impassable on foot; ordinary land outside those features is walkable.

Terrain, nominal claim and actual control stay separate layers: this module
returns a terrain region key (``region_for_coordinates``) and, alongside it,
the coordinate-sensitive nominal claim (``nominal_nation_for_coordinates``)
plus the national border lines derived from the same ridge and river
geometry. ``world.lore.nations`` keeps the effective-rule demographic targets.
Nothing here reads the database, a clock, or a random source.
"""

from dataclasses import dataclass
from functools import cache

from evennia.contrib.grid.wilderness.wilderness import WildernessMapProvider

from typeclasses.rooms import TerrainRoom
from world.lore.wilderness_regions import (
    CONTINENT_FRAME_CELLS,
    WILDERNESS_REGION_REGISTRY,
    is_on_mainland,
)
from world.maps.room_art import (
    REGION_SCENE_ARCHETYPES,
    wilderness_scene_identity,
)
# Read the entry registry as a MODULE attribute at call time (never a
# from-import binding): a test rebinding world.lore.wilderness_entry.
# WILDERNESS_ENTRY_REGISTRY must be observed here (wilderness-map-provider
# delta: registry patches change validity without patching the provider).
from world.lore import wilderness_entry as _wilderness_entry_module

# One logical kilometre per wilderness cell over the declared 2700-cell frame
# (0-indexed to 2699). The area inside the frame is ocean plus land; the
# mainland polygon itself carries the 5,000,000 km² land target.
WILDERNESS_KM_PER_CELL = 1
WILDERNESS_MAX_X = CONTINENT_FRAME_CELLS - 1
WILDERNESS_MAX_Y = CONTINENT_FRAME_CELLS - 1

WILDERNESS_NAME = "elosern"

# The central mountain system (world-map-scale design §6): a bending
# north-south corridor broadly around X 1310..1510 whose roughly 200 km width
# includes foothills, valleys and subsidiary ridges. The summit ridge inside it
# is a one-cell-wide cliff wall; only the authored passes below cross it.
_MOUNTAIN_CORRIDOR_HALF_WIDTH = 100
_MOUNTAIN_RIDGE_BASE_X = 1410
_MOUNTAIN_RIDGE_PERIOD = 60
_MOUNTAIN_RIDGE_STEP = 10
_RIDGE_MIN_X = 1300
_RIDGE_MAX_X = 1520
# The ridge's northern limit. It lies inside the northern deep forest, whose
# southern edge is the authored line below; north of the limit the forest
# ground is walkable.
_RIDGE_NORTH_LIMIT_Y = 2200

# Authored crossings of the summit ridge as inclusive Y windows: the principal
# pass near (1410, 980), a southern high trail, and a northern trail. A crossing
# is mountain trail ground (slower, supplies needed), never an all-road
# shortcut; the centre cell of the principal pass is (1410, 980).
RIDGE_PASSES: tuple[tuple[int, int], ...] = (
    (410, 425),
    (970, 990),
    (1770, 1785),
)

# Terrain-region thresholds (authoring constraints from design §6): the
# southern bulk-commerce corridor is the coastal strip. The northern deep
# forest edge and the western hills / highland forest boundary are authored
# lines below (world-map drawer design §3), not straight rows.
_COASTAL_Y_MAX = 500

#: The northern deep forest's southern edge (world-map drawer design §3.2):
#: an x-monotone meandering line averaging about Y 1920, so the forest covers
#: about one fifth of the land. A cell is deep forest when its row is at or
#: north of the edge's row in its column. The forest is narrative wilderness
#: with ordinary forest travel speed; it adds no movement block, and the summit
#: ridge keeps its own northern limit (``_RIDGE_NORTH_LIMIT_Y``) inside it.
NORTH_FOREST_EDGE: tuple[tuple[int, int], ...] = (
    (0, 1950),
    (190, 1950),
    (330, 1900),
    (480, 1955),
    (640, 1925),
    (780, 1920),
    (900, 1890),
    (1040, 1945),
    (1200, 1900),
    (1330, 1935),
    (1470, 1890),
    (1600, 1945),
    (1760, 1905),
    (1900, 1950),
    (2050, 1915),
    (2180, 1925),
    (WILDERNESS_MAX_X, 1925),
)

# Authored inland water networks (design §6): the capital's river runs southwest
# to the kingdom ports, and the imperial network connects the eastern plain to
# the southeastern ports. Water is impassable on foot; the declared fords are
# the ordinary crossings, not a transport mechanic.
#
# 界河 (``border_river``, world-map drawer design §3.1) rises in the central
# range's western foothills at the corridor's first cell (1320, 1410) and
# meanders west inside Y 1290..1410 to the west coast: (124, 1290) is the last
# land cell and its western neighbour is sea. Every segment is shallower than
# 45 degrees with X strictly decreasing, so the rasterizer lays exactly one
# water cell per column and ``_BORDER_RIVER_ROW`` below is that same cell.
# It is the Altoria-Valhalla border; west of the corridor it is crossable on
# foot only at its three fords (the principal one at (830, 1370) on the line
# between the two capitals). Between its source and the summit ridge lies the
# mountain corridor, mountain-trail ground that is not river.
WATERWAY_ROUTES: dict[str, tuple[tuple[int, int], ...]] = {
    "capital_river": ((1150, 1060), (860, 1040), (600, 800), (310, 360)),
    "imperial_river": ((1950, 1260), (1990, 1100), (2070, 700), (2060, 250)),
    "imperial_east_branch": ((2070, 700), (2200, 600), (2390, 460)),
    "border_river": (
        (1320, 1410),
        (1210, 1380),
        (1100, 1350),
        (990, 1395),
        (900, 1380),
        (830, 1370),
        (740, 1330),
        (650, 1310),
        (530, 1355),
        (400, 1340),
        (290, 1300),
        (170, 1290),
        (124, 1290),
    ),
}

WATERWAY_FORDS: dict[str, tuple[tuple[int, int], ...]] = {
    "capital_river": ((860, 1040), (600, 800), (400, 497)),
    "imperial_river": ((1990, 1100), (2067, 600)),
    "imperial_east_branch": ((2300, 526),),
    # Upstream, principal (on the Altoria-Valhalla capital line), downstream.
    "border_river": ((1150, 1363), (830, 1370), (450, 1345)),
}

# Short registry direction -> the contrib's exit key long form (the stock
# set_active_coordinates pass keys exits "north".."northwest").
LONG_DIRECTIONS = {
    "n": "north",
    "ne": "northeast",
    "e": "east",
    "se": "southeast",
    "s": "south",
    "sw": "southwest",
    "w": "west",
    "nw": "northwest",
}

# The exact lock-string form stock set_active_coordinates applies for a valid
# neighbor; the gate hook re-applies this same form to a registered gate exit.
_EXIT_OPEN = "traverse:true();view:true()"

# Footprint cache: keyed on the ordered (anchor_key, entry) pairs of the live
# registry snapshot. The key tuple RETAINS the entry objects, so their ids
# cannot be recycled behind the cache's back; a patch/rebind replaces value
# objects and produces a key miss on the next call.
_FOOTPRINT_CACHE: dict[tuple[tuple[str, object], ...], frozenset] = {}


def _rasterize_segment(
    start: tuple[int, int], end: tuple[int, int]
) -> set[tuple[int, int]]:
    """Every integer cell on the straight segment between two cell points.

    Deterministic integer interpolation (no floats, no library): the walk takes
    one step per axis major, so the rasterized waterway is continuous.
    """
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        return {(x0, y0)}
    return {
        (x0 + (x1 - x0) * index // steps, y0 + (y1 - y0) * index // steps)
        for index in range(steps + 1)
    }


def _rasterize_routes(
    routes: dict[str, tuple[tuple[int, int], ...]],
) -> frozenset[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for points in routes.values():
        for start, end in zip(points, points[1:]):
            cells |= _rasterize_segment(start, end)
    return frozenset(cells)


_WATERWAY_CELLS = _rasterize_routes(WATERWAY_ROUTES) - frozenset(
    cell for fords in WATERWAY_FORDS.values() for cell in fords
)
_FORD_CELLS = frozenset(cell for fords in WATERWAY_FORDS.values() for cell in fords)


def _route_row_at(points: tuple[tuple[int, int], ...], x: int) -> int:
    """The row an x-monotone, shallow route occupies in column ``x``.

    Uses the rasterizer's own integer arithmetic (``_rasterize_segment``), so
    for a route whose segments all satisfy ``|dx| >= |dy|`` the result is the
    exact rasterized cell of that column. Outside the route's X span the
    nearest end vertex's row continues straight (the derived extension that
    closes a line against the ridge or the frame edge).
    """
    for start, end in zip(points, points[1:]):
        x0, y0 = start
        x1, y1 = end
        if min(x0, x1) <= x <= max(x0, x1):
            steps = abs(x1 - x0)
            if steps == 0:
                return y0
            index = abs(x - x0)
            return y0 + (y1 - y0) * index // steps
    west, east = sorted((points[0], points[-1]))
    return west[1] if x < west[0] else east[1]


def _column_table(points: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    """``_route_row_at`` precomputed for every frame column (hot-path lookup)."""
    return tuple(_route_row_at(points, x) for x in range(WILDERNESS_MAX_X + 1))


_FOREST_EDGE_ROW = _column_table(NORTH_FOREST_EDGE)
_BORDER_RIVER_ROW = _column_table(WATERWAY_ROUTES["border_river"])


def _clamped_column(x: int) -> int:
    return min(max(x, 0), WILDERNESS_MAX_X)


def forest_edge_row(x: int) -> int:
    """The northern deep forest's first row in column ``x``."""
    return _FOREST_EDGE_ROW[_clamped_column(x)]


def border_river_row(x: int) -> int:
    """The border river's row in column ``x`` (or its derived extension).

    East of the source the river's source row continues as the watershed line
    to the summit ridge; west of the mouth the mouth row continues to sea.
    """
    return _BORDER_RIVER_ROW[_clamped_column(x)]


_FOREST_EDGE_Y_MIN = min(y for _, y in NORTH_FOREST_EDGE)
_FOREST_EDGE_Y_MAX = max(y for _, y in NORTH_FOREST_EDGE)
_BORDER_RIVER_Y_MIN = min(y for _, y in WATERWAY_ROUTES["border_river"])
_BORDER_RIVER_Y_MAX = max(y for _, y in WATERWAY_ROUTES["border_river"])

#: Authored enumeration windows per region, as
#: ``(x_min, x_max, y_min, y_max)`` inclusive. They are a superset of each
#: region's cells (the classifier still decides membership) and exist so
#: sparse-index consumers such as ambient provisioning enumerate only the
#: relevant band instead of scanning the whole frame. Every region key of
#: ``WILDERNESS_REGION_REGISTRY`` has a window; the bands follow the authored
#: forest edge and border river extents.
REGION_SEARCH_BOXES: dict[str, tuple[int, int, int, int]] = {
    "north_deep_forest": (0, WILDERNESS_MAX_X, _FOREST_EDGE_Y_MIN, WILDERNESS_MAX_Y),
    "central_mountains": (
        _MOUNTAIN_RIDGE_BASE_X - 2 * _MOUNTAIN_RIDGE_STEP - _MOUNTAIN_CORRIDOR_HALF_WIDTH,
        _MOUNTAIN_RIDGE_BASE_X + 2 * _MOUNTAIN_RIDGE_STEP + _MOUNTAIN_CORRIDOR_HALF_WIDTH,
        0,
        _FOREST_EDGE_Y_MAX - 1,
    ),
    "eastern_plains": (0, WILDERNESS_MAX_X, _COASTAL_Y_MAX + 1, _FOREST_EDGE_Y_MAX - 1),
    "southeast_coast": (0, WILDERNESS_MAX_X, 0, _COASTAL_Y_MAX),
    "southwest_coast": (0, WILDERNESS_MAX_X, 0, _COASTAL_Y_MAX),
    "northwest_highland_forest": (
        0,
        WILDERNESS_MAX_X,
        _BORDER_RIVER_Y_MIN + 1,
        _FOREST_EDGE_Y_MAX - 1,
    ),
    "western_hills_valleys": (
        0,
        WILDERNESS_MAX_X,
        _COASTAL_Y_MAX + 1,
        _BORDER_RIVER_Y_MAX,
    ),
}


def _footprint_union() -> frozenset:
    """Every anchor footprint cell in the live registry (point shapes: none)."""
    registry = _wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY
    snapshot = tuple(registry.items())
    cached = _FOOTPRINT_CACHE.get(snapshot)
    if cached is None:
        cached = frozenset(cell for entry in registry.values() for cell in entry.footprint_cells)
        _FOOTPRINT_CACHE[snapshot] = cached
        # Keep the cache bounded against long test histories (insertion order:
        # the entry just stored is the newest, never the first popped).
        while len(_FOOTPRINT_CACHE) > 8:
            _FOOTPRINT_CACHE.pop(next(iter(_FOOTPRINT_CACHE)))
    return cached


def is_footprint_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is an anchor footprint cell of the live registry."""
    return coordinates in _footprint_union()


def _ridge_center_x(y: int) -> int:
    """The summit ridge's X centre at row ``y`` (a deterministic bend)."""
    bend = (y // _MOUNTAIN_RIDGE_PERIOD) % 5 - 2
    return _MOUNTAIN_RIDGE_BASE_X + bend * _MOUNTAIN_RIDGE_STEP


def _ridge_span(y: int) -> tuple[int, int]:
    """The ridge's inclusive X span at row ``y``.

    Spanning every column between this row's centre and the next row's centre
    keeps the wall 8-connected, so no diagonal gap can slip through it.
    """
    current = _ridge_center_x(y)
    following = _ridge_center_x(y + 1)
    return (min(current, following), max(current, following))


def is_closed_ridge_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is an impassable summit-ridge/cliff cell.

    The ridge bends through the central corridor up to its northern limit; the
    authored pass windows are open ground, so land crossings require one of
    them.
    """
    x, y = coordinates
    if not (_RIDGE_MIN_X <= x <= _RIDGE_MAX_X) or y >= _RIDGE_NORTH_LIMIT_Y:
        return False
    if any(low <= y <= high for low, high in RIDGE_PASSES):
        return False
    low, high = _ridge_span(y)
    return low <= x <= high


def is_inland_water_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is impassable river water (a ford is not water)."""
    return coordinates in _WATERWAY_CELLS


def is_land_cell(coordinates: tuple[int, int]) -> bool:
    """Whether the cell's centre lies inside the mainland polygon.

    A cell is an area; its representative centre is offset half a kilometre
    into the cell (``world.lore.wilderness_regions.cell_center_m``).
    """
    x, y = coordinates
    return is_on_mainland(x + 0.5, y + 0.5)


def is_passable_terrain(coordinates: tuple[int, int]) -> bool:
    """Whether the cell is walkable ground (not a ridge wall or water)."""
    return not is_closed_ridge_cell(coordinates) and not is_inland_water_cell(
        coordinates
    )


def is_walkable_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is in-frame, mainland and passable on foot."""
    x, y = coordinates
    if not (0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y):
        return False
    return is_land_cell((x, y)) and is_passable_terrain((x, y))


def is_valid_wilderness_cell(coordinates: tuple[int, int]) -> bool:
    """The single wilderness-cell validity rule every consumer shares.

    In-frame, land-side, passable terrain, and not an anchor footprint cell of
    the live ``WILDERNESS_ENTRY_REGISTRY`` (point shapes contribute no
    footprint). The provider, the canonical destination resolver and the local
    map all read this one rule.
    """
    return is_walkable_cell(coordinates) and not is_footprint_cell(coordinates)


def region_for_coordinates(x: int, y: int) -> str:
    """Return the terrain region key for ``(x, y)``.

    Pure integer partition over the two coordinates alone -- no database read,
    no randomness, no wall-clock input. Same input always returns the same key,
    and every cell inside the frame (including sea cells) resolves to a
    registered region. The central mountain region follows the authored
    bending corridor rather than a rectangular band.
    """

    if y >= forest_edge_row(x):
        return "north_deep_forest"
    centre = _ridge_center_x(y)
    if abs(x - centre) <= _MOUNTAIN_CORRIDOR_HALF_WIDTH:
        return "central_mountains"
    if x > centre:  # east of the mountains
        return "southeast_coast" if y <= _COASTAL_Y_MAX else "eastern_plains"
    # x < centre -- west of the mountains; the border river divides the
    # western hills and valleys from the northwest highland forest.
    if y <= _COASTAL_Y_MAX:
        return "southwest_coast"
    if y > border_river_row(x):
        return "northwest_highland_forest"
    return "western_hills_valleys"


def nominal_nation_for_coordinates(x: int, y: int) -> str:
    """Return the one nation that nominally claims ``(x, y)``.

    The coordinate-sensitive claim layer (world-map drawer design §3.3): east
    of the summit ridge is Grandia (the ridge's centre line continues north of
    its own limit through the deep forest); west of it, the border river
    divides Altoria (the river row and south) from Valhalla (north). Region
    keys stay terrain: the mountain and deep-forest regions span several
    claims, which ``WildernessRegion.nominal_nation_keys`` lists. Nominal
    claims are not effective rule; the demographic targets in
    ``world.lore.nations`` are unchanged. Pure integer arithmetic.
    """
    if x > _ridge_center_x(y):
        return "grandia"
    if y <= border_river_row(x):
        return "altoria"
    return "valhalla"


@dataclass(frozen=True)
class NationalBorder:
    """One displayed national border line in wilderness cell coordinates.

    ``nation_keys`` is the sorted pair the line separates. The lines are
    derived from the summit ridge and the border river; no political polyline
    is authored, and no line is drawn inside the northern deep forest.
    """

    nation_keys: tuple[str, str]
    points: tuple[tuple[int, int], ...]


def _ridge_polyline(y_start: int, y_end: int) -> tuple[tuple[int, int], ...]:
    """The ridge centre line from ``y_start`` to ``y_end`` (inclusive rows)."""
    points = [(_ridge_center_x(y_start), y_start)]
    for y in range(y_start, y_end):
        here, following = _ridge_center_x(y), _ridge_center_x(y + 1)
        if here != following:
            points.extend(((here, y), (following, y + 1)))
    points.append((_ridge_center_x(y_end), y_end))
    deduplicated: list[tuple[int, int]] = []
    for point in points:
        if not deduplicated or deduplicated[-1] != point:
            deduplicated.append(point)
    return tuple(deduplicated)


@cache
def national_borders() -> tuple[NationalBorder, ...]:
    """The displayed national borders, derived from the ridge and the river.

    * Altoria | Valhalla: the border river from its mouth to its source, then
      the source row east to the summit ridge (the derived watershed line the
      claim resolver uses between the source and the ridge).
    * Altoria | Grandia: the ridge centre line from the southern coast north to
      the river's source row.
    * Grandia | Valhalla: the ridge centre line from that row north to the last
      row south of the deep forest edge; inside the forest no line is drawn.
    """
    river = WATERWAY_ROUTES["border_river"]
    source_x, junction_y = river[0]
    junction = (_ridge_center_x(junction_y), junction_y)
    river_line = tuple(reversed(river)) + ((junction,) if junction[0] != source_x else ())
    ridge_start = next(
        y for y in range(WILDERNESS_MAX_Y + 1) if is_land_cell((_ridge_center_x(y), y))
    )
    ridge_end = junction_y
    while (ridge_end + 1) < forest_edge_row(_ridge_center_x(ridge_end + 1)):
        ridge_end += 1
    return (
        NationalBorder(("altoria", "valhalla"), river_line),
        NationalBorder(("altoria", "grandia"), _ridge_polyline(ridge_start, junction_y)),
        NationalBorder(("grandia", "valhalla"), _ridge_polyline(junction_y, ridge_end)),
    )


def terrain_description(x: int, y: int) -> str:
    """Return one deterministic flavor variant for the region at ``(x, y)``.

    Pure closed-form integer arithmetic on the two coordinates alone -- no RNG,
    no LLM, no DB read. The ``92821``/``68917`` multipliers are deliberately
    large odd numbers purely to spread adjacent coordinates across variants.
    """

    region = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)]
    variants = region.terrain_flavor_zh
    index = (x * 92821 + y * 68917) % len(variants)
    return variants[index]


class ElosernWildernessMapProvider(WildernessMapProvider):
    """Bounded 2700x2700 wilderness frame at 1 km/cell over the terrain model."""

    room_typeclass = TerrainRoom

    @property
    def exit_typeclass(self):
        """Resolve the exit typeclass lazily (design.md task 7.2's forward reference).

        ``typeclasses/exits.py`` imports this module's ``WILDERNESS_NAME``, so a
        module-scope import of the exit class here would be circular. The
        contrib accesses ``mapprovider.exit_typeclass`` on the pickled instance,
        so a property resolves it on first use without a load-time cycle.
        """

        from typeclasses.exits import WildernessReturnExit

        return WildernessReturnExit

    def is_valid_coordinates(self, wilderness, coordinates):
        # The shared rule: frame, mainland, passable terrain, no anchor
        # footprint. The stock per-exit lock pass and at_traverse_coordinates
        # re-check, the canonical resolver and the local map all inherit this
        # single boundary rule; no query scans the frame.
        return is_valid_wilderness_cell(tuple(coordinates))

    def get_location_name(self, coordinates):
        return WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh

    def at_prepare_room(self, coordinates, caller, room):
        # D-3/unified-room-art-metadata: re-set EVERY scene fact unconditionally
        # on every call -- a TerrainRoom is pooled and reused across
        # coordinates, so a stale archetype, identity or room-art key from a
        # previous place would silently persist if these were not re-assigned.
        # The archetype is the authored region->scene mapping (a registered
        # scene key, never the raw terrain region key), the identity is the
        # CURRENT wilderness' name plus the current coordinates, and the
        # room-art key is cleared because wilderness declares none -- an
        # earlier place's key must never leak into another coordinate.
        wilderness = room.wilderness
        wilderness_name = getattr(wilderness, "key", None) or WILDERNESS_NAME
        region = region_for_coordinates(*coordinates)
        room.scene_archetype = REGION_SCENE_ARCHETYPES[region]
        room.scene_identity = wilderness_scene_identity(wilderness_name, *coordinates)
        room.room_art_key = None
        room.ndb.active_desc = terrain_description(*coordinates)
        # wilderness-monster-population D-4: ensure the deterministic monster
        # population for this coordinate whenever a wilderness script is
        # attached. Deferred import breaks the load-time cycle: this module is
        # imported by wilderness_population, which reads region_for_coordinates
        # from here.
        if wilderness is not None:
            from world.maps.wilderness_population import ensure_population

            ensure_population(wilderness, coordinates)
        # Gate-face lock re-application (design D3): runs after the stock lock
        # pass of the same set_active_coordinates activation, so it overrides
        # exactly one activation's lock state and stock recomputes everything
        # on the next. Away from gateway cells it touches no locks at all.
        self._apply_gate_locks(coordinates, room)

    def _apply_gate_locks(self, coordinates, room):
        """Open the registered gate exit(s) a room shows at ``coordinates``."""
        registry = _wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY
        exits_by_key = {exit_obj.key: exit_obj for exit_obj in room.exits}
        for entry in registry.values():
            if entry.is_point_shape:
                # Concealed point entry: only the authored eligible entry
                # direction is a gateway. Unrelated directions stay ordinary
                # terrain-validity steps, so a cave never hijacks a route.
                if coordinates == entry.anchor_cell:
                    for gate in entry.gates:
                        exit_obj = exits_by_key.get(
                            LONG_DIRECTIONS[gate.return_direction]
                        )
                        if exit_obj is not None:
                            exit_obj.locks.add(_EXIT_OPEN)
                continue
            for gate in entry.gates:
                if entry.approach_cell(gate) != coordinates:
                    continue
                exit_obj = exits_by_key.get(LONG_DIRECTIONS[gate.return_direction])
                if exit_obj is not None:
                    exit_obj.locks.add(_EXIT_OPEN)
