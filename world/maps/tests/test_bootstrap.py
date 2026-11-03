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
from world.maps.bootstrap import SyncReport, sync_grid, sync_limbo, sync_wilderness
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
from world.tests.geography_fixture import (
    publish_shipped_geography,
    selected_startup_settlements,
    sync_test_settlements,
    sync_test_wilderness,
)


publish_shipped_geography()

_CAPITAL_ENTRY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
_VILLAGE_ENTRY = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
SOUTH_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("n").destination)
EAST_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("w").destination)

#: The capital/village pair every cross-settlement fixture in this module needs.
#: Selector ids are settlement map ids, never entry anchor/location identities.
CAPITAL_MAP_IDS = (_CAPITAL_ENTRY.gate_for("w").destination.map_id,)
VILLAGE_MAP_IDS = (_VILLAGE_ENTRY.gate_for("n").destination.map_id,)
CAPITAL_VILLAGE_MAP_IDS = tuple(sorted({*CAPITAL_MAP_IDS, *VILLAGE_MAP_IDS}))
SELECTED_GATE_ROW_COUNT = sum(
    1
    for row in CITY_GATE_REGISTRY.values()
    if row.gate.map_id in CAPITAL_VILLAGE_MAP_IDS
)
#: The map ids the starting-room bridge rows would materialize.
CITY_GATE_MAP_IDS = tuple(
    sorted({row.gate.map_id for row in CITY_GATE_REGISTRY.values()})
)
#: The destination maps of every registered wilderness gate.
WILDERNESS_GATE_MAP_IDS = tuple(
    sorted(
        {
            gate.destination.map_id
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
    )
)
#: The maps carrying an authored anchor placement.
ANCHOR_PLACEMENT_MAP_IDS = tuple(
    sorted({placement.zcoord for placement in ANCHOR_PLACEMENT_REGISTRY.values()})
)


def _declared_road_count(settlement_ids):
    """The authored directed-road count of the declared settlements."""

    return sum(len(SETTLEMENT_GRAPHS[map_id].edges) for map_id in settlement_ids)


def _declared_node_count(settlement_ids):
    """The authored node count of the declared settlements."""

    return sum(len(SETTLEMENT_GRAPHS[map_id].nodes) for map_id in settlement_ids)


def _approach(return_direction):
    from elosern_map_core.authoring import gate_approach_cell
    from world.maps import geography
    from world.maps.map_data import current

    document = current().settlements["capital_altoria"]
    cell = geography.current().locations.locations["capital_altoria"].cell
    return gate_approach_cell(document.wilderness_geometry(cell), return_direction)


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
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        # The declared pair's authored topology, with no unrelated graph work.
        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        # One forward Limbo bridge per CITY_GATE_REGISTRY row.
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(
            len(self._bridging_exits()) + self._count_city_exits(),
            _declared_road_count(CAPITAL_VILLAGE_MAP_IDS) + SELECTED_GATE_ROW_COUNT,
        )

    def test_sync_grid_is_idempotent_and_preserves_dbid(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        first_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        second_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(first_ids, second_ids)

    def test_single_call_on_fresh_grid_spawns_every_declared_room(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        self.assertEqual(XYZGrid.objects.all().count(), 0)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )

    def test_in_place_update_changes_desc_without_new_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)

        # zhtw-room-prose: the spawn pin asserts the mechanism (the room's desc
        # equals its authored prototype), not the sentence — the prototype's
        # prose is Traditional Chinese like every other shipped room text.
        from world.maps.map_data import current

        declared = current().settlements["capital_altoria"].nodes["south_gate"]
        # A node key is unique inside one map, never across the settled world:
        # several settlements have their own 南門. Resolve the room by the
        # authored coordinate that identifies it.
        xyz = (*declared.coordinate, "capital_altoria")
        south_gate = GridRoom.objects.filter_xyz(xyz=xyz).first()
        self.assertIsNotNone(south_gate)
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
            sync_test_settlements(CAPITAL_MAP_IDS)

        self.assertEqual(self._count_grid_rooms(), _declared_node_count(CAPITAL_MAP_IDS))
        south_gate = GridRoom.objects.filter_xyz(xyz=xyz).first()
        self.assertIsNotNone(south_gate)
        self.assertEqual(south_gate.db.desc, "A rebuilt southern gate.")

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
        with selected_startup_settlements(CAPITAL_VILLAGE_MAP_IDS):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), 0)
        from evennia.utils.search import search_script

        self.assertEqual(len(search_script("lore:anchor_placements:capital_altoria")), 1)

    def test_at_server_start_with_limbo_creates_bridging_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        with selected_startup_settlements(CAPITAL_VILLAGE_MAP_IDS):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), SELECTED_GATE_ROW_COUNT)


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
        from world.maps.map_data import current

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(WILDERNESS_GATE_MAP_IDS)
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS)

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

    def test_sync_wilderness_is_idempotent(self):
        from world.maps.map_data import current

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(WILDERNESS_GATE_MAP_IDS)
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS)
        sync_test_wilderness(WILDERNESS_GATE_MAP_IDS)

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

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_sync_wilderness_materializes_no_frame_rooms(self):
        # The 2700x2700 frame is virtual: boot creates the script and the
        # registered gate exits, never a room per cell.
        from typeclasses.rooms import TerrainRoom

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)

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

        import math

        from elosern_map_core.authoring import gate_approach_cell

        from world.maps import geography
        from world.maps.map_data import current

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        document = current().settlements[entry.anchor_key]
        cell = geography.current().locations.locations[document.location_ref].cell
        anchor_x, anchor_y = document.local_anchor_m

        def authored_segment(return_direction):
            gate = entry.gate_for(return_direction)
            gate_x, gate_y = document.nodes[gate.destination.object_id].coordinate
            gate_world = (
                1000 * cell[0] + 500 + gate_x - anchor_x,
                1000 * cell[1] + 500 + gate_y - anchor_y,
            )
            approach = gate_approach_cell(
                document.wilderness_geometry(cell), return_direction
            )
            return math.dist(
                gate_world, (1000 * approach[0] + 500, 1000 * approach[1] + 500)
            )

        south = gate_approach_distance_m(entry, entry.gate_for("n"))
        east = gate_approach_distance_m(entry, entry.gate_for("w"))
        self.assertAlmostEqual(south, authored_segment("n"))
        self.assertAlmostEqual(east, authored_segment("w"))
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
        sync_test_settlements(VILLAGE_MAP_IDS)
        sync_test_wilderness(VILLAGE_MAP_IDS)
        provider = __import__(
            "world.maps.wilderness_provider", fromlist=["ElosernWildernessMapProvider"]
        ).ElosernWildernessMapProvider()
        create_wilderness(name=NAME, mapprovider=provider)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=village.anchor_cell, name=NAME)
        )

    def test_sync_wilderness_without_east_gate_degrades_gracefully(self):
        sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)

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
        with selected_startup_settlements(CAPITAL_VILLAGE_MAP_IDS):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
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
        sync_test_settlements(VILLAGE_MAP_IDS)
        sync_test_wilderness(VILLAGE_MAP_IDS)

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
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
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
        x, y = _approach("w")
        ok = enter_wilderness(self.char1, coordinates=(x, y), name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertEqual(room.ndb.active_desc, terrain_description(x, y))
        room.ndb.active_desc = None  # wipe like a restart would
        room.ndb.someother = 1
        # The returned room is retained (account still present); re-running
        # sync_wilderness must re-prepare it.
        sync_test_wilderness(CAPITAL_MAP_IDS)
        self.assertEqual(room.ndb.active_desc, terrain_description(x, y))
        self.assertEqual(
            room.scene_archetype,
            regions()[region_for_coordinates(x, y)].scene_archetype,
        )
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, x, y),
        )

    def test_sync_wilderness_heals_miskeyed_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        # Misconfigure the gate's anchor_key, then re-run and confirm it heals.
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        gate = gates[0]
        gate.db.anchor_key = "wrong_anchor"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_misdirected_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        gate = self._gate_exits()[1][0]
        gate.db.gate_direction = "e"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_a_misattributed_single_gate_exit(self):
        # A lone WildernessGateExit with foreign attrs on a gate room IS that
        # room's gate slot: sync heals its (anchor, gate) pair in place rather
        # than stacking a second gate (spec scenario "a mis-provisioned gate
        # is healed").
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        foreign = create_object(
            WildernessGateExit,
            key="荒野",
            location=self._south_gate(),
            destination=self._south_gate(),
        )
        foreign.db.anchor_key = "wrong_anchor"
        foreign.db.gate_direction = "w"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        south_gates = self._gate_exits(self._south_gate())[1]
        self.assertEqual(len(south_gates), 1)
        self.assertIs(south_gates[0], foreign)
        self.assertEqual(foreign.db.anchor_key, "capital_altoria")
        self.assertEqual(foreign.db.gate_direction, "n")

    def test_sync_wilderness_skips_an_ambiguous_multi_row_gate_room(self):
        # Two WildernessGateExit rows on one room are ambiguous: sync warns and
        # provisions nothing there, but still heals/provisions the other gate.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        south_gate = self._south_gate()
        create_object(WildernessGateExit, key="荒野", location=south_gate, destination=south_gate)
        create_object(WildernessGateExit, key="荒野二", location=south_gate, destination=south_gate)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        self.assertEqual(len(self._gate_exits(south_gate)[1]), 2)
        # The unaffected east gate provisions to exactly one exit.
        self.assertEqual(len(self._gate_exits()[1]), 1)

    def test_sync_wilderness_leaves_same_key_foreign_exit_alone(self):
        from typeclasses.exits import Exit

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        # Plant a plain Exit that occupies the gate key.
        east_gate = self._east_gate()
        create_object(
            Exit,
            key="荒野",
            location=east_gate,
            destination=east_gate,
        )
        sync_test_wilderness(CAPITAL_MAP_IDS)
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


