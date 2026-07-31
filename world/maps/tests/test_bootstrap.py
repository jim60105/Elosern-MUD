"""Integration tests for idempotent grid and wilderness bootstrap (map-anchor-grid, map-wilderness)."""

import inspect

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.maps.altoria_capital import XYMAP_DATA
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")
NORTH_GATE_XYZ = (2, 4, "capital_altoria")


class GridBootstrapTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _count_city_exits(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        return XYZExit.objects.all().count()

    def _bridging_exits(self):
        limbo = search_object("Limbo", exact=True)
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        targets = [obj for obj in (limbo[0] if limbo else None, south_gate) if obj is not None]
        return [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location in targets or exit_obj.destination in targets
        ]

    def test_sync_grid_creates_thirteen_rooms_and_twenty_six_exits(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()

        self.assertEqual(self._count_grid_rooms(), 13)
        self.assertEqual(self._count_city_exits(), 24)
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(len(self._bridging_exits()) + self._count_city_exits(), 26)

    def test_sync_grid_is_idempotent_and_preserves_dbid(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        first_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        sync_grid()
        second_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        self.assertEqual(self._count_grid_rooms(), 13)
        self.assertEqual(self._count_city_exits(), 24)
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(first_ids, second_ids)

    def test_single_call_on_fresh_grid_spawns_all_thirteen_rooms(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        self.assertEqual(XYZGrid.objects.all().count(), 0)
        sync_grid()
        self.assertEqual(self._count_grid_rooms(), 13)

    def test_in_place_update_changes_desc_without_new_room(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()

        south_gate = GridRoom.objects.get(db_key="南門")
        self.assertIn("southern gate", south_gate.db.desc)

        changed = dict(XYMAP_DATA)
        changed["prototypes"] = dict(XYMAP_DATA["prototypes"])
        changed["prototypes"][(2, 0)] = dict(changed["prototypes"][(2, 0)])
        changed["prototypes"][(2, 0)]["desc"] = "A rebuilt southern gate."

        from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid

        grid = get_xyzgrid()
        grid.add_maps(changed)
        grid.reload()
        grid.spawn()

        self.assertEqual(self._count_grid_rooms(), 13)
        south_gate = GridRoom.objects.get(db_key="南門")
        self.assertEqual(south_gate.db.desc, "A rebuilt southern gate.")

    def test_anchor_room_matches_placement_registry_after_sync(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()

        placement = ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]
        room = GridRoom.objects.filter_xyz(
            xyz=(placement.entrance_xy[0], placement.entrance_xy[1], placement.zcoord)
        ).first()
        self.assertIsInstance(room, AnchorRoom)
        self.assertEqual(room.anchor_key, "capital_altoria")

    def test_bridging_exits_bind_limbo_and_south_gate_idempotently(self):
        limbo = create_object(Room, key="Limbo", location=None)
        sync_grid()

        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        limbo_exits = [exit_obj for exit_obj in limbo.exits]
        south_gate_to_limbo = [
            exit_obj for exit_obj in south_gate.exits if exit_obj.destination == limbo
        ]
        self.assertEqual([exit_obj.key for exit_obj in limbo_exits], ["南門"])
        self.assertEqual([exit_obj.key for exit_obj in south_gate_to_limbo], ["離開王都"])

        sync_grid()
        self.assertEqual([exit_obj.key for exit_obj in limbo.exits], ["南門"])
        self.assertEqual(
            [exit_obj.key for exit_obj in south_gate.exits if exit_obj.destination == limbo],
            ["離開王都"],
        )

    def test_bridging_lookup_is_by_key_not_dbref(self):
        limbo = create_object(Room, key="Limbo", location=None)
        sync_grid()

        dbref2 = self.room2
        self.assertEqual(dbref2.id, 2)
        self.assertEqual([exit_obj.key for exit_obj in dbref2.exits], [])
        self.assertEqual([exit_obj.key for exit_obj in limbo.exits], ["南門"])

    def test_north_gate_is_a_dead_end(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()

        north_gate = GridRoom.objects.filter_xyz(xyz=(2, 4, "capital_altoria")).first()
        exits = list(north_gate.exits)
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].destination.xyz, (2, 3, "capital_altoria"))

    def test_absent_limbo_degrades_without_raising(self):
        sync_grid()

        self.assertEqual(self._count_grid_rooms(), 13)
        self.assertEqual(self._count_city_exits(), 24)
        self.assertEqual(len(self._bridging_exits()), 0)

    def test_at_server_start_calls_sync_grid_after_sync_all(self):
        source = inspect.getsource(at_server_start)
        self.assertLess(source.index("sync_all()"), source.index("sync_grid()"))

    def test_at_server_start_without_limbo_syncs_lore_and_grid(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 13)
        self.assertEqual(self._count_city_exits(), 24)
        self.assertEqual(len(self._bridging_exits()), 0)
        from evennia.utils.search import search_script

        self.assertEqual(len(search_script("lore:anchor_placements:capital_altoria")), 1)

    def test_at_server_start_with_limbo_creates_bridging_exits(self):
        create_object(Room, key="Limbo", location=None)
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 13)
        self.assertEqual(self._count_city_exits(), 24)
        self.assertEqual(len(self._bridging_exits()), 2)


class WildernessBootstrapTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _north_gate(self):
        return GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()

    def _gate_exits(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        gate = self._north_gate()
        gates = [e for e in gate.exits if isinstance(e, WildernessGateExit)]
        return script, gates

    def test_sync_wilderness_creates_script_and_gate_with_anchor_key(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()

        script, gates = self._gate_exits()
        self.assertIsNotNone(script)
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(gates[0].key, "荒野")

    def test_sync_wilderness_is_idempotent(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()
        sync_wilderness()

        script, gates = self._gate_exits()
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        self.assertEqual(WildernessScript.objects.filter(db_key=WILDERNESS_NAME).count(), 1)
        self.assertEqual(len(gates), 1)

    def test_sync_wilderness_without_north_gate_degrades_gracefully(self):
        sync_wilderness()

        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(WildernessGateExit.objects.all().count(), 0)

    def test_sync_grid_body_is_unmodified(self):
        source = inspect.getsource(sync_grid)
        self.assertIn("grid.spawn()", source)
        self.assertNotIn("sync_wilderness", source)

    def test_at_server_start_calls_sync_wilderness_after_sync_grid(self):
        source = inspect.getsource(at_server_start)
        self.assertLess(source.index("sync_grid()"), source.index("sync_wilderness()"))

    def test_at_server_start_provisions_wilderness_too(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 13)
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)

    def test_sync_wilderness_restores_retained_room_descriptions(self):
        # Simulate a server restart: provision the wilderness, walk in to
        # create a retained room, wipe its non-persistent description (as a
        # restart does -- ndb values are not stored), then re-run
        # sync_wilderness() and confirm the deterministic description returns.
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()
        from evennia.contrib.grid.wilderness.wilderness import (  # noqa: F811
            WildernessScript,
            enter_wilderness,
        )

        from world.maps.wilderness_provider import terrain_description

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        ok = enter_wilderness(self.char1, coordinates=(60, 100), name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertEqual(room.ndb.active_desc, terrain_description(60, 100))
        room.ndb.active_desc = None  # wipe like a restart would
        room.ndb.someother = 1
        # The returned room is retained (account still present); re-running
        # sync_wilderness must re-prepare it.
        sync_wilderness()
        self.assertEqual(room.ndb.active_desc, terrain_description(60, 100))
        self.assertEqual(room.scene_archetype, "western_hills_valleys")

    def test_sync_wilderness_heals_miskeyed_gate(self):
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()
        # Misconfigure the gate's anchor_key, then re-run and confirm it heals.
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        gate = gates[0]
        gate.db.anchor_key = "wrong_anchor"
        sync_wilderness()
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")

    def test_sync_wilderness_leaves_same_key_foreign_exit_alone(self):
        from typeclasses.exits import Exit

        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()
        # Plant a plain Exit that occupies the gate key.
        north_gate = self._north_gate()
        create_object(
            Exit,
            key="荒野",
            location=north_gate,
            destination=north_gate,
        )
        sync_wilderness()
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        # The foreign exit is untouched (not replaced, not duplicated), and the
        # gate count stays at exactly one WildernessGateExit.
        foreign = [e for e in north_gate.exits if isinstance(e, Exit) and not isinstance(e, WildernessGateExit)]
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].key, "荒野")