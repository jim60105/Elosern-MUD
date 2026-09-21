"""Data-contract test: map bootstrap/gate data contract
Integration tests for idempotent grid and wilderness bootstrap (map-anchor-grid, map-wilderness)."""

from tools.spec_traceability import covers_requirement

import inspect
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.altoria_capital import XYMAP_DATA
from world.maps.city_gates import CITY_GATE_REGISTRY, CityGateDef
from world.maps.bootstrap import sync_grid, sync_limbo, sync_wilderness
from world.maps.limbo import LIMBO_ALIAS, LIMBO_DESC, LIMBO_KEY, LIMBO_LEGACY_KEY
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.tests.combat_fixtures import BattlefieldIsolation

SOUTH_GATE_XYZ = (3, 0, "capital_altoria")
EAST_GATE_XYZ = (6, 3, "capital_altoria")


class GridBootstrapTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Grid bootstrap tests.

    ``at_server_start()`` runs the full startup synchronization (including
    ``sync_guild_economy()``), so the process-global registries are snapshotted
    and restored around every test.
    """

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _count_city_exits(self):
        # all_family() counts CostedXYZExit (map-movement-clock) as well as bare
        # XYZExit, so this stays a count of intra-city exits after the wildcard
        # prototype override changes their exact typeclass.
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        return XYZExit.objects.all_family().count()

    def _bridging_exits(self):
        limbo = search_object(LIMBO_KEY, exact=True)
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        targets = [obj for obj in (limbo[0] if limbo else None, south_gate) if obj is not None]
        return [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location in targets or exit_obj.destination in targets
        ]

    @covers_requirement("sample-city-altoria::the-sample-city-has-exactly-thirteen-rooms-in-a-fixed-connected-topology")
    @covers_requirement("grid-room-sync::a-single-authored-idempotent-exit-bridges-limbo-and-the-sample-city")
    def test_sync_grid_spawns_both_settlements_rooms_and_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        # Two settlements: the capital's twenty-one rooms and the village's
        # ten (ciaran-village-crafts grew 暗影谷村 from six nodes to ten).
        self.assertEqual(self._count_grid_rooms(), 31)
        # 52 capital directed links + 18 village directed links.
        self.assertEqual(self._count_city_exits(), 70)
        # One forward Limbo bridge per CITY_GATE_REGISTRY row.
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(len(self._bridging_exits()) + self._count_city_exits(), 72)

    def test_sync_grid_is_idempotent_and_preserves_dbid(self):
        create_object(Room, key=LIMBO_KEY, location=None)
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

        self.assertEqual(self._count_grid_rooms(), 31)
        self.assertEqual(self._count_city_exits(), 70)
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(first_ids, second_ids)

    def test_single_call_on_fresh_grid_spawns_all_thirty_one_rooms(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        self.assertEqual(XYZGrid.objects.all().count(), 0)
        sync_grid()
        self.assertEqual(self._count_grid_rooms(), 31)

    def test_in_place_update_changes_desc_without_new_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        south_gate = GridRoom.objects.get(db_key="南門")
        self.assertIn("southern gate", south_gate.db.desc)

        changed = dict(XYMAP_DATA)
        changed["prototypes"] = dict(XYMAP_DATA["prototypes"])
        changed["prototypes"][(3, 0)] = dict(changed["prototypes"][(3, 0)])
        changed["prototypes"][(3, 0)]["desc"] = "A rebuilt southern gate."

        from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid

        grid = get_xyzgrid()
        grid.add_maps(changed)
        grid.reload()
        grid.spawn()

        self.assertEqual(self._count_grid_rooms(), 31)
        south_gate = GridRoom.objects.get(db_key="南門")
        self.assertEqual(south_gate.db.desc, "A rebuilt southern gate.")

    @covers_requirement("scene-archetype-mixin::gridroom-is-retrofitted-onto-scenearchetypemixin-without-changing-its-contract")
    def test_anchor_room_matches_placement_registry_after_sync(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        # Every placement row matches its settlement's spawned AnchorRoom:
        # zcoord and entrance_xy equal the room's coordinates, and no two
        # entries share a zcoord.
        self.assertEqual(
            len({placement.zcoord for placement in ANCHOR_PLACEMENT_REGISTRY.values()}),
            len(ANCHOR_PLACEMENT_REGISTRY),
        )
        for placement in ANCHOR_PLACEMENT_REGISTRY.values():
            room = GridRoom.objects.filter_xyz(
                xyz=(placement.entrance_xy[0], placement.entrance_xy[1], placement.zcoord)
            ).first()
            self.assertIsInstance(room, AnchorRoom)
            self.assertEqual(room.anchor_key, placement.anchor_key)
            self.assertEqual(room.xyz[2], placement.zcoord)
            self.assertEqual((room.xyz[0], room.xyz[1]), placement.entrance_xy)

    def test_bridging_exits_bind_limbo_and_south_gate_idempotently(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        # One forward exit per registry row: the capital's 南門 and the
        # village's 隱密小徑.
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            ["南門", "隱密小徑"],
        )
        self.assertEqual(
            [exit_obj.key for exit_obj in south_gate.exits if exit_obj.destination == limbo],
            [],
        )

        sync_grid()
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            ["南門", "隱密小徑"],
        )
        self.assertEqual(
            [exit_obj.key for exit_obj in south_gate.exits if exit_obj.destination == limbo],
            [],
        )

    def test_bridging_lookup_is_by_key_not_dbref(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        dbref2 = self.room2
        self.assertEqual(dbref2.id, 2)
        self.assertEqual([exit_obj.key for exit_obj in dbref2.exits], [])
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            ["南門", "隱密小徑"],
        )

    def test_east_gate_holds_only_its_west_grid_link_before_wilderness_sync(self):
        # Before sync_wilderness() the 東門 is the one room whose sole grid
        # link runs west to 東市; the wilderness gate exit it later carries
        # is provisioned per-gate (wilderness-anchor-footprint).
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        exits = list(east_gate.exits)
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].destination.xyz, (5, 3, "capital_altoria"))

    def test_absent_limbo_degrades_without_raising(self):
        sync_grid()

        self.assertEqual(self._count_grid_rooms(), 31)
        self.assertEqual(self._count_city_exits(), 70)
        self.assertEqual(len(self._bridging_exits()), 0)

    @covers_requirement("limbo-one-way-gates::sync-grid-creates-exactly-one-forward-gate-exit-per-registry-row-and-converges-it-idempotently")
    def test_forward_gate_exit_converges_from_legacy_aliases_in_place(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        forward = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate][0]
        forward_id = forward.id
        # Drift the object the way a legacy database has it: English aliases.
        forward.aliases.clear()
        forward.aliases.add("south gate", "altoria")

        sync_grid()

        forwards = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate]
        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0].id, forward_id)
        self.assertEqual(forwards[0].key, "南門")
        self.assertEqual(set(forwards[0].aliases.all()), {"王都", "城門"})

    @covers_requirement("limbo-one-way-gates::the-city-gate-registry-is-the-sole-authored-source-of-虛境-city-gates")
    def test_registry_pins_the_capital_row_and_rejects_mutation(self):
        from dataclasses import FrozenInstanceError

        self.assertEqual(list(CITY_GATE_REGISTRY), ["capital_altoria", "village_ciaran"])
        row = CITY_GATE_REGISTRY["capital_altoria"]
        self.assertEqual(row.gate_xyz, (3, 0, "capital_altoria"))
        self.assertEqual(row.exit_key, "南門")
        self.assertEqual(row.exit_aliases, ("王都", "城門"))
        village = CITY_GATE_REGISTRY["village_ciaran"]
        self.assertEqual(village.gate_xyz, (0, 1, "village_ciaran"))
        self.assertEqual(village.exit_key, "隱密小徑")
        with self.assertRaises(TypeError):
            CITY_GATE_REGISTRY["ghost"] = row
        with self.assertRaises(TypeError):
            del CITY_GATE_REGISTRY["capital_altoria"]
        with self.assertRaises(FrozenInstanceError):
            row.exit_key = "篡改"
        self.assertEqual(list(CITY_GATE_REGISTRY), ["capital_altoria", "village_ciaran"])

    @covers_requirement("limbo-one-way-gates::the-city-gate-registry-is-the-sole-authored-source-of-虛境-city-gates")
    def test_no_exit_key_or_alias_collides_between_registry_rows(self):
        # The village's row (隱密小徑 + its aliases) must not collide with the
        # capital's (南門/王都/城門) — the starting room trusts exit keys as
        # unique resolution targets.
        seen = set()
        for row in CITY_GATE_REGISTRY.values():
            for name in (row.exit_key, *row.exit_aliases):
                self.assertNotIn(name, seen)
                seen.add(name)

    @covers_requirement("limbo-one-way-gates::sync-grid-creates-exactly-one-forward-gate-exit-per-registry-row-and-converges-it-idempotently")
    def test_duplicate_forward_exits_collapse_to_the_single_authored_exit(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        # Seed a second forward exit toward the same gate (database history).
        duplicate = create_object(Exit, key="重複門", location=limbo, destination=south_gate)
        keeper_id = min(
            exit_obj.id for exit_obj in limbo.exits if exit_obj.destination == south_gate
        )

        sync_grid()

        forwards = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate]
        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0].id, keeper_id)
        self.assertEqual(forwards[0].key, "南門")
        self.assertFalse(Exit.objects.filter(id=duplicate.id).exists())

    @covers_requirement("limbo-one-way-gates::every-sync-prunes-every-exit-whose-destination-is-the-starting-room")
    def test_reverse_exit_is_pruned_once_with_event(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        # Seed the pre-change return exit the way an existing database has it.
        create_object(
            Exit,
            key="離開王都",
            aliases=["回虛境"],
            location=south_gate,
            destination=limbo,
        )

        with patch("world.maps.bootstrap.log_info") as info:
            sync_grid()
        prunes = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "bootstrap_grid_exit_pruned"
        ]
        self.assertEqual(len(prunes), 1)
        self.assertEqual(prunes[0].args[0], "bootstrap_grid_exit_pruned")
        self.assertEqual(prunes[0].kwargs["context"]["exit_key"], "離開王都")
        self.assertEqual(prunes[0].kwargs["context"]["source_room_key"], south_gate.key)
        self.assertEqual(
            [exit_obj for exit_obj in south_gate.exits if exit_obj.destination == limbo],
            [],
        )

        # A converged database prunes and logs nothing.
        with patch("world.maps.bootstrap.log_info") as info:
            sync_grid()
        self.assertEqual(
            [
                call
                for call in info.call_args_list
                if call.args and call.args[0] == "bootstrap_grid_exit_pruned"
            ],
            [],
        )

    @covers_requirement("limbo-one-way-gates::the-city-gate-registry-is-the-sole-authored-source-of-虛境-city-gates")
    def test_limbo_exit_set_equals_registry_rows(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        expected = {row.exit_key: row.gate_xyz for row in CITY_GATE_REGISTRY.values()}
        self.assertEqual(
            {exit_obj.key: exit_obj.destination.xyz for exit_obj in limbo.exits},
            expected,
        )

    @covers_requirement("limbo-one-way-gates::sync-grid-creates-exactly-one-forward-gate-exit-per-registry-row-and-converges-it-idempotently")
    def test_starting_room_gains_exactly_one_forward_exit_per_registry_row(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        limbo = next(
            exit_obj.location
            for exit_obj in Exit.objects.all()
            if exit_obj.destination == south_gate
        )

        by_key = {exit_obj.key: exit_obj for exit_obj in limbo.exits}
        self.assertEqual(sorted(by_key), sorted(row.exit_key for row in CITY_GATE_REGISTRY.values()))
        for row in CITY_GATE_REGISTRY.values():
            exit_obj = by_key[row.exit_key]
            # Exactly one forward exit per row, leading to that row's gate room.
            self.assertEqual(exit_obj.destination.xyz, row.gate_xyz)

    @covers_requirement(
        "village-ciaran-map::the-village-has-exactly-one-concealed-entrance"
    )
    @covers_requirement("limbo-one-way-gates::every-sync-prunes-every-exit-whose-destination-is-the-starting-room")
    def test_no_village_room_holds_an_exit_back_to_the_starting_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        limbo = next(
            exit_obj.location
            for exit_obj in Exit.objects.all()
            if exit_obj.destination == south_gate
        )
        for room in GridRoom.objects.filter_xyz(xyz=("*", "*", "village_ciaran")):
            self.assertEqual(
                [exit_obj for exit_obj in room.exits if exit_obj.destination == limbo],
                [],
                f"{room.key} at {room.xyz} holds an exit back into 虛境",
            )

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_same_coordinate_resolves_to_different_rooms_in_each_settlement(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        # (2,1) exists on both maps: 河岸道 in the capital, 練刀場 in the
        # village — the shared (X, Y) still names two different rooms.
        capital_room = GridRoom.objects.filter_xyz(xyz=(2, 1, "capital_altoria")).first()
        village_room = GridRoom.objects.filter_xyz(xyz=(2, 1, "village_ciaran")).first()
        self.assertIsNotNone(capital_room)
        self.assertIsNotNone(village_room)
        self.assertIsNot(capital_room, village_room)
        self.assertNotEqual(capital_room.id, village_room.id)
        self.assertEqual(capital_room.key, "河岸道")
        self.assertEqual(village_room.key, "練刀場")

    @covers_requirement("limbo-one-way-gates::a-registry-row-whose-gate-room-is-missing-warns-and-is-skipped-without-blocking-other-rows")
    def test_missing_gate_room_row_warns_and_skips_without_blocking(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        broken_row = CityGateDef(
            map_id="nowhere_city",
            gate_xyz=(9, 9, "nowhere"),
            exit_key="空門",
            exit_aliases=("不存在",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["nowhere_city"] = broken_row

        with (
            patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound),
            patch("world.maps.bootstrap.log_warn") as warn,
        ):
            sync_grid()

        missing = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "bootstrap_grid_gate_missing"
        ]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].kwargs["context"]["map_id"], "nowhere_city")
        self.assertEqual(missing[0].kwargs["context"]["action"], "skip_gate_row")
        # The healthy rows still converged; the broken row created nothing.
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            sorted(row.exit_key for row in CITY_GATE_REGISTRY.values()),
        )

    @covers_requirement("limbo-one-way-gates::adding-a-city-means-adding-a-registry-row-with-no-bootstrap-code-change")
    def test_second_registry_row_converges_a_second_forward_gate(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        second_row = CityGateDef(
            map_id="capital_altoria",
            gate_xyz=EAST_GATE_XYZ,
            exit_key="北門",
            exit_aliases=("王都北",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["capital_altoria_north"] = second_row

        with patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound):
            sync_grid()

        second_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        keys = sorted(exit_obj.key for exit_obj in limbo.exits)
        self.assertEqual(
            keys,
            sorted(row.exit_key for row in rebound.values()),
        )
        self.assertEqual(len(limbo.exits), len(rebound))
        # Every gate exists; neither city side leads back into 虛境.
        self.assertIsNone(
            [exit_obj for exit_obj in second_gate.exits if exit_obj.destination == limbo] or None
        )
        # And a seeded reverse exit for the NEW gate prunes the same way.
        create_object(Exit, key="回虛境二", location=second_gate, destination=limbo)
        sync_grid()
        self.assertEqual([exit_obj for exit_obj in second_gate.exits if exit_obj.destination == limbo], [])
        sync_grid()
        self.assertEqual(len(limbo.exits), len(rebound))

    @covers_requirement("grid-room-sync::sync-grid-runs-automatically-at-server-start-after-sync-all")
    @covers_requirement("grid-room-sync::the-evennia-xyzgrid-cli-remains-available-but-is-not-required-for-boot", "lore-startup-sync::sync-runs-automatically-at-evennia-server-start")
    def test_at_server_start_calls_sync_grid_after_sync_all(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_all"),
            STARTUP_STEP_ORDER.index("sync_grid"),
        )

    def test_at_server_start_without_limbo_syncs_lore_and_grid(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 31)
        self.assertEqual(self._count_city_exits(), 70)
        self.assertEqual(len(self._bridging_exits()), 0)
        from evennia.utils.search import search_script

        self.assertEqual(len(search_script("lore:anchor_placements:capital_altoria")), 1)

    def test_at_server_start_with_limbo_creates_bridging_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 31)
        self.assertEqual(self._count_city_exits(), 70)
        self.assertEqual(len(self._bridging_exits()), 2)


class WildernessBootstrapTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Wilderness bootstrap tests (``at_server_start()`` mutates the shared
    registries, so they are snapshotted and restored around every test)."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _east_gate(self):
        return GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()

    def _south_gate(self):
        return GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()

    def _gate_exits(self, gate=None):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        gate = gate if gate is not None else self._east_gate()
        gates = [e for e in gate.exits if isinstance(e, WildernessGateExit)]
        return script, gates

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_sync_wilderness_provisions_one_gate_exit_per_authored_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()

        script, gates = self._gate_exits()
        self.assertIsNotNone(script)
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(gates[0].key, "荒野")
        # Per-gate provisioning (wilderness-anchor-footprint): the 東門 room
        # holds the return-direction "w" gate, the 南門 room the "n" gate.
        self.assertEqual(gates[0].db.gate_direction, "w")
        south_gates = self._gate_exits(self._south_gate())[1]
        self.assertEqual(len(south_gates), 1)
        self.assertEqual(south_gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(south_gates[0].db.gate_direction, "n")
        self.assertEqual(south_gates[0].key, "荒野")
        # Exact outward-face aliases: the 東門 faces east; the
        # 南門 faces south.
        self.assertEqual(sorted(gates[0].aliases.all()), ["e", "east", "wilderness"])
        self.assertEqual(sorted(south_gates[0].aliases.all()), ["s", "south", "wilderness"])
        # The village's single gate provisions exactly one exit on the
        # entrance node 隱密小徑, facing the wilderness with the authored
        # return direction "n".
        village_gate_exits = [
            e for e in GridRoom.objects.filter_xyz(xyz=(0, 1, "village_ciaran")).first().exits
            if isinstance(e, WildernessGateExit)
        ]
        self.assertEqual(len(village_gate_exits), 1)
        self.assertEqual(village_gate_exits[0].key, "荒野")
        self.assertEqual(village_gate_exits[0].db.anchor_key, "village_ciaran")
        self.assertEqual(village_gate_exits[0].db.gate_direction, "n")
        self.assertEqual(
            sorted(village_gate_exits[0].aliases.all()),
            ["s", "south", "wilderness"],
        )
        self.assertEqual(WildernessGateExit.objects.all().count(), 3)

    def test_provisioned_gates_are_immediately_traversable(self):
        # No extra sync pass is needed before the gates work (design D2):
        # freshly provisioned rooms land deterministically on their approach
        # cells.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        east_gate = self._gate_exits()[1][0]
        east_gate.at_traverse(self.char1, self._east_gate())
        self.assertEqual(self.char1.location.coordinates, (63, 100))
        self.char1.move_to(self._east_gate())
        south_gate = self._gate_exits(self._south_gate())[1][0]
        south_gate.at_traverse(self.char1, self._south_gate())
        self.assertEqual(self.char1.location.coordinates, (60, 97))

    def test_sync_wilderness_is_idempotent(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        sync_wilderness()

        script, gates = self._gate_exits()
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        self.assertEqual(WildernessScript.objects.filter(db_key=WILDERNESS_NAME).count(), 1)
        self.assertEqual(len(gates), 1)
        self.assertEqual(WildernessGateExit.objects.all().count(), 3)

    def test_sync_wilderness_without_east_gate_degrades_gracefully(self):
        sync_wilderness()

        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(WildernessGateExit.objects.all().count(), 0)

    def test_sync_grid_body_is_unmodified(self):
        source = inspect.getsource(sync_grid)
        self.assertIn("grid.spawn()", source)
        self.assertNotIn("sync_wilderness", source)

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_at_server_start_calls_sync_wilderness_after_sync_grid(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_grid"),
            STARTUP_STEP_ORDER.index("sync_wilderness"),
        )

    def test_at_server_start_provisions_wilderness_too(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), 31)
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_village_gate_roundtrips_to_the_entrance_node(self):
        # A traveler on 隱密小徑 steps into the wilderness at the village's
        # approach cell, and a traveler standing there and moving in the
        # gate's return direction ("n") arrives back at 隱密小徑 (task 3.3).
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()

        entrance_room = GridRoom.objects.filter_xyz(xyz=(0, 1, "village_ciaran")).first()
        gate_exit = [
            e for e in entrance_room.exits if isinstance(e, WildernessGateExit)
        ][0]

        gate_exit.at_traverse(self.char1, entrance_room)
        self.assertEqual(self.char1.location.coordinates, (40, 138))

        north = [e for e in self.char1.location.exits if e.key == "north"][0]
        north.at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, entrance_room)

    def test_sync_wilderness_restores_retained_room_descriptions(self):
        # Simulate a server restart: provision the wilderness, walk in to
        # create a retained room, wipe its non-persistent description (as a
        # restart does -- ndb values are not stored), then re-run
        # sync_wilderness() and confirm the deterministic description returns.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        from evennia.contrib.grid.wilderness.wilderness import (  # noqa: F811
            WildernessScript,
            enter_wilderness,
        )

        from world.maps.wilderness_provider import terrain_description

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        ok = enter_wilderness(self.char1, coordinates=(63, 100), name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertEqual(room.ndb.active_desc, terrain_description(63, 100))
        room.ndb.active_desc = None  # wipe like a restart would
        room.ndb.someother = 1
        # The returned room is retained (account still present); re-running
        # sync_wilderness must re-prepare it.
        sync_wilderness()
        self.assertEqual(room.ndb.active_desc, terrain_description(63, 100))
        self.assertEqual(room.scene_archetype, "western_hills_valleys")

    def test_sync_wilderness_heals_miskeyed_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
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
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_misdirected_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        gate = self._gate_exits()[1][0]
        gate.db.gate_direction = "e"
        sync_wilderness()
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_a_misattributed_single_gate_exit(self):
        # A lone WildernessGateExit with foreign attrs on a gate room IS that
        # room's gate slot: sync heals its (anchor, gate) pair in place rather
        # than stacking a second gate (spec scenario "a mis-provisioned gate
        # is healed").
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        foreign = create_object(
            WildernessGateExit,
            key="荒野",
            location=self._south_gate(),
            destination=self._south_gate(),
        )
        foreign.db.anchor_key = "wrong_anchor"
        foreign.db.gate_direction = "w"
        sync_wilderness()
        south_gates = self._gate_exits(self._south_gate())[1]
        self.assertEqual(len(south_gates), 1)
        self.assertIs(south_gates[0], foreign)
        self.assertEqual(foreign.db.anchor_key, "capital_altoria")
        self.assertEqual(foreign.db.gate_direction, "n")

    def test_sync_wilderness_skips_an_ambiguous_multi_row_gate_room(self):
        # Two WildernessGateExit rows on one room are ambiguous: sync warns and
        # provisions nothing there, but still heals/provisions the other gate.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        south_gate = self._south_gate()
        create_object(WildernessGateExit, key="荒野", location=south_gate, destination=south_gate)
        create_object(WildernessGateExit, key="荒野二", location=south_gate, destination=south_gate)
        sync_wilderness()
        self.assertEqual(len(self._gate_exits(south_gate)[1]), 2)
        # The unaffected east gate provisions to exactly one exit.
        self.assertEqual(len(self._gate_exits()[1]), 1)

    def test_sync_wilderness_leaves_same_key_foreign_exit_alone(self):
        from typeclasses.exits import Exit

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        # Plant a plain Exit that occupies the gate key.
        east_gate = self._east_gate()
        create_object(
            Exit,
            key="荒野",
            location=east_gate,
            destination=east_gate,
        )
        sync_wilderness()
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        # The foreign exit is untouched (not replaced, not duplicated), and the
        # gate count stays at exactly one WildernessGateExit.
        foreign = [e for e in east_gate.exits if isinstance(e, Exit) and not isinstance(e, WildernessGateExit)]
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].key, "荒野")