def _synthetic_graph_for(map_id, start_coordinate, north_coordinate):
    """One invented sparse graph in its own map coordinate space."""

    from elosern_map_core.sparse import SparseRoad, SparseSettlementGraph

    return SparseSettlementGraph(
        map_id,
        [
            _synthetic_node("start", start_coordinate, f"測試{map_id}起點"),
            _synthetic_node("north", north_coordinate, f"測試{map_id}北端"),
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


class _SynchronizerSpy:
    """Record which graphs reach the real planner and writer, keeping them real."""

    def __enter__(self):
        from world.maps import bootstrap

        self._bootstrap = bootstrap
        self._real_plan = bootstrap._plan_settlement_graph
        self._real_apply = bootstrap._apply_graph_plan
        self.planned = []
        self.applied = []

        def plan(graph):
            self.planned.append(graph.map_id)
            return self._real_plan(graph)

        def apply(plan, knowledge_journal=None):
            self.applied.append(plan.graph.map_id)
            return self._real_apply(plan, knowledge_journal)

        self._plan_patch = patch.object(
            bootstrap, "_plan_settlement_graph", side_effect=plan
        )
        self._apply_patch = patch.object(
            bootstrap, "_apply_graph_plan", side_effect=apply
        )
        self._plan_patch.start()
        self._apply_patch.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._apply_patch.stop()
        self._plan_patch.stop()
        return False


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
    def test_capital_sparse_graph_spawns_one_room_per_node_and_one_exit_per_road(self):
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
        from world.maps.map_data import current

        sync_test_settlements(CAPITAL_MAP_IDS)
        self.assertEqual(
            GridRoom.objects.filter_xyz(xyz=("*", "*", "capital_altoria")).count(),
            len(current().settlements["capital_altoria"].nodes),
        )
        self.assertEqual(
            XYZExit.objects.filter_xyz(xyz=("*", "*", "capital_altoria")).count(),
            len(current().settlements["capital_altoria"].roads),
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


def _plaza_key():
    x, y = SETTLEMENT_GRAPHS["capital_altoria"].node("central_plaza").coordinate
    return f"grid:capital_altoria:{x}:{y}"


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
        for map_id, old_coordinates in OLD_COORDINATES.items():
            ids[map_id] = {}
            for node_id in SETTLEMENT_GRAPHS[map_id].nodes:
                if node_id not in old_coordinates:
                    continue
                coordinate = old_coordinates[node_id]
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
                "schema_version": 2,
                "visited": {
                    "grid:capital_altoria:3:3": {
                        "first_seen_tick": 5,
                        "last_seen_tick": 9,
                    },
                    _plaza_key(): {
                        "first_seen_tick": 7,
                        "last_seen_tick": 11,
                    },
                },
                "wilderness": {},
            },
        )

        report = sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
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
                _plaza_key(): {
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
        second = sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
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
            "schema_version": 2,
            "visited": {
                "grid:capital_altoria:3:0": {
                    "first_seen_tick": 1,
                    "last_seen_tick": 2,
                }
            },
            "wilderness": {},
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
                sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

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
            "schema_version": 2,
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
            "wilderness": {},
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
                sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

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

        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        self.assertNotIn("capital_altoria", grid.db.map_data)
        self.assertIn("synthetic_keep", grid.db.map_data)
        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )

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
                "schema_version": 2,
                "visited": {
                    "grid:capital_altoria:3:3": {
                        "first_seen_tick": 4,
                        "last_seen_tick": 8,
                    }
                },
                "wilderness": {},
            },
        )

        with selected_startup_settlements(CAPITAL_VILLAGE_MAP_IDS):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(self._object(plaza_id).sparse_node_id, "central_plaza")
        self.assertEqual(
            observer.attributes.get(KNOWLEDGE_ATTR)["visited"],
            {
                _plaza_key(): {
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


#: Invented map identities for the selection evidence. None of these exist in
#: the authored world; the tests patch only the synchronizer's graph registry.
ALPHA = "t_selected_alpha"
BETA = "t_selected_beta"
GAMMA = "t_selected_gamma"
DELTA = "t_selected_delta"


def _synthetic_registry(*graphs):
    return {graph.map_id: graph for graph in graphs}


class SelectedSettlementSyncTests(EvenniaTest):
    """Explicit settlement selection through the real planner and writer."""

    def _rooms(self, map_id):
        return list(GridRoom.objects.filter_xyz(xyz=("*", "*", map_id)))

    def _room(self, xyz):
        return GridRoom.objects.filter_xyz(xyz=xyz).first()

    def _alpha(self, start=(1, 1), north=(1, 2)):
        return _synthetic_graph_for(ALPHA, start, north)

    def _beta(self, start=(1, 1), north=(1, 2)):
        return _synthetic_graph_for(BETA, start, north)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_selected_work_is_bounded_and_unrelated_growth_adds_nothing(self):
        alpha = self._alpha()
        beta = self._beta()
        with (
            patch(
                "world.maps.bootstrap.SETTLEMENT_GRAPHS",
                _synthetic_registry(alpha, beta),
            ),
            _SynchronizerSpy() as spy,
        ):
            report = sync_test_settlements((ALPHA,))

        self.assertEqual(spy.planned, [ALPHA])
        self.assertEqual(spy.applied, [ALPHA])
        self.assertGreater(report.created, 0)
        self.assertEqual(len(self._rooms(ALPHA)), 2)
        self.assertEqual(self._rooms(BETA), [])
        alpha_ids = {room.xyz: room.id for room in self._rooms(ALPHA)}

        gamma = _synthetic_graph_for(GAMMA, (7, 7), (7, 8))
        delta = _synthetic_graph_for(DELTA, (9, 9), (9, 10))
        with (
            patch(
                "world.maps.bootstrap.SETTLEMENT_GRAPHS",
                _synthetic_registry(alpha, beta, gamma, delta),
            ),
            _SynchronizerSpy() as spy,
        ):
            repeat = sync_test_settlements((ALPHA,))

        self.assertEqual(spy.planned, [ALPHA])
        self.assertEqual(spy.applied, [ALPHA])
        self.assertEqual(repeat, SyncReport())
        self.assertEqual(
            {room.xyz: room.id for room in self._rooms(ALPHA)}, alpha_ids
        )
        self.assertEqual(self._rooms(GAMMA), [])
        self.assertEqual(self._rooms(DELTA), [])

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_unknown_and_malformed_selections_reject_before_planning(self):
        alpha = self._alpha()
        registry = _synthetic_registry(alpha)
        with patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", registry):
            sync_test_settlements((ALPHA,))
            before_rooms = {
                (room.id, tuple(room.xyz)) for room in GridRoom.objects.all_family()
            }
            before_exits = {exit_obj.id for exit_obj in Exit.objects.all()}
            before_tags = set(
                self._room((1, 1, ALPHA)).tags.all()
            )

            with _SynchronizerSpy() as spy:
                with self.assertRaises(KeyError) as unknown:
                    sync_test_settlements((ALPHA, "t_missing_map"))
                self.assertIn("t_missing_map", str(unknown.exception))
                for malformed in ("t_selected_alpha", (ALPHA, 7)):
                    with self.assertRaises(TypeError):
                        sync_test_settlements(malformed)

            self.assertEqual(spy.planned, [])
            self.assertEqual(spy.applied, [])

        self.assertEqual(
            {(room.id, tuple(room.xyz)) for room in GridRoom.objects.all_family()},
            before_rooms,
        )
        self.assertEqual({exit_obj.id for exit_obj in Exit.objects.all()}, before_exits)
        self.assertEqual(set(self._room((1, 1, ALPHA)).tags.all()), before_tags)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_selection_is_deduplicated_sorted_and_one_shot(self):
        alpha = self._alpha()
        beta = self._beta()
        with (
            patch(
                "world.maps.bootstrap.SETTLEMENT_GRAPHS",
                _synthetic_registry(alpha, beta),
            ),
            _SynchronizerSpy() as spy,
        ):
            one_shot = (map_id for map_id in (BETA, ALPHA, BETA))
            sync_test_settlements(one_shot)

        self.assertEqual(spy.planned, [ALPHA, BETA])
        self.assertEqual(spy.applied, [ALPHA, BETA])
        self.assertEqual(len(self._rooms(ALPHA)), 2)
        self.assertEqual(len(self._rooms(BETA)), 2)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_explicit_empty_selection_performs_no_persistent_work(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        unrelated = create_object(Room, key="測試無關房", location=None)
        reverse = create_object(
            Exit, key="測試回虛境", location=unrelated, destination=limbo
        )
        grid, errors = XYZGrid.create("XYZGrid")
        self.assertFalse(errors, errors)
        grid.db.map_data = {
            ALPHA: {
                "zcoord": ALPHA,
                "map": "+ 0\n0 #\n+ 0\n",
                "prototypes": {},
            }
        }
        grid.save()

        sync_test_settlements(())
        sync_test_wilderness(())

        self.assertEqual(GridRoom.objects.all_family().count(), 0)
        self.assertEqual(list(limbo.exits), [])
        self.assertTrue(Exit.objects.filter(id=reverse.id).exists())
        self.assertIn(ALPHA, grid.db.map_data)
        self.assertEqual(
            WildernessScript.objects.filter(db_key=WILDERNESS_NAME).count(), 0
        )

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_selected_batch_failure_rolls_back_both_settlements(self):
        from typeclasses.characters import PlayerCharacter
        from typeclasses.npcs import NPC
        from world.maps import bootstrap
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        baseline_alpha = self._alpha()
        baseline_beta = self._beta()
        with patch(
            "world.maps.bootstrap.SETTLEMENT_GRAPHS",
            _synthetic_registry(baseline_alpha, baseline_beta),
        ):
            sync_test_settlements((ALPHA, BETA))

        alpha_room = self._room((1, 1, ALPHA))
        beta_room = self._room((1, 1, BETA))
        alpha_room_id = alpha_room.id
        beta_room_id = beta_room.id
        occupant = create_object(NPC, key="測試居民", location=alpha_room)
        native = create_object(PlayerCharacter, key="測試歸鄉者", location=alpha_room)
        native.home = alpha_room
        native.save()
        external = create_object(Room, key="測試外部", location=None)
        inbound = create_object(
            Exit, key="測試入境", location=external, destination=alpha_room
        )
        original_knowledge = {
            "schema_version": 2,
            "visited": {
                f"grid:{ALPHA}:1:1": {
                    "first_seen_tick": 5,
                    "last_seen_tick": 9,
                }
            },
            "wilderness": {},
        }
        native.attributes.add(KNOWLEDGE_ATTR, original_knowledge)

        moved_alpha = self._alpha(start=(2, 1), north=(2, 2))
        moved_beta = self._beta(start=(2, 1), north=(2, 2))
        real_apply = bootstrap._apply_graph_plan

        def fail_on_second(plan, knowledge_journal=None):
            if plan.graph.map_id == BETA:
                raise RuntimeError("injected late write fault")
            return real_apply(plan, knowledge_journal)

        with (
            patch(
                "world.maps.bootstrap.SETTLEMENT_GRAPHS",
                _synthetic_registry(moved_alpha, moved_beta),
            ),
            patch.object(
                bootstrap, "_apply_graph_plan", side_effect=fail_on_second
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_test_settlements((ALPHA, BETA))

        self.assertEqual(self._object(alpha_room_id).xyz, (1, 1, ALPHA))
        self.assertEqual(self._object(beta_room_id).xyz, (1, 1, BETA))
        self.assertEqual(occupant.db_location_id, alpha_room_id)
        self.assertEqual(native.db_location_id, alpha_room_id)
        self.assertEqual(native.db_home_id, alpha_room_id)
        self.assertEqual(inbound.db_destination_id, alpha_room_id)
        self.assertEqual(
            native.attributes.get(KNOWLEDGE_ATTR), original_knowledge
        )

    def _object(self, pk):
        from evennia.objects.models import ObjectDB

        return ObjectDB.objects.get(pk=pk)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_ancillary_work_respects_the_selection_and_global_prune_stays(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid
        from world.maps import bootstrap
        from world.maps.room_art import GRID_NODE_SCENE_ARCHETYPES

        capital = CAPITAL_MAP_IDS[0]
        village = VILLAGE_MAP_IDS[0]
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        capital_row = next(
            row for row in CITY_GATE_REGISTRY.values() if row.gate.map_id == capital
        )
        village_row = next(
            row for row in CITY_GATE_REGISTRY.values() if row.gate.map_id == village
        )
        capital_forward = next(
            exit_obj for exit_obj in limbo.exits if exit_obj.key == capital_row.exit_key
        )
        village_forward = next(
            exit_obj for exit_obj in limbo.exits if exit_obj.key == village_row.exit_key
        )
        capital_forward.key = "drifted capital"
        capital_forward.save()
        village_forward.key = "drifted village"
        village_forward.save()

        capital_reference, capital_scene = next(
            (reference, scene)
            for reference, scene in GRID_NODE_SCENE_ARCHETYPES.items()
            if reference.map_id == capital
        )
        village_reference, village_scene = next(
            (reference, scene)
            for reference, scene in GRID_NODE_SCENE_ARCHETYPES.items()
            if reference.map_id == village
        )
        capital_art_room = self._room(
            (*settlement_node_xyz(capital_reference),)
        )
        village_art_room = self._room(
            (*settlement_node_xyz(village_reference),)
        )
        capital_art_room.scene_archetype = "drifted capital art"
        capital_art_room.save()
        village_art_room.scene_archetype = "drifted village art"
        village_art_room.save()
        village_art_room.db.desc = "drifted village prose"
        village_art_room.save()
        village_exit = list(village_art_room.exits)[0]
        village_exit.key = "drifted village road"
        village_exit.save()

        grid, errors = XYZGrid.create("XYZGrid")
        self.assertFalse(errors, errors)
        grid.db.map_data = {
            capital: {
                "zcoord": capital,
                "map": "+ 0\n0 #\n+ 0\n",
                "prototypes": {},
            },
            village: {
                "zcoord": village,
                "map": "+ 0\n0 #\n+ 0\n",
                "prototypes": {},
            },
        }
        grid.save()

        reverse = create_object(
            Exit, key="測試村回虛境", location=village_art_room, destination=limbo
        )
        reverse_id = reverse.id
        unmaterialized = CityGateDef(
            gate=settlement_node_ref(village, "hidden_path"),
            exit_key="測試未佈建門",
            exit_aliases=("未佈建",),
        )
        rebound = dict(CITY_GATE_REGISTRY)
        rebound["unmaterialized"] = unmaterialized
        real_resolve = settlement_node_xyz

        def resolve(reference, **kwargs):
            if reference == unmaterialized.gate:
                return (999, 999, village)
            return real_resolve(reference, **kwargs)

        with (
            patch("world.maps.bootstrap.CITY_GATE_REGISTRY", rebound),
            patch("world.maps.bootstrap.settlement_node_xyz", side_effect=resolve),
            patch("world.maps.bootstrap.log_warn") as warn,
            patch("world.maps.bootstrap.log_info") as info,
        ):
            sync_test_settlements(CAPITAL_MAP_IDS)

        missing = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "bootstrap_grid_gate_missing"
        ]
        self.assertEqual(missing, [])
        self.assertNotIn(capital, grid.db.map_data)
        self.assertIn(village, grid.db.map_data)
        self.assertEqual(capital_art_room.scene_archetype, capital_scene)
        self.assertEqual(village_art_room.scene_archetype, "drifted village art")
        self.assertEqual(village_art_room.db.desc, "drifted village prose")
        self.assertEqual(village_exit.key, "drifted village road")
        self.assertTrue(Exit.objects.filter(id=village_forward.id).exists())
        self.assertEqual(
            Exit.objects.get(id=village_forward.id).key, "drifted village"
        )
        self.assertEqual(
            next(
                exit_obj.key
                for exit_obj in limbo.exits
                if exit_obj.destination == capital_forward.destination
            ),
            capital_row.exit_key,
        )
        self.assertFalse(Exit.objects.filter(id=reverse_id).exists())
        prunes = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "bootstrap_grid_exit_pruned"
        ]
        self.assertEqual(len(prunes), 1)
        self.assertEqual(prunes[0].kwargs["context"]["source_room_key"], village_art_room.key)

    @covers_requirement(
        "grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits"
    )
    def test_default_selection_materializes_every_graph_and_runtime_stays_selector_free(self):
        from world.maps import bootstrap, runtime

        alpha = self._alpha()
        beta = self._beta()
        with (
            patch(
                "world.maps.bootstrap.SETTLEMENT_GRAPHS",
                _synthetic_registry(alpha, beta),
            ),
            _SynchronizerSpy() as spy,
        ):
            sync_grid()

        self.assertEqual(spy.planned, [ALPHA, BETA])
        self.assertEqual(spy.applied, [ALPHA, BETA])
        self.assertEqual(len(self._rooms(ALPHA)), 2)
        self.assertEqual(len(self._rooms(BETA)), 2)

        with (
            patch.object(bootstrap, "sync_limbo"),
            patch.object(bootstrap, "sync_grid") as grid_call,
            patch.object(bootstrap, "sync_interiors"),
            patch.object(runtime, "ensure_published", return_value=object()),
            patch.object(runtime, "commit_adoption"),
        ):
            runtime.synchronize()
        grid_call.assert_called_once_with()

    @covers_requirement(
        "grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits"
    )
    def test_cold_process_default_sync_publishes_before_reading_the_registry(self):
        from world.maps import runtime

        runtime.clear_published_world()
        self.addCleanup(runtime.ensure_published)
        alpha = self._alpha()
        with patch(
            "world.maps.bootstrap.SETTLEMENT_GRAPHS",
            _synthetic_registry(alpha),
        ):
            sync_grid()
        self.assertTrue(runtime.is_published())
        self.assertEqual(len(self._rooms(ALPHA)), 2)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_wilderness_selection_uses_destination_map_identity(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
        from world.maps import bootstrap

        alpha = self._alpha()
        beta = self._beta()
        entries = {
            "t_anchor_alpha": WildernessEntryPoint(
                anchor_key="t_anchor_alpha",
                shape=("#",),
                origin_xy=(500, 500),
                gates=(
                    WildernessGate("w", settlement_node_ref(ALPHA, "start")),
                ),
            ),
            "t_anchor_beta": WildernessEntryPoint(
                anchor_key="t_anchor_beta",
                shape=("#",),
                origin_xy=(700, 700),
                gates=(
                    WildernessGate("w", settlement_node_ref(BETA, "start")),
                ),
            ),
        }
        graphs = _synthetic_registry(alpha, beta)
        coordinates = {
            ALPHA: settlement_node_ref(ALPHA, "start"),
            BETA: settlement_node_ref(BETA, "start"),
        }

        def resolve(reference, **kwargs):
            if reference in coordinates.values():
                graph = alpha if reference.map_id == ALPHA else beta
                x, y = graph.node("start").coordinate
                return (x, y, reference.map_id)
            from world.maps.static_references import settlement_node_xyz as real

            return real(reference, **kwargs)

        with (
            patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", graphs),
            patch("world.maps.bootstrap.WILDERNESS_ENTRY_REGISTRY", entries),
            patch("world.maps.bootstrap.settlement_node_xyz", side_effect=resolve),
        ):
            sync_test_settlements((ALPHA, BETA))
            sync_test_wilderness((ALPHA,))

            alpha_gate = self._room((1, 1, ALPHA))
            alpha_exits = [
                exit_obj
                for exit_obj in alpha_gate.exits
                if isinstance(exit_obj, WildernessGateExit)
            ]
            self.assertEqual(len(alpha_exits), 1)
            self.assertEqual(alpha_exits[0].db.anchor_key, "t_anchor_alpha")
            self.assertEqual(
                [
                    exit_obj
                    for exit_obj in self._room((1, 1, BETA)).exits
                    if isinstance(exit_obj, WildernessGateExit)
                ],
                [],
            )

            sync_wilderness()
            for map_id in (ALPHA, BETA):
                gate_room = self._room((1, 1, map_id))
                self.assertEqual(
                    len(
                        [
                            exit_obj
                            for exit_obj in gate_room.exits
                            if isinstance(exit_obj, WildernessGateExit)
                        ]
                    ),
                    1,
                )
        self.assertEqual(
            WildernessScript.objects.filter(db_key=WILDERNESS_NAME).count(), 1
        )
        self.assertIs(
            bootstrap.WILDERNESS_ENTRY_REGISTRY, WILDERNESS_ENTRY_REGISTRY
        )

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_adapter_forwards_a_frozen_declaration_and_restores_bindings(self):
        from world.maps import bootstrap

        alpha = self._alpha()
        beta = self._beta()
        real_grid = bootstrap.sync_grid
        real_wilderness = bootstrap.sync_wilderness
        with patch(
            "world.maps.bootstrap.SETTLEMENT_GRAPHS",
            _synthetic_registry(alpha, beta),
        ):
            with selected_startup_settlements(
                map_id for map_id in (BETA, ALPHA, BETA)
            ):
                with _SynchronizerSpy() as spy:
                    bootstrap.sync_grid()
                bootstrap.sync_wilderness()
        self.assertEqual(spy.planned, [ALPHA, BETA])
        self.assertEqual(spy.applied, [ALPHA, BETA])
        self.assertIs(bootstrap.sync_grid, real_grid)
        self.assertIs(bootstrap.sync_wilderness, real_wilderness)

        try:
            with selected_startup_settlements((next(iter(SETTLEMENT_GRAPHS)),)):
                raise RuntimeError("injected startup failure")
        except RuntimeError:
            pass
        self.assertIs(bootstrap.sync_grid, real_grid)
        self.assertIs(bootstrap.sync_wilderness, real_wilderness)

    @covers_requirement(
        "grid-room-sync::explicit-settlement-selection-bounds-test-synchronization"
    )
    def test_adapter_requires_an_argument_and_preserves_the_published_bundle(self):
        from world.maps import runtime

        with self.assertRaises(TypeError):
            sync_test_settlements()
        with self.assertRaises(TypeError):
            sync_test_wilderness()
        with self.assertRaises(TypeError):
            selected_startup_settlements()

        before = runtime.current()
        alpha = self._alpha()
        with patch(
            "world.maps.bootstrap.SETTLEMENT_GRAPHS",
            _synthetic_registry(alpha),
        ):
            sync_test_settlements((ALPHA,))
        self.assertIs(runtime.current(), before)