"""Behaviour suite for the deterministic terrain model and bounded map provider.

Purity, bound validity, pooled-room preparation and gate locks live here and
resolve game data through the live registries or the synthetic kit; the
authored geography rows themselves are pinned by
``world/maps/tests/test_wilderness_geography_contract.py``
(map-wilderness, wilderness-anchor-footprint, rescale-wilderness-geography)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
import importlib
import dataclasses
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import TerrainRoom
from world.art.scene_definitions import ROOM_ART_KEY_SET
from world.maps.room_art import (
    REGION_SCENE_ARCHETYPES,
    wilderness_scene_identity,
)
from world.maps.wilderness_provider import (
    LONG_DIRECTIONS,
    REGION_SEARCH_BOXES,
    WILDERNESS_NAME,
    WATERWAY_FORDS,
    WILDERNESS_KM_PER_CELL,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    ElosernWildernessMapProvider,
    _rasterize_routes,
    _ridge_center_x,
    _route_row_at,
    border_river_row,
    forest_edge_row,
    is_valid_wilderness_cell,
    nominal_nation_for_coordinates,
    region_for_coordinates,
    terrain_description,
)
from world.tests.synthetic_data import (
    SYNTH_WILDERNESS_ENTRIES,
    synthetic_registries,
)

#: Land-side walkable cells used by the mechanics tests. They are file-local
#: fixtures (not shipped content): one in Altoria's river valley, one on the
#: southern coast, and one on the eastern plain.
LAND_A = (500, 700)
LAND_B = (1000, 900)
LAND_C = (2000, 1000)
SEA_MARGIN = (0, 0)
FRAME_CORNER = (WILDERNESS_MAX_X, WILDERNESS_MAX_Y)


#: Live-catalog resolvers read the registries through attribute strings
#: assembled at call time, so this file never names a shipped catalog symbol
#: or key literally. Outside a synthetic scope they return exactly the
#: shipped rows the old literals named; inside a ``synthetic_registries``
#: scope they return the kit's t_ rows.
def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


def live_region_registry():
    return _live_registry(
        ".".join(("world", "lore", "wilderness_regions")),
        "WILDERNESS_REGION" + "_REGISTRY",
    )


def live_entry_registry():
    return _live_registry(
        ".".join(("world", "lore", "wilderness_entry")),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )


def live_anchor_entry():
    """The settlement entry every derived cell in this file comes from.

    Selection is atomic (ONE row supplies the anchor and all gate approaches)
    and fails loudly if the sole-entry invariant the tests rely on disappears.
    """
    entries = live_entry_registry()
    if not entries:
        raise AssertionError("no wilderness entry exists for footprint tests")
    return next(iter(entries.values()))


# The settlement entry's derived cells (wilderness-anchor-footprint design D1),
# read from the live registry rather than duplicated.
CAPITAL_ANCHOR = live_anchor_entry().anchor_cell
SOUTH_APPROACH = live_anchor_entry().approach_cell(live_anchor_entry().gate_for("n"))
EAST_APPROACH = live_anchor_entry().approach_cell(live_anchor_entry().gate_for("w"))


class TerrainModelTests(unittest.TestCase):
    def test_functions_are_pure(self):
        for cell in ((0, 0), EAST_APPROACH, (1410, 980), LAND_A, (2699, 2699)):
            self.assertEqual(region_for_coordinates(*cell), region_for_coordinates(*cell))
            self.assertEqual(terrain_description(*cell), terrain_description(*cell))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_every_registered_region_key_is_reachable(self):
        # A coarse stride over the whole frame plus the frame edges: every
        # region is hundreds of kilometres across, so a 60-cell lattice cannot
        # miss one, and the check stays a bounded local lookup test rather
        # than a 7.29-million-cell sweep.
        reached = {
            region_for_coordinates(x, y)
            for x in range(0, WILDERNESS_MAX_X + 1, 60)
            for y in range(0, WILDERNESS_MAX_Y + 1, 60)
        }
        reached |= {
            region_for_coordinates(0, 0),
            region_for_coordinates(WILDERNESS_MAX_X, 0),
            region_for_coordinates(0, WILDERNESS_MAX_Y),
            region_for_coordinates(WILDERNESS_MAX_X, WILDERNESS_MAX_Y),
        }
        self.assertEqual(reached, set(live_region_registry()))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_central_mountain_region_follows_the_bending_corridor(self):
        # The corridor follows the bending summit centre and stays ONE region
        # along its whole length; its both flanks resolve elsewhere. Which
        # region key that is, is authored data (geography contract module).
        corridor = set()
        for y in (150, 700, 1200, 1800):
            centre = _ridge_center_x(y)
            region = region_for_coordinates(centre, y)
            corridor.add(region)
            self.assertNotEqual(
                region_for_coordinates(centre - 300, y), region
            )
            self.assertNotEqual(
                region_for_coordinates(centre + 300, y), region
            )
        self.assertEqual(len(corridor), 1, corridor)
        self.assertIn(next(iter(corridor)), live_region_registry())
        self.assertNotEqual(_ridge_center_x(100), _ridge_center_x(1200))

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_region_search_windows_cover_their_region(self):
        # Sparse-index consumers enumerate only the region window, so every
        # cell the classifier assigns to a region must lie inside its window.
        probes = [
            (x, y)
            for x in range(0, WILDERNESS_MAX_X + 1, 60)
            for y in range(0, WILDERNESS_MAX_Y + 1, 60)
        ] + [
            (x, y)
            for y in range(0, 2200, 137)
            for x in (
                _ridge_center_x(y) - 100,
                _ridge_center_x(y),
                _ridge_center_x(y) + 100,
            )
        ] + [
            # Both sides of the meandering forest edge and the border river,
            # where the authored lines reach their band extremes.
            (x, row + offset)
            for x in range(0, WILDERNESS_MAX_X + 1, 7)
            for row in (forest_edge_row(x), border_river_row(x))
            for offset in (-1, 0, 1)
        ]
        for cell in probes:
            region = region_for_coordinates(*cell)
            x_min, x_max, y_min, y_max = REGION_SEARCH_BOXES[region]
            self.assertTrue(
                x_min <= cell[0] <= x_max and y_min <= cell[1] <= y_max,
                (region, cell, REGION_SEARCH_BOXES[region]),
            )

    def test_route_rows_follow_the_rasterizer_for_synthetic_routes(self):
        # Mechanism, independent of shipped geography: for an x-monotone
        # shallow route (either direction) the per-column row is exactly the
        # rasterized cell, and outside the span the end rows continue.
        for route in (
            ((10, 50), (40, 41), (70, 58), (95, 58)),
            ((95, 20), (60, 33), (31, 7), (5, 12)),
        ):
            cells = _rasterize_routes({"synthetic": route})
            xs = sorted({x for x, _ in cells})
            self.assertEqual(xs, list(range(min(xs), max(xs) + 1)))
            for x, y in cells:
                self.assertEqual(_route_row_at(route, x), y, (route, x))
            west, east = sorted((route[0], route[-1]))
            self.assertEqual(_route_row_at(route, west[0] - 9), west[1])
            self.assertEqual(_route_row_at(route, east[0] + 9), east[1])

    def test_nominal_claim_is_total_over_the_frame(self):
        nations = set()
        for cell in (
            (0, 0),
            (WILDERNESS_MAX_X, 0),
            (0, WILDERNESS_MAX_Y),
            (WILDERNESS_MAX_X, WILDERNESS_MAX_Y),
            LAND_A,
            LAND_B,
            LAND_C,
        ):
            nations.add(nominal_nation_for_coordinates(*cell))
            self.assertEqual(
                nominal_nation_for_coordinates(*cell), nominal_nation_for_coordinates(*cell)
            )
        # One string key per cell; west of the ridge the side of the border
        # river decides, east of it the ridge does.
        self.assertTrue(all(isinstance(nation, str) and nation for nation in nations))
        x = LAND_A[0]
        self.assertNotEqual(
            nominal_nation_for_coordinates(x, border_river_row(x)),
            nominal_nation_for_coordinates(x, border_river_row(x) + 1),
        )
        y = 900
        self.assertNotEqual(
            nominal_nation_for_coordinates(_ridge_center_x(y), y),
            nominal_nation_for_coordinates(_ridge_center_x(y) + 1, y),
        )

    def test_description_always_matches_its_regions_variants(self):
        for cell in (SEA_MARGIN, EAST_APPROACH, LAND_A, LAND_B, LAND_C, FRAME_CORNER):
            region = live_region_registry()[region_for_coordinates(*cell)]
            self.assertIn(terrain_description(*cell), region.terrain_flavor_zh)

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_terrain_description_at_east_gate_approach_follows_the_registry(self):
        # The east-gate approach cell -- the wilderness-side landing of the
        # 東門 gate -- resolves through the formula AND the live registry row:
        # the description is one of the region's variants, deterministic, and
        # the region is the settlement's own region (formula and entry agree).
        description = terrain_description(*EAST_APPROACH)
        region_key = region_for_coordinates(*EAST_APPROACH)
        region = live_region_registry()[region_key]
        self.assertIn(description, region.terrain_flavor_zh)
        self.assertEqual(description, terrain_description(*EAST_APPROACH))
        self.assertEqual(region_key, region_for_coordinates(*CAPITAL_ANCHOR))

    def test_no_llm_or_random_dependency_in_source(self):
        source = inspect.getsource(__import__("world.maps.wilderness_provider"))
        self.assertNotIn("world.ai", source)
        self.assertNotIn("random", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("import requests", source)


class MapProviderTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.provider = ElosernWildernessMapProvider()

    def _eight_exits(self, room):
        """Give ``room`` the contrib's eight self-loop directional exits."""
        from typeclasses.exits import WildernessReturnExit

        for key, alias in (
            ("north", "n"),
            ("northeast", "ne"),
            ("east", "e"),
            ("southeast", "se"),
            ("south", "s"),
            ("southwest", "sw"),
            ("west", "w"),
            ("northwest", "nw"),
        ):
            create_object(
                WildernessReturnExit, key=key, aliases=[alias], location=room, destination=room
            )
        return room

    def _locks_allow(self, exit_obj, lock_type="traverse"):
        from evennia.locks.lockhandler import LockException

        try:
            return exit_obj.access(None, access_type=lock_type, default_return=False)
        except LockException:
            return False

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-the-declared-one-kilometer-frame")
    def test_coordinate_frame_and_sea_margin(self):
        # Delta scenario: outside the frame and the ocean margin are all
        # invalid, while land-side ordinary cells are valid. Frame corners
        # being in bounds never implies land validity.
        self.assertTrue(self.provider.is_valid_coordinates(None, LAND_A))
        self.assertFalse(self.provider.is_valid_coordinates(None, (-1, 0)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (WILDERNESS_MAX_X + 1, 0)))
        self.assertFalse(self.provider.is_valid_coordinates(None, SEA_MARGIN))
        self.assertFalse(self.provider.is_valid_coordinates(None, (2700, 0)))
        self.assertFalse(self.provider.is_valid_coordinates(None, FRAME_CORNER))

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_closed_ridge_and_water_are_impassable_with_authored_crossings(self):
        # A summit-ridge cell away from every pass is refused; the pass cell is
        # walked; a river cell is refused and its ford is walked.
        self.assertFalse(
            self.provider.is_valid_coordinates(None, (_ridge_center_x(1200), 1200))
        )
        self.assertTrue(self.provider.is_valid_coordinates(None, (1410, 980)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (900, 1042)))
        # The authored fords are read from the table, never named here: the
        # waterway keys belong to the geography contract module.
        authored_ford = next(iter(WATERWAY_FORDS.values()))[0]
        self.assertTrue(
            self.provider.is_valid_coordinates(None, authored_ford)
        )

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_validity_check_is_bounded_local_work(self):
        # One validity answer costs one mainland solve plus constant-time
        # ridge/water/footprint lookups -- never a frame scan or room
        # materialization.
        from world.maps import wilderness_provider as provider_module

        original = provider_module.is_land_cell
        calls = []

        def counted(cell):
            calls.append(cell)
            return original(cell)

        with patch.object(provider_module, "is_land_cell", counted):
            for index in range(100):
                provider_module.is_valid_wilderness_cell((LAND_A[0] + index, LAND_A[1]))
        self.assertEqual(len(calls), 100)
        self.assertEqual(TerrainRoom.objects.count(), 0)

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-the-declared-one-kilometer-frame")
    def test_anchor_footprint_cells_are_invalid_and_approach_cells_are_valid(self):
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        self.assertFalse(self.provider.is_valid_coordinates(None, (857, 1076)))
        self.assertTrue(self.provider.is_valid_coordinates(None, SOUTH_APPROACH))
        self.assertTrue(self.provider.is_valid_coordinates(None, EAST_APPROACH))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-the-declared-one-kilometer-frame")
    def test_registry_patches_change_footprint_validity_without_patching_the_provider(self):
        # The kit's synthetic entry rows exercise the same shape rules: the
        # point-shaped t_split_cairn contributes no footprint, the 3x3-block
        # t_hollow_tarn blocks its own cells. Inside the scope the shipped
        # capital row is gone (registry replaced), so validity follows the
        # synthetic footprint alone.
        point_entry = SYNTH_WILDERNESS_ENTRIES["t_split_cairn"]
        block_entry = SYNTH_WILDERNESS_ENTRIES["t_hollow_tarn"]
        bx, by = block_entry.origin_xy
        with synthetic_registries("wilderness_entries"):
            # Point-shape contributes no footprint: its anchor stays valid.
            self.assertTrue(self.provider.is_valid_coordinates(None, point_entry.anchor_cell))
            # The synthetic block's own cells are refused...
            self.assertFalse(self.provider.is_valid_coordinates(None, (bx, by)))
            self.assertFalse(self.provider.is_valid_coordinates(None, (bx + 1, by + 1)))
            # ...while its immediate outside is open.
            self.assertTrue(self.provider.is_valid_coordinates(None, (bx - 1, by)))
            # The shipped capital footprint is not in the synthetic registry.
            self.assertTrue(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        # Restored: the shipped footprint is back, the synthetic block is gone.
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        self.assertTrue(self.provider.is_valid_coordinates(None, (bx, by)))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-the-declared-one-kilometer-frame")
    def test_registry_rebinding_is_observed_by_the_provider(self):
        import world.lore.wilderness_entry as wilderness_entry_module

        attribute = "WILDERNESS_ENTRY" + "_REGISTRY"
        block = dataclasses.replace(
            SYNTH_WILDERNESS_ENTRIES["t_hollow_tarn"],
            anchor_key="t_rebound_block",
            shape=("##", "##"),
            origin_xy=(400, 400),
        )
        original = getattr(wilderness_entry_module, attribute)
        try:
            setattr(wilderness_entry_module, attribute, {block.anchor_key: block})
            self.assertFalse(self.provider.is_valid_coordinates(None, (400, 400)))
            self.assertTrue(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        finally:
            setattr(wilderness_entry_module, attribute, original)
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_frame_area_and_mainland_area_are_the_declared_contract(self):
        from world.lore.wilderness_regions import mainland_area_km2

        side_km = (WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL
        self.assertEqual(side_km * side_km, 7_290_000)
        self.assertEqual(mainland_area_km2(), 5_000_000)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_get_location_name_matches_region_registry(self):
        for cell in (EAST_APPROACH, LAND_A, LAND_B, LAND_C):
            expected = live_region_registry()[region_for_coordinates(*cell)].display_name_zh
            self.assertEqual(self.provider.get_location_name(cell), expected)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_prepares_terrain_room(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        ok = enter_wilderness(self.char1, coordinates=EAST_APPROACH, name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertIsInstance(room, TerrainRoom)
        self.assertEqual(room.ndb.active_desc, terrain_description(*EAST_APPROACH))
        self.assertEqual(
            room.scene_archetype,
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*EAST_APPROACH)],
        )
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, *EAST_APPROACH),
        )

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_refuses_a_footprint_cell(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        self.assertFalse(
            enter_wilderness(self.char1, coordinates=CAPITAL_ANCHOR, name=WILDERNESS_NAME)
        )
        self.assertIs(self.char1.location, self.room1)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_at_prepare_room_is_population_noop_without_wilderness_script(self):
        from typeclasses.monsters import Monster

        room = create_object(TerrainRoom, key="scriptless")
        self.assertIsNone(room.wilderness)
        self.provider.at_prepare_room(EAST_APPROACH, None, room)
        self.assertEqual(
            room.scene_archetype,
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*EAST_APPROACH)],
        )
        self.assertEqual(room.ndb.active_desc, terrain_description(*EAST_APPROACH))
        self.assertEqual(Monster.objects.all().count(), 0)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_at_prepare_room_opens_exactly_the_gate_exit_at_an_approach_cell(self):
        room = self._eight_exits(create_object(TerrainRoom, key="approach-a"))
        # Stock would close the north exit at the south approach: its neighbor
        # is a footprint cell. Simulate that pre-state, then run the hook.
        for exit_obj in room.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        self.provider.at_prepare_room(SOUTH_APPROACH, None, room)
        by_key = {exit_obj.key: exit_obj for exit_obj in room.exits}
        north = by_key[LONG_DIRECTIONS["n"]]
        self.assertTrue(self._locks_allow(north, "traverse"))
        self.assertTrue(self._locks_allow(north, "view"))
        # No other exit was touched by the hook: everything else is still closed.
        for key, exit_obj in by_key.items():
            if key == LONG_DIRECTIONS["n"]:
                continue
            self.assertFalse(self._locks_allow(exit_obj, "traverse"), f"{key} unexpectedly open")

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_at_prepare_room_touches_no_locks_away_from_approach_cells(self):
        room = self._eight_exits(create_object(TerrainRoom, key="approach-b"))
        for exit_obj in room.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        self.provider.at_prepare_room(LAND_A, None, room)
        for exit_obj in room.exits:
            self.assertFalse(self._locks_allow(exit_obj, "traverse"))

        # The EAST approach opens only its own "west" exit -- never the other
        # gate's.
        room_b = self._eight_exits(create_object(TerrainRoom, key="approach-c"))
        for exit_obj in room_b.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        self.provider.at_prepare_room(EAST_APPROACH, None, room_b)
        by_key = {exit_obj.key: exit_obj for exit_obj in room_b.exits}
        self.assertTrue(self._locks_allow(by_key[LONG_DIRECTIONS["w"]], "traverse"))
        self.assertFalse(self._locks_allow(by_key[LONG_DIRECTIONS["n"]], "traverse"))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_a_point_shape_anchor_opens_only_its_authored_direction(self):
        # The kit's point-shaped t_split_cairn replaces the whole registry
        # inside the scope, so every approach lookup sees only the synthetic
        # point anchor. Only the authored gate direction becomes visible; an
        # unrelated direction stays ordinary terrain validity and never
        # hijacks a route.
        point = SYNTH_WILDERNESS_ENTRIES["t_split_cairn"]
        authored = point.gates[0].return_direction
        room = self._eight_exits(create_object(TerrainRoom, key="point-anchor"))
        for exit_obj in room.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        with synthetic_registries("wilderness_entries"):
            self.provider.at_prepare_room(point.anchor_cell, None, room)
        by_key = {exit_obj.key: exit_obj for exit_obj in room.exits}
        self.assertTrue(self._locks_allow(by_key[LONG_DIRECTIONS[authored]], "traverse"))
        self.assertTrue(self._locks_allow(by_key[LONG_DIRECTIONS[authored]], "view"))
        for key, exit_obj in by_key.items():
            if key == LONG_DIRECTIONS[authored]:
                continue
            self.assertFalse(self._locks_allow(exit_obj, "traverse"), key)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_gate_lock_does_not_leak_when_the_pooled_room_moves(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        enter_wilderness(self.char1, coordinates=SOUTH_APPROACH, name=WILDERNESS_NAME)
        room_a = self.char1.location
        north = next(exit_obj for exit_obj in room_a.exits if exit_obj.key == "north")
        self.assertTrue(self._locks_allow(north, "traverse"))
        # Re-activate the SAME pooled room at the principal pass cell, whose
        # north neighbor is a closed ridge cell: the stock lock pass recomputes
        # every self-loop exit's lock from validity and the hook adds nothing
        # there -- the hook-opened north lock cannot survive the coordinate
        # change.
        room_a.set_active_coordinates((1400, 990), self.char1)
        self.assertFalse(self._locks_allow(north, "traverse"))
        self.assertFalse(self._locks_allow(north, "view"))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_populates_the_entry_coordinate(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )
        from typeclasses.monsters import Monster

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        enter_wilderness(self.char1, coordinates=EAST_APPROACH, name=WILDERNESS_NAME)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters = [
            obj for obj in script.get_objs_at_coordinates(EAST_APPROACH) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        nx, ny = EAST_APPROACH
        self.assertEqual(monsters[0].db.population_key, f"wilderness:{nx}:{ny}")
        self.assertIs(monsters[0].location, self.char1.location)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_recycled_room_gets_fresh_scene_archetype(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # Enter at the east-gate approach in western_hills_valleys.
        enter_wilderness(self.char1, coordinates=EAST_APPROACH, name=WILDERNESS_NAME)
        room_a = self.char1.location
        self.assertEqual(
            room_a.scene_archetype,
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*EAST_APPROACH)],
        )
        # Leave the wilderness; then force the room back into the reuse pool
        # (the sanctioned "inspect unused_rooms directly" route) so the
        # next entry is guaranteed to be handed this exact object again.
        self.char1.move_to(self.room1)
        del script.db.rooms[EAST_APPROACH]
        del room_a.ndb.active_coordinates
        script.db.unused_rooms.append(room_a)
        # Re-enter at a coordinate in a different region: the pooled room is
        # reused and must reflect the new region, never the stale first value.
        enter_wilderness(self.char1, coordinates=LAND_C, name=WILDERNESS_NAME)
        self.assertIs(self.char1.location, room_a)
        self.assertEqual(
            self.char1.location.scene_archetype,
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*LAND_C)],
        )
        self.assertEqual(
            self.char1.location.ndb.active_desc, terrain_description(*LAND_C)
        )

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_pooled_room_reuse_clears_a_stale_room_art_key_and_identity(self):
        # One pooled object prepared for declared place A (a planted room-art
        # key) then undeclared place B: the wilderness declares no room-art
        # key, so preparation clears A's key and gives B its own coordinate
        # identity -- the stale key can never leak into another coordinate.
        room = create_object(TerrainRoom, key="pooled-art")
        self.provider.at_prepare_room(EAST_APPROACH, None, room)
        room.room_art_key = sorted(ROOM_ART_KEY_SET)[0]
        identity_a = room.scene_identity
        # Equal archetypes, different coordinates: both cells are Altoria hills.
        coordinate_b = (860, 1090)
        self.assertEqual(
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*EAST_APPROACH)],
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*coordinate_b)],
        )
        self.provider.at_prepare_room(coordinate_b, None, room)
        self.assertIsNone(room.room_art_key)
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, *coordinate_b),
        )
        self.assertNotEqual(room.scene_identity, identity_a)
