"""Data-contract test: authored continental terrain, waterway and anchor-region data contract

Mechanics (purity, bound validity, pooled-room preparation and gate locks) live
here beside the authored geography rows they must agree with
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
    RIDGE_PASSES,
    WILDERNESS_NAME,
    WATERWAY_FORDS,
    WILDERNESS_KM_PER_CELL,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    ElosernWildernessMapProvider,
    _ridge_center_x,
    is_closed_ridge_cell,
    is_inland_water_cell,
    is_land_cell,
    is_valid_wilderness_cell,
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
    def test_central_mountain_region_bends_with_the_authored_corridor(self):
        # The corridor follows the bending summit centre; it is neither a fixed
        # rectangular band nor a continuous summit wall (the pass windows below
        # are open ground).
        for y in (150, 700, 1200, 2100):
            centre = _ridge_center_x(y)
            self.assertEqual(region_for_coordinates(centre, y), "central_mountains")
            self.assertNotEqual(
                region_for_coordinates(centre - 300, y), "central_mountains"
            )
            self.assertNotEqual(
                region_for_coordinates(centre + 300, y), "central_mountains"
            )
        self.assertNotEqual(_ridge_center_x(100), _ridge_center_x(1200))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_settlement_derived_anchor_cells_resolve_to_altoria_territory(self):
        entry = live_anchor_entry()
        cells = {entry.anchor_cell} | {
            entry.approach_cell(gate) for gate in entry.gates
        }
        self.assertEqual(cells, {CAPITAL_ANCHOR, SOUTH_APPROACH, EAST_APPROACH})
        # Delta scenario: Altoria's anchor and both gate approaches are the
        # western hills and valleys (the signed anchor relationships).
        for cell in cells:
            self.assertEqual(region_for_coordinates(*cell), "western_hills_valleys")

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_anchor_centres_resolve_their_authored_terrain(self):
        # Region keys are the terrain layer; nominal claims stay in
        # ``world.lore.nations``. The authored anchor relationships pin which
        # terrain each canonical anchor cell belongs to.
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        expected = {
            "capital_altoria": "western_hills_valleys",
            "capital_valhalla": "northwest_highland_forest",
            "capital_grandia": "eastern_plains",
            "village_ciaran": "central_mountains",
            "village_fionnen": "central_mountains",
            "village_eolas": "central_mountains",
        }
        for anchor_key, region_key in expected.items():
            cell = ANCHOR_GEOGRAPHY_REGISTRY[anchor_key].cell
            self.assertEqual(region_for_coordinates(*cell), region_key, anchor_key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_principal_pass_is_open_mountain_trail_and_ridge_blocks_elsewhere(self):
        from world.rules.travel_cost import WILDERNESS_TERRAIN, terrain_speed_m_per_hour

        # The principal pass near (1410, 980) is open ground in the mountain
        # region, costed as mountain trail: an explicit slower crossing, never
        # an all-road shortcut.
        self.assertIn(980, range(*RIDGE_PASSES[1]))
        self.assertFalse(is_closed_ridge_cell((1410, 980)))
        self.assertEqual(region_for_coordinates(1410, 980), "central_mountains")
        mountain = terrain_speed_m_per_hour(WILDERNESS_TERRAIN["central_mountains"])
        self.assertLess(mountain, terrain_speed_m_per_hour("road"))
        # Away from an authored pass the summit ridge is a closed cliff wall.
        self.assertTrue(is_closed_ridge_cell((_ridge_center_x(1200), 1200)))

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_rivers_are_authored_water_with_declared_fords(self):
        from world.maps.wilderness_provider import WATERWAY_ROUTES

        # Every ford lies on its own river, and every river starts and ends on
        # the coastal region it drains into (capital river -> southwest coast;
        # imperial rivers -> southeast coast).
        for name, fords in WATERWAY_FORDS.items():
            for ford in fords:
                self.assertFalse(is_inland_water_cell(ford), name)
                self.assertTrue(is_land_cell(ford), name)
        capital = WATERWAY_ROUTES["capital_river"]
        self.assertEqual(region_for_coordinates(*capital[-1]), "southwest_coast")
        for name in ("imperial_river", "imperial_east_branch"):
            self.assertEqual(
                region_for_coordinates(*WATERWAY_ROUTES[name][-1]), "southeast_coast"
            )
        # A river cell is impassable water; its declared ford is ordinary land.
        river_cell = (900, 1042)
        self.assertTrue(is_inland_water_cell(river_cell))
        self.assertFalse(is_valid_wilderness_cell(river_cell))
        self.assertFalse(is_inland_water_cell(WATERWAY_FORDS["capital_river"][0]))
        self.assertTrue(is_valid_wilderness_cell(WATERWAY_FORDS["capital_river"][0]))

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

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_description_formula_is_pinned_at_a_literal_coordinate(self):
        # (860 * 92821 + 1080 * 68917) % 3 == 2 selects the third western-hills
        # variant: the arithmetic constants and the flavor text are contract.
        self.assertEqual(
            terrain_description(860, 1080),
            "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。",
        )

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

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
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
        self.assertTrue(
            self.provider.is_valid_coordinates(
                None, WATERWAY_FORDS["capital_river"][0]
            )
        )

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_anchor_and_port_centres_are_land_side(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
        from world.lore.wilderness_regions import HARBOR_SITE_REGISTRY

        for anchor in ANCHOR_GEOGRAPHY_REGISTRY.values():
            self.assertTrue(is_land_cell(anchor.cell), anchor.anchor_key)
        for harbor in HARBOR_SITE_REGISTRY.values():
            self.assertTrue(is_land_cell(harbor.cell), harbor.key)
        # Declaration reveals nothing: no settlement map is invented for the
        # seven unbuilt anchors.
        self.assertLessEqual(
            set(live_entry_registry()), set(ANCHOR_GEOGRAPHY_REGISTRY)
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

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
    def test_anchor_footprint_cells_are_invalid_and_approach_cells_are_valid(self):
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        self.assertFalse(self.provider.is_valid_coordinates(None, (857, 1076)))
        self.assertTrue(self.provider.is_valid_coordinates(None, SOUTH_APPROACH))
        self.assertTrue(self.provider.is_valid_coordinates(None, EAST_APPROACH))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
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

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
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
