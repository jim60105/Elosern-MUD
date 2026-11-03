"""Data-contract test: city movement cost data contract
Integration tests for wiring CostedXYZExit into the sample city (map-movement-clock)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import CostedXYZExit, Exit
from typeclasses.rooms import GridRoom, Room
from world.lore.sync import sync_all
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.limbo import LIMBO_KEY
from world.maps.static_references import settlement_node_xyz
from world.rules.clock import CLOCK_YAML, get_world_clock

from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.tests.geography_fixture import (
    publish_shipped_geography,
    sync_test_settlements,
)

publish_shipped_geography()

SOUTH_GATE_XYZ = settlement_node_xyz(
    WILDERNESS_ENTRY_REGISTRY["capital_altoria"].gate_for("n").destination
)

MOVE = CLOCK_YAML["command_defaults"]["move"]

# The village's authored physical duration (world-map-scale §8/§9) at the
# settlement 1.25 m/s calibration, rounded upward once; the capital's own
# duration is checked against the authored polyline instead.
HIDDEN_PATH_TO_PLAZA_SECONDS = 394

SYNTHETIC_COST_MAPS = ("t_cost_path", "t_cost_spur")


def _synthetic_cost_graphs():
    """Invented graphs with independently known directed-road counts."""

    from elosern_map_core.sparse import SparseNode, SparseRoad, SparseSettlementGraph

    def node(node_id, x, y):
        return SparseNode(
            node_id=node_id,
            x=x,
            y=y,
            prototype={"prototype_parent": "grid_room", "key": f"測試{node_id}"},
        )

    path = SparseSettlementGraph(
        SYNTHETIC_COST_MAPS[0],
        [node("a", 1, 1), node("b", 1, 2), node("c", 1, 3)],
        [
            SparseRoad("a>b", "a", "b"),
            SparseRoad("b>c", "b", "c"),
            SparseRoad("c>a", "c", "a"),
        ],
        exit_prototype={
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    )
    spur = SparseSettlementGraph(
        SYNTHETIC_COST_MAPS[1],
        [node("s", 5, 5), node("t", 5, 6)],
        [SparseRoad("s>t", "s", "t")],
        exit_prototype={
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    )
    return {path.map_id: path, spur.map_id: spur}, {path.map_id: 3, spur.map_id: 1}


def _polyline_metres(points):
    """Authored length only; the charged seconds come from the clock, never from here."""
    import math

    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


class _ChargeAssertions:
    def assertChargedFor(self, delta, metres):
        """The spec's healthy settlement speed is 1.25 m/s with one upward rounding."""
        self.assertGreater(delta, 0)
        self.assertLess((delta - 1) * 1.25, metres)
        self.assertLessEqual(metres, delta * 1.25)


