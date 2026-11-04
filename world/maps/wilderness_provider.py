"""Wilderness terrain provider over the published continental geography.

Every authored input (frame, mainland boundary, classifier parameters,
waterways and fords, forest edge, ridge, passes, region prose and region scene
associations) lives in ``content/maps/continent.yaml`` and is loaded once into
an immutable :class:`world.maps.geography.GeographySnapshot`. This module is
the game-side provider wrapper: it binds that snapshot and the live wilderness
entry registry into the pure ``elosern_map_core.terrain`` rules, and adapts the
Evennia wilderness contrib (rooms, exits, gate locks).

Derived tables and caches belong to the snapshot's explicit
``TerrainDefinition`` or are keyed by the snapshot/registry identity, so a
reload or a second world can never reuse another world's classification.
"""

from evennia.contrib.grid.wilderness.wilderness import WildernessMapProvider

from elosern_map_core import terrain as core_terrain

from world.lore.wilderness_regions import regions
from typeclasses.rooms import TerrainRoom
from world.maps.room_art import wilderness_scene_identity
# Read the entry registry as a MODULE attribute at call time (never a
# from-import binding): a test rebinding world.lore.wilderness_entry.
# WILDERNESS_ENTRY_REGISTRY must be observed here (wilderness-map-provider
# delta: registry patches change validity without patching the provider).
from world.lore import wilderness_entry as _wilderness_entry_module

WILDERNESS_NAME = "elosern"

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

# Footprint cache. The published registry is a read view over one immutable
# settlement snapshot, so its identity (and the underlying mapping's) is the
# exact version: a republish or a rebind is a key miss, while a per-cell
# lookup costs one id() pair instead of hashing every entry object. The
# cached tuples RETAIN both objects, so their ids cannot be recycled behind
# the cache's back. A plain mapping (a documented test patch) still keys on
# its contents, which is the only cheap exact version it offers.
_FOOTPRINT_CACHE: dict[
    tuple[int, int] | tuple[tuple[str, object], ...],
    tuple[object, object, frozenset],
] = {}


def __getattr__(name: str):
    """Expose the scale and frame bounds as live projections of the snapshot.

    The merged wilderness-map-provider and webclient-local-map contracts name
    ``WILDERNESS_KM_PER_CELL``/``WILDERNESS_MAX_X``/``WILDERNESS_MAX_Y`` as
    module attributes read at build time. They are projections of the loaded
    continent document rather than authored copies, so a reload, a second
    world, or a test patch of the module attribute all stay consistent with
    what a consumer reads.
    """

    if name == "WILDERNESS_KM_PER_CELL":
        from world.maps.geography import current

        return current().cell_size_km
    if name == "WILDERNESS_MAX_X":
        from world.maps.geography import current

        return current().max_x
    if name == "WILDERNESS_MAX_Y":
        from world.maps.geography import current

        return current().max_y
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _footprint_union() -> frozenset:
    """Every anchor footprint cell in the live registry (point shapes: none)."""

    registry = _wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY
    read_value = getattr(registry, "_value", None)
    if read_value is not None:
        entries = read_value()
        key: tuple = (id(registry), id(entries))
    else:
        entries = registry
        key = tuple(entries.items())
    cached = _FOOTPRINT_CACHE.get(key)
    if cached is None:
        union = frozenset(
            cell for entry in entries.values() for cell in entry.footprint_cells
        )
        cached = (registry, entries, union)
        _FOOTPRINT_CACHE[key] = cached
        # Keep the cache bounded against long test histories (insertion order:
        # the entry just stored is the newest, never the first popped).
        while len(_FOOTPRINT_CACHE) > 8:
            _FOOTPRINT_CACHE.pop(next(iter(_FOOTPRINT_CACHE)))
    return cached[2]


def is_footprint_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is an anchor footprint cell of the live registry."""
    return coordinates in _footprint_union()


# -- game wrappers over the published terrain snapshot --------------------
# These bind the published snapshot (and, for validity, the live footprint
# registry snapshot) that pure core functions cannot read themselves. They are
# the game provider surface the map callers and the contrib integration use.


def terrain_definition() -> core_terrain.TerrainDefinition:
    """The published snapshot's explicit terrain definition."""

    from world.maps.geography import current

    return current().terrain


def region_search_boxes():
    """Each region's authored enumeration window (a superset of its cells)."""

    from world.maps.geography import current

    return current().region_search_boxes


