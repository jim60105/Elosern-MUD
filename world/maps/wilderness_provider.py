"""Deterministic wilderness terrain model and map provider (map-wilderness)."""

from evennia.contrib.grid.wilderness.wilderness import WildernessMapProvider

from typeclasses.rooms import TerrainRoom
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY

# D-4: 10 km per wilderness cell, 224 cells per axis (0-indexed to 223).
# 224 * 10 km = 2,240 km per side; 2,240^2 = 5,017,600 km^2, within 0.35% of the
# stated ~5,000,000 km^2 continent area.
WILDERNESS_KM_PER_CELL = 10
WILDERNESS_MAX_X = 223
WILDERNESS_MAX_Y = 223

WILDERNESS_NAME = "elosern"

# D-1: seven rectangular bounds, checked top-to-bottom.
_MOUNTAIN_X = (100, 123)  # 24-column central band, full Y range
_NORTH_FOREST_Y_MIN = 190  # top 34 rows, full X range -- checked first, dominates the mountain band
_COASTAL_Y_MAX = 40  # southern strip, both sides of the mountains
_HIGHLAND_Y_MIN = 150  # west side only, between the coast and the northern forest


def region_for_coordinates(x: int, y: int) -> str:
    """Return the terrain region key for ``(x, y)``.

    Pure integer partition over the two coordinates alone -- no database read,
    no randomness, no wall-clock input. Same input always returns the same key.
    """

    if y >= _NORTH_FOREST_Y_MIN:
        return "north_deep_forest"
    if _MOUNTAIN_X[0] <= x <= _MOUNTAIN_X[1]:
        return "central_mountains"
    if x > _MOUNTAIN_X[1]:  # east of the mountains
        return "southeast_coast" if y <= _COASTAL_Y_MAX else "eastern_plains"
    # x < _MOUNTAIN_X[0] -- west of the mountains
    if y <= _COASTAL_Y_MAX:
        return "southwest_coast"
    if y >= _HIGHLAND_Y_MIN:
        return "northwest_highland_forest"
    return "western_hills_valleys"


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
    """Bounded 224x224 wilderness map at 10 km/cell over the deterministic terrain model."""

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
        x, y = coordinates
        return 0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y

    def get_location_name(self, coordinates):
        return WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh

    def at_prepare_room(self, coordinates, caller, room):
        # D-3: re-set unconditionally on every call -- a TerrainRoom is pooled
        # and reused across coordinates, so a stale value from a previous
        # coordinate would silently persist if this were not re-assigned.
        room.scene_archetype = region_for_coordinates(*coordinates)
        room.ndb.active_desc = terrain_description(*coordinates)
        # wilderness-monster-population D-4: ensure the deterministic monster
        # population for this coordinate whenever a wilderness script is
        # attached. Deferred import breaks the load-time cycle: this module is
        # imported by wilderness_population, which reads region_for_coordinates
        # from here.
        wilderness = room.wilderness
        if wilderness is not None:
            from world.maps.wilderness_population import ensure_population

            ensure_population(wilderness, coordinates)