class SampleCityCostedExitTests(_ChargeAssertions, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="Room3", location=None)

    def _intra_city_exits(self):
        # all_family() counts CostedXYZExit (exact-typeclass all() filters them out).
        return [obj for obj in XYZExit.objects.all_family()]

    def test_fresh_spawn_every_intra_city_exit_is_costed_xyz_exit(self):
        graphs, expected_roads = _synthetic_cost_graphs()
        with patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", graphs):
            sync_test_settlements(SYNTHETIC_COST_MAPS)
        exits = self._intra_city_exits()
        # Every invented directed road spawns the costed exit; the independently
        # declared per-map counts would fail if one map were silently skipped.
        self.assertEqual(len(exits), sum(expected_roads.values()))
        for map_id, expected in expected_roads.items():
            self.assertEqual(
                len(
                    [
                        exit_obj
                        for exit_obj in exits
                        if exit_obj.destination.xyz[2] == map_id
                    ]
                ),
                expected,
            )
        for exit_obj in exits:
            self.assertIsInstance(exit_obj, CostedXYZExit)

    def test_retype_path_updates_db_row_but_not_loaded_objects(self):
        # First sync WITHOUT the wildcard override: bare XYZExit instances.
        from elosern_map_core.sparse import SparseSettlementGraph

        capital = SETTLEMENT_GRAPHS["capital_altoria"]
        bare_graph = SparseSettlementGraph(
            capital.map_id,
            capital.nodes.values(),
            capital.roads,
            options=capital.options,
            exit_prototype={},
        )
        without_override = {"capital_altoria": bare_graph}
        with patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", without_override):
            sync_test_settlements((capital.map_id,))

        loaded = self._intra_city_exits()
        self.assertEqual(len(loaded), len(capital.roads))
        for exit_obj in loaded:
            self.assertEqual(type(exit_obj).__name__, "XYZExit")

        # Second sync WITH the wildcard override.
        sync_test_settlements((capital.map_id,))
        for exit_obj in loaded:
            self.assertEqual(
                exit_obj.db_typeclass_path, "typeclasses.exits.CostedXYZExit"
            )
            # The already-loaded Python object is not retyped in this process
            # (spawner.batch_update_objects_with_prototype writes the raw field;
            # it never calls swap_typeclass).
            self.assertEqual(type(exit_obj).__name__, "XYZExit")

        # A traversal through one of the still-loaded bare objects does not charge.
        exit_obj = loaded[0]
        traverser_location = exit_obj.location
        destination = exit_obj.destination
        before = get_world_clock().tick
        self.char1.location = traverser_location
        exit_obj.at_traverse(self.char1, destination)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement(
        "movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry",
        "movement-cost-charging::typeclasses-exits-exit-and-costedxyzexit-both-carry-movementcostmixin-with",
    )
    def test_fresh_intra_city_traversal_advances_clock_by_move(self):
        from world.maps.map_data import current

        sync_test_settlements((SETTLEMENT_GRAPHS["capital_altoria"].map_id,))
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.char1.location = south_gate
        city_exit = next(e for e in south_gate.exits if isinstance(e, CostedXYZExit))
        self.assertIsInstance(city_exit, CostedXYZExit)
        document = current().settlements["capital_altoria"]
        road = next(
            road
            for road in document.roads
            if road.source == south_gate.sparse_node_id
            and road.destination == city_exit.destination.sparse_node_id
        )
        points = [
            document.nodes[road.source].coordinate,
            *[(bend.x_m, bend.y_m) for bend in road.bends],
            document.nodes[road.destination].coordinate,
        ]
        before = get_world_clock().tick
        city_exit.at_traverse(self.char1, city_exit.destination)
        self.assertEqual(self.char1.location, city_exit.destination)
        # A settlement edge charges its authored physical duration, not the
        # flat non-distance connector default.
        delta = get_world_clock().tick - before
        self.assertChargedFor(delta, _polyline_metres(points))
        self.assertNotEqual(delta, MOVE)

    @covers_requirement(
        "movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry",
        "world-clock::move-and-converse-command-default-time-costs-are-declared-as-rulebook-data-only",
    )
    def test_village_traversal_advances_clock_by_move_like_city_movement(self):
        # The village's wildcard link override spawns CostedXYZExit for every
        # intra-village link, and each step charges the same physical-edge
        # calculation as a capital street step.
        sync_test_settlements(
            (
                WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
                .gate_for("n")
                .destination.map_id,
            )
        )
        village_entrance = settlement_node_xyz(
            WILDERNESS_ENTRY_REGISTRY["village_ciaran"].gate_for("n").destination
        )
        entrance = GridRoom.objects.filter_xyz(xyz=village_entrance).first()
        self.char1.location = entrance
        village_exit = [e for e in entrance.exits if e.destination.key == "村中廣場"][0]
        self.assertIsInstance(village_exit, CostedXYZExit)
        before = get_world_clock().tick
        village_exit.at_traverse(self.char1, village_exit.destination)
        self.assertEqual(self.char1.location.key, "村中廣場")
        self.assertEqual(
            get_world_clock().tick, before + HIDDEN_PATH_TO_PLAZA_SECONDS
        )

    @covers_requirement("sample-city-altoria::the-sample-city-s-declared-intra-city-exits-spawn-as-costedxyzexit", "world-clock::move-and-converse-command-default-time-costs-are-declared-as-rulebook-data-only")
    def test_limbo_bridge_exit_advances_clock_on_successful_traversal(self):
        sync_test_settlements(
            (WILDERNESS_ENTRY_REGISTRY["capital_altoria"].gate_for("n").destination.map_id,)
        )
        limbo = self.room2
        limbo.key = LIMBO_KEY
        limbo.save()
        sync_test_settlements(
            (WILDERNESS_ENTRY_REGISTRY["capital_altoria"].gate_for("n").destination.map_id,)
        )
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        from_each = [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location == limbo and exit_obj.destination == south_gate
        ]
        self.assertEqual(len(from_each), 1)
        exit_obj = from_each[0]
        self.assertIsInstance(exit_obj, Exit)
        before = get_world_clock().tick
        self.char1.location = limbo
        exit_obj.at_traverse(self.char1, south_gate)
        self.assertIs(self.char1.location, south_gate)
        self.assertEqual(get_world_clock().tick, before + MOVE)
