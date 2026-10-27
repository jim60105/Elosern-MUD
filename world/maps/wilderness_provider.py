"""Authored wilderness terrain snapshot and its Evennia map provider.

The deterministic terrain rules themselves (region classification, ridge,
waterways, land test, validity, flavours, derived national borders) live in
:mod:`elosern_map_core.terrain`. This module owns the game side of that
boundary:

* the authored terrain declarations for the 2700 by 2700 one-kilometre frame
  (world-map-scale design §5-§6), which remain the data authority until the
  geography source cutover replaces them with continent documents;
* one explicit :data:`TERRAIN` value built from those declarations, so every
  calculation reads frozen inputs rather than module globals; and
* the provider integration: the contrib ``WildernessMapProvider`` subclass,
  the live anchor-footprint snapshot from ``WILDERNESS_ENTRY_REGISTRY``, and
  thin wrappers that bind the snapshot for existing game callers.

Terrain, nominal claim and actual control stay separate layers: the rules
return a terrain region key and, alongside it, the coordinate-sensitive nominal
claim plus the border lines derived from the same ridge and river geometry.
``world.lore.nations`` keeps the effective-rule demographic targets. Nothing
here reads the database, a clock, or a random source.
"""

from elosern_map_core import terrain as core_terrain
from evennia.contrib.grid.wilderness.wilderness import WildernessMapProvider

from typeclasses.rooms import TerrainRoom
from world.lore.wilderness_regions import (
    CONTINENT_FRAME_CELLS,
    MAINLAND_BOUNDARY_KM,
    WILDERNESS_REGION_REGISTRY,
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
# water cell per column and ``border_river_row`` is that same cell.
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

#: The one explicit terrain snapshot the game binds its authored declarations
#: into. Every derived table and cache (column rows, waterway cells, search
#: boxes, national borders) belongs to this value, never to module state, so a
#: second snapshot can never reuse these results.
TERRAIN = core_terrain.TerrainDefinition(
    frame_cells=CONTINENT_FRAME_CELLS,
    mainland_boundary_km=MAINLAND_BOUNDARY_KM,
    forest_edge=NORTH_FOREST_EDGE,
    waterway_routes=WATERWAY_ROUTES,
    waterway_fords=WATERWAY_FORDS,
    border_river_key="border_river",
    ridge_base_x=_MOUNTAIN_RIDGE_BASE_X,
    ridge_period=_MOUNTAIN_RIDGE_PERIOD,
    ridge_step=_MOUNTAIN_RIDGE_STEP,
    ridge_min_x=_RIDGE_MIN_X,
    ridge_max_x=_RIDGE_MAX_X,
    ridge_north_limit=_RIDGE_NORTH_LIMIT_Y,
    ridge_passes=RIDGE_PASSES,
    coastal_y_max=_COASTAL_Y_MAX,
    mountain_corridor_half_width=_MOUNTAIN_CORRIDOR_HALF_WIDTH,
    region_flavors={
        key: region.terrain_flavor_zh
        for key, region in WILDERNESS_REGION_REGISTRY.items()
    },
)

#: Authored enumeration windows per region (superset of each region's cells).
REGION_SEARCH_BOXES = TERRAIN.region_search_boxes

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


# -- game wrappers over the explicit terrain snapshot ---------------------
# These bind the authored snapshot (and, for validity, the live footprint
# registry snapshot) that pure core functions cannot read themselves. They are
# the game provider surface the map callers and the contrib integration use.


def forest_edge_row(x: int) -> int:
    """The northern deep forest's first row in column ``x``."""
    return core_terrain.forest_edge_row(TERRAIN, x)


def border_river_row(x: int) -> int:
    """The border river's row in column ``x`` (or its derived extension)."""
    return core_terrain.border_river_row(TERRAIN, x)


def is_closed_ridge_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is an impassable summit-ridge/cliff cell."""
    return core_terrain.is_closed_ridge_cell(TERRAIN, coordinates)


def is_inland_water_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is impassable river water (a ford is not water)."""
    return core_terrain.is_inland_water_cell(TERRAIN, coordinates)


def is_land_cell(coordinates: tuple[int, int]) -> bool:
    """Whether the cell's centre lies inside the mainland polygon."""
    return core_terrain.is_land_cell(TERRAIN, coordinates)


def is_passable_terrain(coordinates: tuple[int, int]) -> bool:
    """Whether the cell is walkable ground (not a ridge wall or water)."""
    return core_terrain.is_passable_terrain(TERRAIN, coordinates)


def is_walkable_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is in-frame, mainland and passable on foot."""
    return core_terrain.is_walkable_cell(TERRAIN, coordinates)


def is_valid_wilderness_cell(coordinates: tuple[int, int]) -> bool:
    """The single wilderness-cell validity rule every consumer shares.

    In-frame, land-side, passable terrain, and not an anchor footprint cell of
    the live ``WILDERNESS_ENTRY_REGISTRY`` (point shapes contribute no
    footprint). The provider, the canonical destination resolver and the local
    map all read this one rule.
    """
    return core_terrain.is_valid_wilderness_cell(
        TERRAIN, _footprint_union(), coordinates
    )


def region_for_coordinates(x: int, y: int) -> str:
    """Return the terrain region key for ``(x, y)``."""
    return core_terrain.region_for_coordinates(TERRAIN, x, y)


def nominal_nation_for_coordinates(x: int, y: int) -> str:
    """Return the one nation that nominally claims ``(x, y)``."""
    return core_terrain.nominal_nation_for_coordinates(TERRAIN, x, y)


def national_borders() -> tuple[core_terrain.NationalBorder, ...]:
    """The displayed national borders, derived from the ridge and the river."""
    return TERRAIN.national_borders


def terrain_description(x: int, y: int) -> str:
    """Return one deterministic flavor variant for the region at ``(x, y)``."""
    return core_terrain.terrain_description(TERRAIN, x, y)


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
