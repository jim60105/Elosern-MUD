"""Data-contract test: map bootstrap/gate data contract

The shipped-scale convergence cases: one class per worker-sized unit, kept
apart from the local fixture cases so a four-worker job can run them in
parallel without serializing two whole-world passes onto one worker.
"""

from tools.spec_traceability import covers_requirement


from evennia.utils.create import create_object

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.limbo import LIMBO_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import (
    anchor_entrance_xyz,
    settlement_node_xyz,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.maps.bootstrap import sync_grid
from world.tests.geography_fixture import (
    first_entrance_ref,
    sync_test_settlements,
    sync_test_wilderness,
)
from world.maps.tests._bootstrap_fixtures import (
    ANCHOR_PLACEMENT_MAP_IDS,
    CAPITAL_MAP_IDS,
    CAPITAL_VILLAGE_MAP_IDS,
    EAST_GATE_XYZ,
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
    """Starting-room isolation, gate exits and startup cases."""

    def test_sync_grid_creates_no_exit_touching_the_starting_room(self):
        from evennia.objects.models import ObjectDB

        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid(settlement_ids=(first_entrance_ref().map_id,))

        self.assertGreater(self._count_grid_rooms(), 0)
        self.assertEqual(list(limbo.exits), [])
        self.assertFalse(
            any(
                isinstance(obj, Exit)
                for obj in ObjectDB.objects.filter(db_destination=limbo.id)
            )
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
        self.assertEqual(self._bridging_exits(), [])

    @covers_requirement(
        "village-ciaran-map::the-village-has-exactly-one-concealed-entrance"
    )
    @covers_requirement("limbo-one-way-gates::every-sync-prunes-every-exit-whose-destination-is-the-starting-room")
    def test_no_exit_joins_the_starting_room_and_the_village(self):
        limbo = create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        village_rooms = list(
            GridRoom.objects.filter_xyz(xyz=("*", "*", "elven_village_ciaran"))
        )
        self.assertTrue(village_rooms)
        self.assertEqual(
            [exit_obj for exit_obj in limbo.exits if exit_obj.destination in village_rooms],
            [],
        )
        for room in village_rooms:
            self.assertEqual(
                [exit_obj for exit_obj in room.exits if exit_obj.destination == limbo],
                [],
                f"{room.key} at {room.xyz} holds an exit into 虛境",
            )

    @covers_requirement("grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits")
    def test_each_settlement_keeps_its_own_coordinate_space(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        # The metre frames are disjoint: each settlement's coordinates resolve
        # only inside its own map key, never into the other's rooms.
        for map_key, node_id, key in (
            ("capital_altoria", "riverbank_road", "河岸道"),
            ("elven_village_ciaran", "training_clearing", "練刀場"),
        ):
            coordinate = SETTLEMENT_GRAPHS[map_key].node(node_id).coordinate
            room = GridRoom.objects.filter_xyz(xyz=(*coordinate, map_key)).first()
            self.assertIsNotNone(room)
            self.assertEqual(room.key, key)
            other_map = (
                "elven_village_ciaran" if map_key == "capital_altoria" else "capital_altoria"
            )
            self.assertIsNone(
                GridRoom.objects.filter_xyz(xyz=(*coordinate, other_map)).first()
            )


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
            WILDERNESS_ENTRY_REGISTRY["elven_village_ciaran"].gate_for("n").destination
        )
        village_gate_exits = [
            e for e in GridRoom.objects.filter_xyz(xyz=village_entrance).first().exits
            if isinstance(e, WildernessGateExit)
        ]
        self.assertEqual(len(village_gate_exits), 1)
        self.assertEqual(village_gate_exits[0].key, "荒野")
        self.assertEqual(village_gate_exits[0].db.anchor_key, "elven_village_ciaran")
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
