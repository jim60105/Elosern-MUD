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
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.city_gates import CITY_GATE_REGISTRY, CityGateDef
from world.maps.bootstrap import sync_grid, sync_limbo, sync_wilderness
from world.maps.limbo import LIMBO_ALIAS, LIMBO_DESC, LIMBO_KEY, LIMBO_LEGACY_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import (
    StaticReferenceError,
    anchor_entrance_xyz,
    place_exterior_xyz,
    settlement_node_xyz,
)
from elosern_map_core.references import settlement_node_ref
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import publish_shipped_geography


publish_shipped_geography()

_CAPITAL_ENTRY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
SOUTH_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("n").destination)
EAST_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("w").destination)


def _declared_road_count():
    """The authored directed-road count of every published settlement."""

    return sum(len(graph.edges) for graph in SETTLEMENT_GRAPHS.values())


def _declared_node_count():
    """The authored node count of every published settlement."""

    return sum(len(graph.nodes) for graph in SETTLEMENT_GRAPHS.values())


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
        # A bridging exit is one that touches the starting room itself. The
        # south gate room may legitimately carry other exits once the boot
        # runs sync_wilderness() (the per-gate 荒野 gate provisioning); the
        # south gate is only resolved here as the bridge's far end, never as
        # a counting target in its own right.
        limbo = search_object(LIMBO_KEY, exact=True)
        targets = [limbo[0]] if limbo else []
        return [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location in targets or exit_obj.destination in targets
        ]

    @covers_requirement("sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology")
    @covers_requirement("grid-room-sync::a-single-authored-idempotent-exit-bridges-limbo-and-the-sample-city")
    def test_sync_grid_spawns_both_settlements_rooms_and_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        # Two settlements: the capital's twenty-one rooms and the village's
        # ten (ciaran-village-crafts grew 暗影谷村 from six nodes to ten).
        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
        # One forward Limbo bridge per CITY_GATE_REGISTRY row.
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(
            len(self._bridging_exits()) + self._count_city_exits(),
            _declared_road_count() + len(CITY_GATE_REGISTRY),
        )

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

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(first_ids, second_ids)

    def test_single_call_on_fresh_grid_spawns_all_thirty_one_rooms(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        self.assertEqual(XYZGrid.objects.all().count(), 0)
        sync_grid()
        self.assertEqual(self._count_grid_rooms(), _declared_node_count())

    def test_in_place_update_changes_desc_without_new_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        south_gate = GridRoom.objects.get(db_key="南門")
        # zhtw-room-prose: the spawn pin asserts the mechanism (the room's desc
        # equals its authored prototype), not the sentence — the prototype's
        # prose is Traditional Chinese like every other shipped room text.
        from world.maps.map_data import current

        declared = current().settlements["capital_altoria"].nodes["south_gate"]
        self.assertEqual(south_gate.xyz, (*declared.coordinate, "capital_altoria"))
        self.assertEqual(south_gate.db.desc, declared.desc)

        from dataclasses import replace

        from elosern_map_core.sparse import SparseSettlementGraph

        capital = SETTLEMENT_GRAPHS["capital_altoria"]
        nodes = [
            replace(
                node,
                prototype={**node.prototype, "desc": "A rebuilt southern gate."},
            )
            if node.node_id == "south_gate"
            else node
            for node in capital.nodes.values()
        ]
        changed_graph = SparseSettlementGraph(
            capital.map_id,
            nodes,
            capital.roads,
            options=capital.options,
            exit_prototype=capital.exit_prototype,
        )
        changed = dict(SETTLEMENT_GRAPHS)
        changed["capital_altoria"] = changed_graph
        with patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", changed):
            sync_grid()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        south_gate = GridRoom.objects.get(db_key="南門")
        self.assertEqual(south_gate.db.desc, "A rebuilt southern gate.")

    @covers_requirement("scene-archetype-mixin::gridroom-is-retrofitted-onto-scenearchetypemixin-without-changing-its-contract")
    def test_anchor_room_matches_placement_registry_after_sync(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

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
        from world.maps.map_data import SETTLEMENT_GRAPHS

        self.assertEqual(
            exits[0].destination.xyz,
            (
                *SETTLEMENT_GRAPHS["capital_altoria"].node("east_market").coordinate,
                "capital_altoria",
            ),
        )

    def test_absent_limbo_degrades_without_raising(self):
        sync_grid()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
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
            self.assertEqual(exit_obj.destination.xyz, settlement_node_xyz(row.gate))

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
    def test_each_settlement_keeps_its_own_coordinate_space(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
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
                sync_grid()
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
            sync_grid()

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

        # The map world (starting room, grid, interiors) converges in the one
        # map-sync step; the lore mirror runs only after it committed.
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_map_world"),
            STARTUP_STEP_ORDER.index("sync_all"),
        )

    def test_at_server_start_without_limbo_syncs_lore_and_grid(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
        self.assertEqual(len(self._bridging_exits()), 0)
        from evennia.utils.search import search_script

        self.assertEqual(len(search_script("lore:anchor_placements:capital_altoria")), 1)

    def test_at_server_start_with_limbo_creates_bridging_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
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
        self.assertEqual(self.char1.location.coordinates, (864, 1080))
        self.char1.move_to(self._east_gate())
        south_gate = self._gate_exits(self._south_gate())[1][0]
        south_gate.at_traverse(self.char1, self._south_gate())
        self.assertEqual(self.char1.location.coordinates, (860, 1077))

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

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_sync_wilderness_materializes_no_frame_rooms(self):
        # The 2700x2700 frame is virtual: boot creates the script and the
        # registered gate exits, never a room per cell.
        from typeclasses.rooms import TerrainRoom

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()

        script, _ = self._gate_exits()
        self.assertEqual(TerrainRoom.objects.count(), 0)
        self.assertEqual(dict(script.db.rooms), {})

    @covers_requirement("wilderness-gateway::physical-footprints-and-concealed-point-entries-preserve-approaches")
    def test_gate_approach_segments_follow_the_authored_physical_geometry(self):
        # The south and east gates measure their own exterior approach segment
        # from the transformed metre position to the approach cell centre; the
        # crossing is one segment, not a full wilderness cell plus a city hop.
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_destination import gate_approach_distance_m

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        south = gate_approach_distance_m(entry, entry.gate_for("n"))
        east = gate_approach_distance_m(entry, entry.gate_for("w"))
        self.assertAlmostEqual(south, 540.83, delta=0.1)
        self.assertAlmostEqual(east, 1012.72, delta=0.1)
        self.assertNotEqual(south, east)
        # Both directions of a crossing measure the single authored segment.
        self.assertEqual(
            gate_approach_distance_m(entry, entry.gate_for("n")), south
        )

    @covers_requirement("wilderness-gateway::physical-footprints-and-concealed-point-entries-preserve-approaches")
    def test_village_point_entrance_has_no_wilderness_footprint(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_provider import WILDERNESS_NAME as NAME

        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertTrue(village.is_point_shape)
        self.assertEqual(village.footprint_cells, frozenset())
        # The anchor cell itself is walkable ground; the point entry is not a
        # village-wide obstacle (only a registered gateway consumes the step).
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_wilderness()
        provider = __import__(
            "world.maps.wilderness_provider", fromlist=["ElosernWildernessMapProvider"]
        ).ElosernWildernessMapProvider()
        create_wilderness(name=NAME, mapprovider=provider)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=village.anchor_cell, name=NAME)
        )

    def test_sync_wilderness_without_east_gate_degrades_gracefully(self):
        sync_wilderness()

        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(WildernessGateExit.objects.all().count(), 0)

    def test_sync_grid_body_is_unmodified(self):
        source = inspect.getsource(sync_grid)
        # The sparse synchronizer is the spawn path; the xyzgrid contrib's
        # dense ``reload()``/``spawn()`` pipeline must not come back.
        self.assertIn("_apply_graph_plan(plan, knowledge_journal)", source)
        self.assertNotIn("grid.spawn()", source)
        self.assertNotIn("get_xyzgrid()", source)
        self.assertNotIn("sync_wilderness", source)

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_at_server_start_calls_sync_wilderness_after_sync_grid(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_map_world"),
            STARTUP_STEP_ORDER.index("sync_wilderness"),
        )

    def test_at_server_start_provisions_wilderness_too(self):
        at_server_start()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
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

        entrance_room = GridRoom.objects.filter_xyz(
            xyz=(
                *settlement_node_xyz(
                    WILDERNESS_ENTRY_REGISTRY["village_ciaran"].gate_for("n").destination
                ),
            )
        ).first()
        gate_exit = [
            e for e in entrance_room.exits if isinstance(e, WildernessGateExit)
        ][0]

        gate_exit.at_traverse(self.char1, entrance_room)
        self.assertEqual(self.char1.location.coordinates, (1366, 554))

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

        from world.maps.room_art import wilderness_scene_identity
        from world.lore.wilderness_regions import regions
        from world.maps.wilderness_provider import (
            region_for_coordinates,
            terrain_description,
        )

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        ok = enter_wilderness(self.char1, coordinates=(864, 1080), name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertEqual(room.ndb.active_desc, terrain_description(864, 1080))
        room.ndb.active_desc = None  # wipe like a restart would
        room.ndb.someother = 1
        # The returned room is retained (account still present); re-running
        # sync_wilderness must re-prepare it.
        sync_wilderness()
        self.assertEqual(room.ndb.active_desc, terrain_description(864, 1080))
        self.assertEqual(
            room.scene_archetype,
            regions()[region_for_coordinates(864, 1080)].scene_archetype,
        )
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, 864, 1080),
        )

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


SYNTHETIC_MAP_KEY = "t_sparse_settlement"


def _synthetic_node(node_id, coordinate, key):
    from elosern_map_core.sparse import SparseNode

    return SparseNode(
        node_id=node_id,
        x=coordinate[0],
        y=coordinate[1],
        prototype={"prototype_parent": "grid_room", "key": key},
    )


def _synthetic_graph(start_coordinate, north_coordinate):
    from elosern_map_core.sparse import SparseRoad, SparseSettlementGraph

    return SparseSettlementGraph(
        SYNTHETIC_MAP_KEY,
        [
            _synthetic_node("start", start_coordinate, "測試起點"),
            _synthetic_node("north", north_coordinate, "測試北端"),
        ],
        [
            SparseRoad("start>north", "start", "north"),
            SparseRoad("north>start", "north", "start"),
        ],
        exit_prototype={
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    )


class SparseSettlementSyncTests(EvenniaTest):
    """Stable-identity convergence over synthetic sparse graphs."""

    def _room(self, xyz):
        return GridRoom.objects.filter_xyz(xyz=xyz).first()

    def _xyz(self, value):
        return tuple(
            int(item) if str(item).lstrip("-").isdigit() else item for item in value
        )

    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_coordinate_replacement_preserves_room_occupant_home_and_references(self):
        from world.maps.bootstrap import SyncReport, sync_settlement_graph

        sync_settlement_graph(_synthetic_graph((1, 1), (1, 2)))
        room = self._room((1, 1, SYNTHETIC_MAP_KEY))
        self.assertIsNotNone(room)
        self.assertEqual(room.sparse_node_id, "start")
        room_id = room.id

        self.char1.location = room
        self.char1.home = room
        self.char1.save()

        external = create_object(Room, key="測試外部", location=None)
        inbound = create_object(Exit, key="測試入口", location=external, destination=room)
        inbound_id = inbound.id
        outbound_roads = {
            exit_obj.destination.key: exit_obj for exit_obj in room.exits
        }
        self.assertEqual(
            set(outbound_roads), {"測試北端"},
        )
        road_exit = outbound_roads["測試北端"]
        road_exit_id = road_exit.id

        sync_settlement_graph(_synthetic_graph((5000, 200), (5000, 201)))
        report = sync_settlement_graph(_synthetic_graph((5000, 200), (5000, 201)))

        moved = self._room((5000, 200, SYNTHETIC_MAP_KEY))
        self.assertEqual(moved.id, room_id)
        self.assertEqual(moved.sparse_node_id, "start")
        self.assertEqual(self.char1.db_location_id, room_id)
        self.assertEqual(self.char1.db_home_id, room_id)
        self.assertEqual(inbound.id, inbound_id)
        self.assertEqual(inbound.db_destination_id, room_id)
        self.assertEqual(report, SyncReport())

        roads = list(moved.exits)
        self.assertEqual(len(roads), 1)
        self.assertEqual(roads[0].id, road_exit_id)
        self.assertEqual(self._xyz(roads[0].xyz), (5000, 200, SYNTHETIC_MAP_KEY))
        self.assertEqual(
            self._xyz(roads[0].xyz_destination), (5000, 201, SYNTHETIC_MAP_KEY)
        )

        north = self._room((5000, 201, SYNTHETIC_MAP_KEY))
        inbound_road = [exit_obj for exit_obj in north.exits if exit_obj.destination == moved]
        self.assertEqual(len(inbound_road), 1)
        self.assertEqual(
            self._xyz(inbound_road[0].xyz_destination), (5000, 200, SYNTHETIC_MAP_KEY)
        )

    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_ambiguous_legacy_room_refuses_before_any_mutation(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import (
            MAP_X_TAG_CATEGORY,
            MAP_Y_TAG_CATEGORY,
            MAP_Z_TAG_CATEGORY,
        )
        from elosern_map_core.sparse import SparseGraphError
        from world.maps.bootstrap import NODE_IDENTITY_TAG_CATEGORY, sync_settlement_graph

        for index in (1, 2):
            create_object(
                GridRoom,
                key=f"測試重複{index}",
                location=None,
                tags=[
                    ("7", MAP_X_TAG_CATEGORY),
                    ("7", MAP_Y_TAG_CATEGORY),
                    (SYNTHETIC_MAP_KEY, MAP_Z_TAG_CATEGORY),
                ],
            )
        before = GridRoom.objects.filter_xyz(
            xyz=("*", "*", SYNTHETIC_MAP_KEY)
        ).count()
        self.assertEqual(before, 2)

        with self.assertRaises(SparseGraphError):
            sync_settlement_graph(_synthetic_graph((7, 7), (7, 8)))

        rooms = list(
            GridRoom.objects.filter_xyz(xyz=("*", "*", SYNTHETIC_MAP_KEY))
        )
        self.assertEqual(len(rooms), 2)
        for room in rooms:
            self.assertIsNone(
                room.tags.get(category=NODE_IDENTITY_TAG_CATEGORY, return_list=False)
            )

    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_moved_identity_cannot_land_on_an_unbound_legacy_room(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import (
            MAP_X_TAG_CATEGORY,
            MAP_Y_TAG_CATEGORY,
            MAP_Z_TAG_CATEGORY,
        )
        from world.maps.bootstrap import sync_settlement_graph
        from elosern_map_core.sparse import SparseGraphError

        sync_settlement_graph(_synthetic_graph((1, 1), (1, 2)))
        moved_identity = self._room((1, 1, SYNTHETIC_MAP_KEY))
        create_object(
            GridRoom,
            key="測試佔位",
            location=None,
            tags=[
                ("9", MAP_X_TAG_CATEGORY),
                ("9", MAP_Y_TAG_CATEGORY),
                (SYNTHETIC_MAP_KEY, MAP_Z_TAG_CATEGORY),
            ],
        )
        occupant = self._room((9, 9, SYNTHETIC_MAP_KEY))

        with self.assertRaises(SparseGraphError):
            sync_settlement_graph(_synthetic_graph((9, 9), (9, 10)))

        self.assertEqual(moved_identity.xyz, (1, 1, SYNTHETIC_MAP_KEY))
        self.assertTrue(
            GridRoom.objects.filter(id=occupant.id).exists(),
        )

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_capital_sparse_graph_spawns_twenty_one_rooms_and_fifty_two_exits(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        sync_grid()
        self.assertEqual(
            GridRoom.objects.filter_xyz(xyz=("*", "*", "capital_altoria")).count(),
            21,
        )
        self.assertEqual(
            XYZExit.objects.filter_xyz(xyz=("*", "*", "capital_altoria")).count(),
            52,
        )


#: The pre-cutover compact bindings, used only to seed a real cutover database.
OLD_COORDINATES = {
    "capital_altoria": {
        "south_gate": (3, 0),
        "quay": (1, 1),
        "riverbank_road": (2, 1),
        "south_avenue": (3, 1),
        "inn_lane": (4, 1),
        "bath_forecourt": (5, 1),
        "old_wall_ruins": (2, 2),
        "north_avenue": (3, 2),
        "craft_alley": (1, 3),
        "market_street": (2, 3),
        "central_plaza": (3, 3),
        "guild_forecourt": (4, 3),
        "east_market": (5, 3),
        "east_gate": (6, 3),
        "training_ground": (2, 4),
        "holy_steps": (3, 4),
        "great_temple": (4, 4),
        "noble_quarter": (3, 5),
        "upper_gate": (4, 5),
        "academy": (5, 5),
        "palace_forecourt": (4, 6),
    },
    "village_ciaran": {
        "hidden_path": (0, 1),
        "village_plaza": (1, 1),
        "stream_path": (1, 0),
        "stream_bend": (2, 0),
        "training_clearing": (2, 1),
        "herb_garden": (3, 1),
        "old_tree_north": (1, 2),
        "elder_tree": (1, 3),
        "weaving_slope": (2, 2),
        "silver_leaf_slope": (2, 3),
    },
}


class MetricCutoverTests(EvenniaTest):
    """The real pre-cutover database converges in place onto metres."""

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _count_city_exits(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        return XYZExit.objects.all_family().count()

    def _seed_precutover_rooms(self):
        from world.maps.bootstrap import NODE_IDENTITY_TAG_CATEGORY

        ids = {}
        for map_id, graph in SETTLEMENT_GRAPHS.items():
            ids[map_id] = {}
            for node_id in graph.nodes:
                coordinate = OLD_COORDINATES[map_id][node_id]
                room, errors = GridRoom.create(
                    key=f"舊{map_id}:{node_id}",
                    xyz=(*coordinate, map_id),
                )
                self.assertFalse(errors, errors)
                room.sparse_node_id = node_id
                room.tags.add(
                    f"{map_id}:{node_id}", category=NODE_IDENTITY_TAG_CATEGORY
                )
                room.save()
                ids[map_id][node_id] = room.id
        return ids

    def _object(self, pk):
        from evennia.objects.models import ObjectDB

        return ObjectDB.objects.get(pk=pk)

    @covers_requirement(
        "map-knowledge::coordinate-cutover-preserves-observations-without-re-observation"
    )
    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_cutover_preserves_identity_references_and_knowledge(self):
        from typeclasses.characters import PlayerCharacter
        from typeclasses.npcs import NPC
        from world.maps.bootstrap import SyncReport
        from world.maps.map_data import SETTLEMENT_GRAPHS

        create_object(Room, key=LIMBO_KEY, location=None)
        ids = self._seed_precutover_rooms()
        plaza_id = ids["capital_altoria"]["central_plaza"]
        plaza = self._object(plaza_id)

        occupant = create_object(NPC, key="測試居民", location=plaza)
        native = create_object(PlayerCharacter, key="測試歸鄉者", location=plaza)
        native.home = plaza
        native.save()
        external = create_object(Room, key="測試外部", location=None)
        inbound = create_object(Exit, key="測試入境", location=external, destination=plaza)
        native.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    "grid:capital_altoria:3:3": {
                        "first_seen_tick": 5,
                        "last_seen_tick": 9,
                    },
                    "grid:capital_altoria:3500:2850": {
                        "first_seen_tick": 7,
                        "last_seen_tick": 11,
                    },
                },
            },
        )

        report = sync_grid()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())
        self.assertGreater(report.updated + report.created, 0)
        moved = self._object(plaza_id)
        self.assertEqual(
            moved.xyz,
            (
                *SETTLEMENT_GRAPHS["capital_altoria"].node("central_plaza").coordinate,
                "capital_altoria",
            ),
        )
        self.assertEqual(occupant.db_location_id, plaza_id)
        self.assertEqual(native.db_location_id, plaza_id)
        self.assertEqual(native.db_home_id, plaza_id)
        self.assertEqual(inbound.db_destination_id, plaza_id)
        self.assertIsNone(
            GridRoom.objects.filter_xyz(xyz=(3, 3, "capital_altoria")).first()
        )

        visits = native.attributes.get("map_knowledge")["visited"]
        self.assertEqual(
            visits,
            {
                "grid:capital_altoria:3500:2850": {
                    "first_seen_tick": 5,
                    "last_seen_tick": 11,
                }
            },
        )

        before = {
            (map_id, node_id): self._object(pk).xyz
            for map_id, nodes in ids.items()
            for node_id, pk in nodes.items()
        }
        second = sync_grid()
        self.assertEqual(second, SyncReport())
        self.assertEqual(
            before,
            {
                (map_id, node_id): self._object(pk).xyz
                for map_id, nodes in ids.items()
                for node_id, pk in nodes.items()
            },
        )

    @covers_requirement(
        "map-knowledge::coordinate-cutover-preserves-observations-without-re-observation"
    )
    def test_failed_cutover_restores_durable_and_cached_state(self):
        from typeclasses.characters import PlayerCharacter
        from world.maps.map_data import SETTLEMENT_GRAPHS
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        create_object(Room, key=LIMBO_KEY, location=None)
        ids = self._seed_precutover_rooms()
        south_id = ids["capital_altoria"]["south_gate"]
        south = self._object(south_id)
        old_xyz = south.xyz

        snapshot = {
            "schema_version": 1,
            "visited": {
                "grid:capital_altoria:3:0": {
                    "first_seen_tick": 1,
                    "last_seen_tick": 2,
                }
            },
        }
        first = create_object(PlayerCharacter, key="測試甲", location=south)
        second = create_object(PlayerCharacter, key="測試乙", location=south)
        first.attributes.add(KNOWLEDGE_ATTR, snapshot)
        second.attributes.add(KNOWLEDGE_ATTR, snapshot)

        import world.rules.map_knowledge as knowledge

        real = knowledge._write_knowledge
        calls = {"n": 0}

        def fail_second(character, record):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected knowledge write fault")
            return real(character, record)

        with patch.object(knowledge, "_write_knowledge", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                sync_grid()

        self.assertEqual(self._object(south_id).xyz, old_xyz)
        self.assertEqual(
            GridRoom.objects.filter_xyz(xyz=(3, 0, "capital_altoria")).first().id,
            south_id,
        )
        for character in (first, second):
            self.assertEqual(character.attributes.get(KNOWLEDGE_ATTR), snapshot)

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_failed_cutover_restores_a_two_settlement_observation(self):
        from typeclasses.characters import PlayerCharacter
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        create_object(Room, key=LIMBO_KEY, location=None)
        ids = self._seed_precutover_rooms()
        observer = create_object(
            PlayerCharacter,
            key="測試雙居者",
            location=self._object(ids["capital_altoria"]["south_gate"]),
        )
        original = {
            "schema_version": 1,
            "visited": {
                "grid:capital_altoria:3:3": {
                    "first_seen_tick": 3,
                    "last_seen_tick": 5,
                },
                "grid:village_ciaran:1:1": {
                    "first_seen_tick": 7,
                    "last_seen_tick": 9,
                },
            },
        }
        observer.attributes.add(KNOWLEDGE_ATTR, original)

        import world.rules.map_knowledge as knowledge

        real = knowledge._write_knowledge
        calls = {"n": 0}

        def fail_second_settlement(character, record):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected second-settlement fault")
            return real(character, record)

        with patch.object(
            knowledge, "_write_knowledge", side_effect=fail_second_settlement
        ):
            with self.assertRaises(RuntimeError):
                sync_grid()

        self.assertEqual(observer.attributes.get(KNOWLEDGE_ATTR), original)

    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_upgrade_removes_retired_ascii_registration_without_deleting_rooms(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        create_object(Room, key=LIMBO_KEY, location=None)
        grid, errors = XYZGrid.create("XYZGrid")
        self.assertFalse(errors, errors)
        grid.db.map_data = {
            "capital_altoria": {
                "zcoord": "capital_altoria",
                "map": "+ 0\n0 #\n+ 0\n",
                "prototypes": {},
            },
            "synthetic_keep": {
                "zcoord": "synthetic_keep",
                "map": "+ 0\n0 #\n+ 0\n",
                "prototypes": {},
            },
        }
        grid.save()

        sync_grid()

        self.assertNotIn("capital_altoria", grid.db.map_data)
        self.assertIn("synthetic_keep", grid.db.map_data)
        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._count_city_exits(), _declared_road_count())

    @covers_requirement(
        "grid-room-sync::sync-grid-runs-automatically-at-server-start-after-sync-all"
    )
    @covers_requirement(
        "map-knowledge::coordinate-cutover-preserves-observations-without-re-observation"
    )
    def test_real_startup_converges_places_scene_art_and_quest_targets(self):
        from evennia.utils.search import search_object_by_tag
        from typeclasses.characters import PlayerCharacter
        from world.lore.settlements.places import PLACE_REGISTRY
        from world.maps.room_art import grid_scene_identity
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        create_object(Room, key=LIMBO_KEY, location=None)
        ids = self._seed_precutover_rooms()
        plaza_id = ids["capital_altoria"]["central_plaza"]
        observer = create_object(
            PlayerCharacter, key="測試旅人", location=self._object(plaza_id)
        )
        observer.attributes.add(
            KNOWLEDGE_ATTR,
            {
                "schema_version": 1,
                "visited": {
                    "grid:capital_altoria:3:3": {
                        "first_seen_tick": 4,
                        "last_seen_tick": 8,
                    }
                },
            },
        )

        at_server_start()

        self.assertEqual(self._count_grid_rooms(), _declared_node_count())
        self.assertEqual(self._object(plaza_id).sparse_node_id, "central_plaza")
        self.assertEqual(
            observer.attributes.get(KNOWLEDGE_ATTR)["visited"],
            {
                "grid:capital_altoria:3500:2850": {
                    "first_seen_tick": 4,
                    "last_seen_tick": 8,
                }
            },
        )
        # Scene-art indices follow the moved room, not a stale coordinate.
        plaza = self._object(plaza_id)
        self.assertEqual(
            plaza.scene_identity,
            grid_scene_identity("capital_altoria", *plaza.xyz[:2]),
        )
        # A quest GRID locator resolves through the new metre coordinate.
        self.assertEqual(
            GridRoom.objects.filter_xyz(
                xyz=(*SETTLEMENT_GRAPHS["capital_altoria"].node("great_temple").coordinate,
                     "capital_altoria")
            ).first().sparse_node_id,
            "great_temple",
        )
        # Every service place's exterior resolves to its converged room and
        # every interior keeps its bidirectional doorway.
        for place in PLACE_REGISTRY.values():
            exterior = GridRoom.objects.filter_xyz(xyz=place_exterior_xyz(place)).first()
            with self.subTest(place=place.key):
                self.assertIsNotNone(exterior)
                interior = search_object_by_tag(place.key)
                self.assertEqual(len(interior), 1)
                self.assertTrue(
                    any(
                        exit_obj.destination == exterior
                        for exit_obj in interior[0].exits
                    )
                )