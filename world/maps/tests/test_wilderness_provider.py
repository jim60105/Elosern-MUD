"""Tests for the deterministic terrain model and bounded map provider (map-wilderness,
wilderness-anchor-footprint)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import TerrainRoom
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.maps.wilderness_provider import (
    LONG_DIRECTIONS,
    WILDERNESS_KM_PER_CELL,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
    terrain_description,
)

# The shipped entry's derived cells (wilderness-anchor-footprint design D1).
CAPITAL_ANCHOR = (60, 100)
SOUTH_APPROACH = (60, 97)
NORTH_APPROACH = (60, 103)


class TerrainModelTests(unittest.TestCase):
    def test_functions_are_pure(self):
        for x, y in ((0, 0), (60, 103), (123, 189), (223, 223)):
            self.assertEqual(region_for_coordinates(x, y), region_for_coordinates(x, y))
            self.assertEqual(terrain_description(x, y), terrain_description(x, y))

    def test_all_seven_region_keys_are_reachable(self):
        reached = set()
        for x in range(WILDERNESS_MAX_X + 1):
            for y in range(WILDERNESS_MAX_Y + 1):
                reached.add(region_for_coordinates(x, y))
        self.assertEqual(reached, set(WILDERNESS_REGION_REGISTRY))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_central_mountain_band_spans_full_y(self):
        for x in (100, 123):
            self.assertEqual(region_for_coordinates(x, 0), "central_mountains")
            self.assertEqual(region_for_coordinates(x, 149), "central_mountains")
            self.assertEqual(region_for_coordinates(x, 189), "central_mountains")

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_capital_altoria_derived_anchor_cells_resolve_to_western_hills_valleys(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        cells = {entry.anchor_cell} | {
            entry.approach_cell(gate) for gate in entry.gates
        }
        self.assertEqual(cells, {CAPITAL_ANCHOR, SOUTH_APPROACH, NORTH_APPROACH})
        for x, y in cells:
            self.assertEqual(region_for_coordinates(x, y), "western_hills_valleys")

    def test_description_always_matches_its_regions_variants(self):
        for x, y in ((0, 0), (60, 103), (111, 50), (200, 200), (223, 223)):
            region = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)]
            self.assertIn(terrain_description(x, y), region.terrain_flavor_zh)

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_literal_pin_for_terrain_description_at_north_gate_approach(self):
        # The north-gate approach cell -- the wilderness-side landing of the
        # 北門 gate -- pins the formula constants and registry text together.
        self.assertEqual(
            terrain_description(*NORTH_APPROACH),
            "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
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

    def test_coordinate_bounds(self):
        self.assertTrue(self.provider.is_valid_coordinates(None, (0, 0)))
        self.assertTrue(self.provider.is_valid_coordinates(None, (223, 223)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (-1, 0)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (224, 0)))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
    def test_anchor_footprint_cells_are_invalid_and_approach_cells_are_valid(self):
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        self.assertFalse(self.provider.is_valid_coordinates(None, (58, 98)))
        self.assertTrue(self.provider.is_valid_coordinates(None, SOUTH_APPROACH))
        self.assertTrue(self.provider.is_valid_coordinates(None, NORTH_APPROACH))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
    def test_registry_patches_change_footprint_validity_without_patching_the_provider(self):
        from world.lore.wilderness_entry import (
            WILDERNESS_ENTRY_REGISTRY,
            WildernessEntryPoint,
            WildernessGate,
        )

        gate = WildernessGate("n", (2, 0), "capital_altoria")
        point = WildernessEntryPoint("capital_altoria", ("#",), (120, 120), (gate,))
        block = WildernessEntryPoint(
            "capital_altoria", ("##", "##"), (200, 200), (gate,)
        )
        with patch.dict(WILDERNESS_ENTRY_REGISTRY, {"capital_altoria": point}):
            # Point-shape contributes no footprint: its anchor stays valid.
            self.assertTrue(self.provider.is_valid_coordinates(None, (120, 120)))
            self.assertTrue(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        with patch.dict(WILDERNESS_ENTRY_REGISTRY, {"capital_altoria": block}):
            self.assertFalse(self.provider.is_valid_coordinates(None, (200, 200)))
            self.assertFalse(self.provider.is_valid_coordinates(None, (201, 201)))
            self.assertTrue(self.provider.is_valid_coordinates(None, (199, 200)))
        # Restored: the shipped footprint is back.
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        self.assertTrue(self.provider.is_valid_coordinates(None, (200, 200)))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
    def test_registry_rebinding_is_observed_by_the_provider(self):
        import world.lore.wilderness_entry as wilderness_entry_module
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate

        gate = WildernessGate("n", (2, 0), "capital_altoria")
        block = WildernessEntryPoint("capital_altoria", ("##", "##"), (150, 150), (gate,))
        original = wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY
        try:
            wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY = {"capital_altoria": block}
            self.assertFalse(self.provider.is_valid_coordinates(None, (150, 150)))
            self.assertTrue(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))
        finally:
            wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY = original
        self.assertFalse(self.provider.is_valid_coordinates(None, CAPITAL_ANCHOR))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_bound_area_matches_continent_size(self):
        side_km = (WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL
        area = side_km * side_km
        self.assertAlmostEqual(area, 5_000_000, delta=5_000_000 * 0.01)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_get_location_name_matches_region_registry(self):
        for x, y in ((60, 103), (111, 189), (200, 30), (0, 220)):
            expected = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh
            self.assertEqual(self.provider.get_location_name((x, y)), expected)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_prepares_terrain_room(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        ok = enter_wilderness(self.char1, coordinates=NORTH_APPROACH, name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertIsInstance(room, TerrainRoom)
        self.assertEqual(room.ndb.active_desc, terrain_description(*NORTH_APPROACH))
        self.assertEqual(room.scene_archetype, region_for_coordinates(*NORTH_APPROACH))

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

        from world.maps.wilderness_provider import (
            terrain_description as _terrain_description,
        )

        room = create_object(TerrainRoom, key="scriptless")
        self.assertIsNone(room.wilderness)
        self.provider.at_prepare_room(NORTH_APPROACH, None, room)
        self.assertEqual(room.scene_archetype, region_for_coordinates(*NORTH_APPROACH))
        self.assertEqual(room.ndb.active_desc, _terrain_description(*NORTH_APPROACH))
        self.assertEqual(Monster.objects.all().count(), 0)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_at_prepare_room_opens_exactly_the_gate_exit_at_an_approach_cell(self):
        room = self._eight_exits(create_object(TerrainRoom, key="approach-a"))
        # Stock would close the north exit at (60, 97): its neighbor (60, 98)
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
        self.provider.at_prepare_room((200, 100), None, room)
        for exit_obj in room.exits:
            self.assertFalse(self._locks_allow(exit_obj, "traverse"))

        # The NORTH approach opens only its own "south" exit -- never the other
        # gate's.
        room_b = self._eight_exits(create_object(TerrainRoom, key="approach-c"))
        for exit_obj in room_b.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        self.provider.at_prepare_room(NORTH_APPROACH, None, room_b)
        by_key = {exit_obj.key: exit_obj for exit_obj in room_b.exits}
        self.assertTrue(self._locks_allow(by_key[LONG_DIRECTIONS["s"]], "traverse"))
        self.assertFalse(self._locks_allow(by_key[LONG_DIRECTIONS["n"]], "traverse"))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_a_point_shape_anchor_opens_all_eight_exits(self):
        from world.lore.wilderness_entry import (
            WILDERNESS_ENTRY_REGISTRY,
            WildernessEntryPoint,
            WildernessGate,
        )

        point = WildernessEntryPoint(
            "capital_altoria", ("#",), (120, 120), (WildernessGate("n", (2, 0), "capital_altoria"),)
        )
        room = self._eight_exits(create_object(TerrainRoom, key="point-anchor"))
        for exit_obj in room.exits:
            exit_obj.locks.add("traverse:false();view:false()")
        with patch.dict(WILDERNESS_ENTRY_REGISTRY, {"capital_altoria": point}):
            self.provider.at_prepare_room((120, 120), None, room)
        for exit_obj in room.exits:
            self.assertTrue(self._locks_allow(exit_obj, "traverse"))
            self.assertTrue(self._locks_allow(exit_obj, "view"))

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
        # Re-activate the SAME pooled room at a non-approach cell whose north
        # neighbor is provider-invalid (y = 223, the rect edge): the stock
        # lock pass recomputes every self-loop exit's lock from validity and
        # the hook adds nothing there -- the hook-opened north lock cannot
        # survive the coordinate change.
        room_a.set_active_coordinates((100, 223), self.char1)
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
        enter_wilderness(self.char1, coordinates=NORTH_APPROACH, name=WILDERNESS_NAME)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters = [
            obj for obj in script.get_objs_at_coordinates(NORTH_APPROACH) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        self.assertEqual(monsters[0].db.population_key, "wilderness:60:103")
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
        # Enter at the north-gate approach in western_hills_valleys.
        enter_wilderness(self.char1, coordinates=NORTH_APPROACH, name=WILDERNESS_NAME)
        room_a = self.char1.location
        self.assertEqual(room_a.scene_archetype, "western_hills_valleys")
        # Leave the wilderness; then force the room back into the reuse pool
        # (the sanctioned "inspect unused_rooms directly" route) so the
        # next entry is guaranteed to be handed this exact object again.
        self.char1.move_to(self.room1)
        del script.db.rooms[NORTH_APPROACH]
        del room_a.ndb.active_coordinates
        script.db.unused_rooms.append(room_a)
        # Re-enter at a coordinate in a different region: the pooled room is
        # reused and must reflect the new region, never the stale first value.
        enter_wilderness(self.char1, coordinates=(200, 100), name=WILDERNESS_NAME)
        self.assertIs(self.char1.location, room_a)
        self.assertEqual(self.char1.location.scene_archetype, "eastern_plains")
        self.assertEqual(
            self.char1.location.ndb.active_desc, terrain_description(200, 100)
        )