def forest_edge_row(x: int) -> int:
    """The northern deep forest's first row in column ``x``."""
    return core_terrain.forest_edge_row(terrain_definition(), x)


def border_river_row(x: int) -> int:
    """The border river's row in column ``x`` (or its derived extension)."""
    return core_terrain.border_river_row(terrain_definition(), x)


def is_closed_ridge_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is an impassable summit-ridge/cliff cell."""
    return core_terrain.is_closed_ridge_cell(terrain_definition(), coordinates)


def is_inland_water_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is impassable river water (a ford is not water)."""
    return core_terrain.is_inland_water_cell(terrain_definition(), coordinates)


def is_land_cell(coordinates: tuple[int, int]) -> bool:
    """Whether the cell's centre lies inside the mainland polygon."""
    return core_terrain.is_land_cell(terrain_definition(), coordinates)


def is_passable_terrain(coordinates: tuple[int, int]) -> bool:
    """Whether the cell is walkable ground (not a ridge wall or water)."""
    return core_terrain.is_passable_terrain(terrain_definition(), coordinates)


def is_walkable_cell(coordinates: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is in-frame, mainland and passable on foot."""
    return core_terrain.is_walkable_cell(terrain_definition(), coordinates)


def is_valid_wilderness_cell(coordinates: tuple[int, int]) -> bool:
    """The single wilderness-cell validity rule every consumer shares.

    In-frame, land-side, passable terrain, and not an anchor footprint cell of
    the live ``WILDERNESS_ENTRY_REGISTRY`` (point shapes contribute no
    footprint). The provider, the canonical destination resolver and the local
    map all read this one rule.
    """
    return core_terrain.is_valid_wilderness_cell(
        terrain_definition(), _footprint_union(), coordinates
    )


def region_for_coordinates(x: int, y: int) -> str:
    """Return the terrain region key for ``(x, y)``."""
    return core_terrain.region_for_coordinates(terrain_definition(), x, y)


def sight_terrain_class(coordinates: tuple[int, int]) -> str:
    """The sight rulebook's terrain row for the region at ``coordinates``.

    Sight classifies terrain for visibility, which is not the travel-cost
    terrain class; the policy owns the join and here the provider merely
    delegates one published region key to it.
    """

    from world.rules.sight import sight_terrain_class as _row_for_region

    return _row_for_region(region_for_coordinates(*coordinates))


def nominal_nation_for_coordinates(x: int, y: int) -> str:
    """Return the one nation that nominally claims ``(x, y)``."""
    return core_terrain.nominal_nation_for_coordinates(terrain_definition(), x, y)


def national_borders() -> tuple[core_terrain.NationalBorder, ...]:
    """The displayed national borders, derived from the ridge and the river."""
    return terrain_definition().national_borders


def terrain_description(x: int, y: int) -> str:
    """Return one deterministic flavor variant for the region at ``(x, y)``."""
    return core_terrain.terrain_description(terrain_definition(), x, y)


class ElosernWildernessMapProvider(WildernessMapProvider):
    """Bounded one-kilometre wilderness frame over the published terrain model."""

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
        return regions()[region_for_coordinates(*coordinates)].display_name_zh

    def at_prepare_room(self, coordinates, caller, room):
        # D-3/unified-room-art-metadata: re-set EVERY scene fact unconditionally
        # on every call -- a TerrainRoom is pooled and reused across
        # coordinates, so a stale archetype, identity or room-art key from a
        # previous place would silently persist if these were not re-assigned.
        # The archetype is the authored region->scene association (a registered
        # scene key, never the raw terrain region key), the identity is the
        # CURRENT wilderness' name plus the current coordinates, and the
        # room-art key is cleared because wilderness declares none -- an
        # earlier place's key must never leak into another coordinate.
        wilderness = room.wilderness
        wilderness_name = getattr(wilderness, "key", None) or WILDERNESS_NAME
        region = region_for_coordinates(*coordinates)
        room.scene_archetype = regions()[region].scene_archetype
        room.scene_identity = wilderness_scene_identity(wilderness_name, *coordinates)
        room.room_art_key = None
        room.ndb.active_desc = terrain_description(*coordinates)
        # Population is never reconciled here: ordinary births belong to the
        # regional owner at its game-time boundaries, and the wilderness
        # contrib re-attaches already registered individuals by coordinate.
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
