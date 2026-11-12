"""Data-contract test: map bootstrap/gate data contract

The shipped-scale convergence cases: one class per worker-sized unit, kept
apart from the local fixture cases so a four-worker job can run them in
parallel without serializing two whole-world passes onto one worker.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.city_gates import CITY_GATE_REGISTRY, CityGateDef
from world.maps.limbo import LIMBO_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import (
    StaticReferenceError,
    anchor_entrance_xyz,
    place_exterior_xyz,
    settlement_node_xyz,
)
from elosern_map_core.references import settlement_node_ref
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.tests.geography_fixture import (
    selected_startup_settlements,
    sync_test_settlements,
    sync_test_wilderness,
)
from world.maps.tests._bootstrap_fixtures import (
    ANCHOR_PLACEMENT_MAP_IDS,
    CAPITAL_MAP_IDS,
    CAPITAL_VILLAGE_MAP_IDS,
    CITY_GATE_MAP_IDS,
    EAST_GATE_XYZ,
    SELECTED_GATE_ROW_COUNT,
    SOUTH_GATE_XYZ,
    VILLAGE_MAP_IDS,
    WILDERNESS_GATE_MAP_IDS,
    _GridBootstrapCase,
    _WildernessBootstrapCase,
    _approach,
    _declared_node_count,
    _declared_road_count,
)

class GridBootstrapAnchorTests(_GridBootstrapCase):
    """The whole-roster anchor placement contract (one serial worker)."""

    @covers_requirement("scene-archetype-mixin::gridroom-is-retrofitted-onto-scenearchetypemixin-without-changing-its-contract")
    def test_anchor_room_matches_placement_registry_after_sync(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(ANCHOR_PLACEMENT_MAP_IDS)

        # Every placement row matches its settlement's spawned AnchorRoom:
        # zcoord and the resolved entrance equal the room's coordinates, and no two
        # entries share a zcoord.
        self.assertEqual(
            len({placement.zcoord for placement in ANCHOR_PLACEMENT_REGISTRY.values()}),
            len(ANCHOR_PLACEMENT_REGISTRY),
        )
        for placement in ANCHOR_PLACEMENT_REGISTRY.values():
            entrance = anchor_entrance_xyz(placement)
            room = GridRoom.objects.filter_xyz(xyz=entrance).first()
            self.assertIsInstance(room, AnchorRoom)
            self.assertEqual(room.anchor_key, placement.anchor_key)
            self.assertEqual(room.xyz[2], placement.zcoord)
            self.assertEqual(room.xyz, entrance)


class GridBootstrapBridgingTests(_GridBootstrapCase):
    """Limbo bridging, gate exits and startup cases."""

    def test_bridging_exits_bind_limbo_and_south_gate_idempotently(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

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

        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
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
        sync_test_settlements(CITY_GATE_MAP_IDS)

        dbref2 = self.room2
        self.assertEqual(dbref2.id, 2)
        self.assertEqual([exit_obj.key for exit_obj in dbref2.exits], [])
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            sorted(row.exit_key for row in CITY_GATE_REGISTRY.values()),
        )

    def test_east_gate_holds_only_its_west_grid_link_before_wilderness_sync(self):
        # Before sync_wilderness() each of the east gate's grid links is one
        # authored road leaving the node; the wilderness gate exit it later
        # carries is provisioned per-gate (wilderness-anchor-footprint).
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        from world.maps.map_data import current

        east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        exits = list(east_gate.exits)
        document = current().settlements[EAST_GATE_XYZ[2]]
        authored = [
            road for road in document.roads if road.source == "east_gate"
        ]
        self.assertEqual(len(exits), len(authored))
        self.assertEqual(
            {exit_obj.destination.xyz for exit_obj in exits},
            {
                (
                    *document.nodes[road.destination].coordinate,
                    EAST_GATE_XYZ[2],
                )
                for road in authored
            },
        )

    def test_absent_limbo_degrades_without_raising(self):
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), 0)

    @covers_requirement("limbo-one-way-gates::sync-grid-creates-exactly-one-forward-gate-exit-per-registry-row-and-converges-it-idempotently")
    def test_forward_gate_exit_converges_from_legacy_aliases_in_place(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        forward = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate][0]
        forward_id = forward.id
        # Drift the object the way a legacy database has it: English aliases.
        forward.aliases.clear()
        forward.aliases.add("south gate", "altoria")

        sync_test_settlements(CAPITAL_MAP_IDS)

        forwards = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate]
        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0].id, forward_id)
        self.assertEqual(forwards[0].key, "南門")
        self.assertEqual(set(forwards[0].aliases.all()), {"王都", "城門"})

    @covers_requirement("limbo-one-way-gates::the-city-gate-registry-is-the-sole-authored-source-of-虛境-city-gates")
    def test_registry_pins_the_capital_row_and_rejects_mutation(self):
        from dataclasses import FrozenInstanceError
        from world.maps.map_data import current

        authored_rows = {
            map_id
            for map_id, document in current().settlements.items()
            if document.city_gate is not None
        }
        self.assertEqual(set(CITY_GATE_REGISTRY), authored_rows)
        row = CITY_GATE_REGISTRY["capital_altoria"]
        self.assertEqual(settlement_node_xyz(row.gate), SOUTH_GATE_XYZ)
        self.assertEqual(row.exit_key, "南門")
        self.assertEqual(row.exit_aliases, ("王都", "城門"))
        village = CITY_GATE_REGISTRY["village_ciaran"]
        self.assertEqual(
            settlement_node_xyz(village.gate),
            settlement_node_xyz(
                WILDERNESS_ENTRY_REGISTRY["village_ciaran"].gate_for("n").destination
            ),
        )
        self.assertEqual(village.exit_key, "隱密小徑")
        with self.assertRaises(TypeError):
            CITY_GATE_REGISTRY["ghost"] = row
        with self.assertRaises(TypeError):
            del CITY_GATE_REGISTRY["capital_altoria"]
        with self.assertRaises(FrozenInstanceError):
            row.exit_key = "篡改"
        self.assertEqual(set(CITY_GATE_REGISTRY), authored_rows)

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
        sync_test_settlements(CAPITAL_MAP_IDS)
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        # Seed a second forward exit toward the same gate (database history).
        duplicate = create_object(Exit, key="重複門", location=limbo, destination=south_gate)
        keeper_id = min(
            exit_obj.id for exit_obj in limbo.exits if exit_obj.destination == south_gate
        )

        sync_test_settlements(CAPITAL_MAP_IDS)

        forwards = [exit_obj for exit_obj in limbo.exits if exit_obj.destination == south_gate]
        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0].id, keeper_id)
        self.assertEqual(forwards[0].key, "南門")
        self.assertFalse(Exit.objects.filter(id=duplicate.id).exists())

    @covers_requirement("limbo-one-way-gates::every-sync-prunes-every-exit-whose-destination-is-the-starting-room")
    def test_reverse_exit_is_pruned_once_with_event(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
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
            sync_test_settlements(CAPITAL_MAP_IDS)
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
            sync_test_settlements(CAPITAL_MAP_IDS)
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
        sync_test_settlements(CITY_GATE_MAP_IDS)

        expected = {
            row.exit_key: settlement_node_xyz(row.gate)
            for row in CITY_GATE_REGISTRY.values()
        }
        self.assertEqual(
            {exit_obj.key: exit_obj.destination.xyz for exit_obj in limbo.exits},
            expected,
        )

    @covers_requirement("limbo-one-way-gates::sync-grid-creates-exactly-one-forward-gate-exit-per-registry-row-and-converges-it-idempotently")
    def test_starting_room_gains_exactly_one_forward_exit_per_registry_row(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CITY_GATE_MAP_IDS)
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
            self.assertEqual(exit_obj.destination.xyz, settlement_node_xyz(row.gate))

    @covers_requirement(
        "village-ciaran-map::the-village-has-exactly-one-concealed-entrance"
    )
    @covers_requirement("limbo-one-way-gates::every-sync-prunes-every-exit-whose-destination-is-the-starting-room")
    def test_no_village_room_holds_an_exit_back_to_the_starting_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
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
    def test_each_settlement_keeps_its_own_coordinate_space(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        # The metre frames are disjoint: each settlement's coordinates resolve
        # only inside its own map key, never into the other's rooms.
        for map_key, node_id, key in (
            ("capital_altoria", "riverbank_road", "河岸道"),
            ("village_ciaran", "training_clearing", "練刀場"),
        ):
            coordinate = SETTLEMENT_GRAPHS[map_key].node(node_id).coordinate
            room = GridRoom.objects.filter_xyz(xyz=(*coordinate, map_key)).first()
            self.assertIsNotNone(room)
            self.assertEqual(room.key, key)
            other_map = (
                "village_ciaran" if map_key == "capital_altoria" else "capital_altoria"
            )
            self.assertIsNone(
                GridRoom.objects.filter_xyz(xyz=(*coordinate, other_map)).first()
            )

    @covers_requirement("limbo-one-way-gates::a-registry-row-whose-gate-room-is-missing-warns-and-is-skipped-without-blocking-other-rows")
    def test_absent_authored_gate_target_rejects_before_bridging(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        broken_row = CityGateDef(
            gate=settlement_node_ref("nowhere_city", "missing"),
            exit_key="空門",
            exit_aliases=("不存在",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["nowhere_city"] = broken_row

        with (
            patch("world.maps.city_gates.CITY_GATE_REGISTRY", rebound),
            patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound),
        ):
            with self.assertRaises(StaticReferenceError):
                sync_test_settlements(CITY_GATE_MAP_IDS)
        self.assertEqual(list(limbo.exits), [])

    @covers_requirement("limbo-one-way-gates::a-registry-row-whose-gate-room-is-missing-warns-and-is-skipped-without-blocking-other-rows")
    def test_missing_gate_room_row_warns_and_skips_without_blocking(self):
        # A valid authored identity whose materialized room is absent keeps
        # the convergence warn-and-skip contract; only resolution failures
        # are rejected by the preflight.
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        broken_row = CityGateDef(
            gate=settlement_node_ref("capital_altoria", "east_gate"),
            exit_key="空門",
            exit_aliases=("不存在",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["missing_room"] = broken_row
        real_resolve = settlement_node_xyz

        def resolve(reference, **kwargs):
            if reference == broken_row.gate:
                return (999, 999, "capital_altoria")
            return real_resolve(reference, **kwargs)

        with (
            patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound),
            patch("world.maps.bootstrap.settlement_node_xyz", side_effect=resolve),
            patch("world.maps.bootstrap.log_warn") as warn,
        ):
            sync_test_settlements(CITY_GATE_MAP_IDS)

        missing = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "bootstrap_grid_gate_missing"
        ]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].kwargs["context"]["map_id"], "capital_altoria")
        self.assertEqual(missing[0].kwargs["context"]["action"], "skip_gate_row")
        # The healthy rows still converged; the broken row created nothing.
        self.assertEqual(
            sorted(exit_obj.key for exit_obj in limbo.exits),
            sorted(row.exit_key for key, row in CITY_GATE_REGISTRY.items()),
        )

    @covers_requirement("limbo-one-way-gates::adding-a-city-means-adding-a-registry-row-with-no-bootstrap-code-change")
    def test_second_registry_row_converges_a_second_forward_gate(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        second_row = CityGateDef(
            gate=settlement_node_ref("capital_altoria", "east_gate"),
            exit_key="北門",
            exit_aliases=("王都北",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["capital_altoria_north"] = second_row

        with patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound):
            sync_test_settlements(CITY_GATE_MAP_IDS)

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
        sync_test_settlements(CITY_GATE_MAP_IDS)
        self.assertEqual([exit_obj for exit_obj in second_gate.exits if exit_obj.destination == limbo], [])
        sync_test_settlements(CITY_GATE_MAP_IDS)
        self.assertEqual(len(limbo.exits), len(rebound))


class WildernessGateProvisioningTests(_WildernessBootstrapCase):
    """Whole-roster gate provisioning (one serial worker's worth of work)."""

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_sync_wilderness_provisions_one_gate_exit_per_authored_gate(self):
        from world.maps.map_data import current

        create_object(Room, key=LIMBO_KEY, location=None)
        # Gate provisioning is this contract; the ambient population is not.
        sync_test_settlements(WILDERNESS_GATE_MAP_IDS)
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS, zone_keys=())

        script, gates = self._gate_exits()
        self.assertIsNotNone(script)
        self.assertEqual(len([g for g in gates if g.db.gate_direction == "w"]), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(gates[0].key, "荒野")
        # Per-gate provisioning (wilderness-anchor-footprint): the 東門 room
        # holds the return-direction "w" gate, the 南門 room the "n" gate.
        self.assertEqual(gates[0].db.gate_direction, "w")
        south_gates = self._gate_exits(self._south_gate())[1]
        self.assertEqual(len([g for g in south_gates if g.db.gate_direction == "n"]), 1)
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
        village_entrance = settlement_node_xyz(
            WILDERNESS_ENTRY_REGISTRY["village_ciaran"].gate_for("n").destination
        )
        village_gate_exits = [
            e for e in GridRoom.objects.filter_xyz(xyz=village_entrance).first().exits
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
        self.assertEqual(
            WildernessGateExit.objects.all().count(),
            sum(
                len(document.wilderness_entry.gates)
                for document in current().settlements.values()
                if document.wilderness_entry is not None
            ),
        )

    def test_provisioned_gates_are_immediately_traversable(self):
        # No extra sync pass is needed before the gates work (design D2):
        # freshly provisioned rooms land deterministically on their approach
        # cells.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        east_gate = next(
            e for e in self._gate_exits()[1] if e.db.gate_direction == "w"
        )
        east_gate.at_traverse(self.char1, self._east_gate())
        self.assertEqual(self.char1.location.coordinates, _approach("w"))
        self.char1.move_to(self._east_gate())
        south_gate = next(
            e for e in self._gate_exits(self._south_gate())[1] if e.db.gate_direction == "n"
        )
        south_gate.at_traverse(self.char1, self._south_gate())
        self.assertEqual(self.char1.location.coordinates, _approach("n"))


class WildernessResyncTests(_WildernessBootstrapCase):
    """A second whole-roster wilderness pass changes no gate or exit."""

    def test_sync_wilderness_is_idempotent(self):
        from world.maps.map_data import current

        create_object(Room, key=LIMBO_KEY, location=None)
        # A resync's idempotency is about gates and exits; the ambient
        # population is not part of this declaration.
        sync_test_settlements(WILDERNESS_GATE_MAP_IDS)
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS, zone_keys=())
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS, zone_keys=())

        script, gates = self._gate_exits()
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        self.assertEqual(WildernessScript.objects.filter(db_key=WILDERNESS_NAME).count(), 1)
        self.assertEqual(len(gates), 1)
        self.assertEqual(
            WildernessGateExit.objects.all().count(),
            sum(
                len(document.wilderness_entry.gates)
                for document in current().settlements.values()
                if document.wilderness_entry is not None
            ),
        )
