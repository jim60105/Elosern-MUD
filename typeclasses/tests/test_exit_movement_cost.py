"""Integration tests for MovementCostMixin exit charging (map-movement-clock)."""

from tools.spec_traceability import covers_requirement

import evennia
from unittest.mock import MagicMock
from evennia.server.serversession import ServerSession
from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.exits import CostedXYZExit, Exit, MovementCostMixin
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()

MOVE = CLOCK_YAML["command_defaults"]["move"]


class FlightRequiredExit(Exit):
    """A module-level flight-gated exit, importable for typeclass creation."""

    requires_flight = True


class MovementCostExitTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    @covers_requirement("movement-settlement-atomicity::movement-settles-relocation-clock-cost-map-knowledge-and-companion-following-as-one-coherent-transaction")
    def test_player_traversing_plain_exit_advances_clock_by_move(self):
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    def test_locked_exit_leaves_location_and_clock_unchanged(self):
        from evennia.objects.objects import ExitCommand

        exit_obj = create_object(Exit, key="locked", location=self.room1, destination=self.room2)
        exit_obj.locks.add("traverse:false()")
        self.assertFalse(exit_obj.access(self.char1, "traverse"))
        before = get_world_clock().tick
        command = ExitCommand()
        command.obj = exit_obj
        command.caller = self.char1
        command.func()
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_vetoed_at_pre_move_leaves_location_and_clock_unchanged(self):
        exit_obj = create_object(Exit, key="veto", location=self.room1, destination=self.room2)
        self.char1.at_pre_move = lambda *a, **k: False
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    def test_costed_xyz_exit_is_a_working_xyz_exit_that_charges(self):
        room_a, _ = GridRoom.create(key="A", xyz=(5, 5, "cost_map"))
        room_b, _ = GridRoom.create(key="B", xyz=(6, 5, "cost_map"))
        exit_obj, errors = CostedXYZExit.create(
            key="link", location=room_a, destination=room_b
        )
        self.assertEqual(errors, [])
        self.assertIsInstance(exit_obj, XYZExit)
        self.assertIsInstance(exit_obj, CostedXYZExit)

        self.char1.location = room_a
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, room_b)
        self.assertIs(self.char1.location, room_b)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("movement-cost-charging::movement-charges-only-for-a-player-driven-traverser-never-for-an-autonomous-npc")
    def test_npc_traversal_moves_but_does_not_advance_clock(self):
        exit_obj = create_object(Exit, key="npc_door", location=self.room1, destination=self.room2)
        npc = create_object(NPC, key="npc", location=self.room1)
        before = get_world_clock().tick
        exit_obj.at_traverse(npc, self.room2)
        self.assertIs(npc.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::movement-charges-only-for-a-player-driven-traverser-never-for-an-autonomous-npc")
    def test_possessed_npc_traversing_exit_charges_clock(self):
        """Scenario: A possessed NPC traversing the same exit charges the clock."""
        exit_obj = create_object(Exit, key="npc_door_p", location=self.room1, destination=self.room2)
        npc = create_object(NPC, key="possessed_npc", location=self.room1)
        npc.db.possessed_by = self.char1.pk
        session = ServerSession()
        session.sessionhandler = evennia.SESSION_HANDLER
        session.data_out = MagicMock()
        session.sessid = 99993
        evennia.SESSION_HANDLER[session.sessid] = session
        npc.sessions.add(session)
        try:
            before = get_world_clock().tick
            exit_obj.at_traverse(npc, self.room2)
            self.assertIs(npc.location, self.room2)
            self.assertEqual(get_world_clock().tick, before + MOVE)
        finally:
            npc.sessions.remove(session)
            evennia.SESSION_HANDLER.pop(session.sessid, None)

    def test_teleport_style_move_to_does_not_advance_clock(self):
        before = get_world_clock().tick
        self.char1.move_to(self.room2, move_type="teleport")
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::movement-never-charges-through-a-teleport-spawn-or-non-exit-relocation")
    def test_quiet_relocation_style_move_to_does_not_advance_clock(self):
        before = get_world_clock().tick
        self.char1.move_to(self.room2, quiet=True)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)


class PhysicalEdgeExitTests(EvenniaTest):
    """A settlement exit charges the authored physical edge, not the flat default."""

    def setUp(self):
        super().setUp()
        from math import ceil

        from world.maps.bootstrap import sync_grid
        from world.maps.map_data import SETTLEMENT_GRAPHS
        from world.rules.travel_cost import TERRAIN_SPEEDS

        sync_grid()
        graph = next(iter(SETTLEMENT_GRAPHS.values()))
        edge = next(iter(graph.edges))
        self.source = GridRoom.objects.filter_xyz(
            (edge.source.x, edge.source.y, graph.map_id)
        ).first()
        self.destination = GridRoom.objects.filter_xyz(
            (edge.destination.x, edge.destination.y, graph.map_id)
        ).first()
        # Independent arithmetic from the authored meter length and speed.
        self.expected = ceil(
            edge.length * 3600 / TERRAIN_SPEEDS["settlement"]
        )

    @covers_requirement(
        "movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry",
        "movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value",
    )
    def test_a_plain_exit_between_authored_nodes_charges_the_physical_edge(self):
        exit_obj = create_object(
            Exit, key="步道", location=self.source, destination=self.destination
        )
        self.char1.location = self.source
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, self.destination)
        self.assertIs(self.char1.location, self.destination)
        self.assertEqual(get_world_clock().tick, before + self.expected)
        self.assertNotEqual(MOVE, self.expected)

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_a_missing_authored_road_refuses_before_any_write(self):
        from world.maps.map_data import SETTLEMENT_GRAPHS

        graph = next(iter(SETTLEMENT_GRAPHS.values()))
        linked = {(edge.source.node_id, edge.destination.node_id) for edge in graph.edges}
        pair = next(
            (source, destination)
            for source in graph.nodes
            for destination in graph.nodes
            if source != destination and (source, destination) not in linked
        )
        source_node = graph.node(pair[0])
        destination_node = graph.node(pair[1])
        source = GridRoom.objects.filter_xyz(
            (source_node.x, source_node.y, graph.map_id)
        ).first()
        destination = GridRoom.objects.filter_xyz(
            (destination_node.x, destination_node.y, graph.map_id)
        ).first()
        exit_obj = create_object(
            Exit, key="無路", location=source, destination=destination
        )
        self.char1.location = source
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, destination)
        self.assertIs(self.char1.location, source)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_a_settlement_room_without_identity_refuses_before_any_write(self):
        from world.maps.map_data import SETTLEMENT_GRAPHS

        graph = next(iter(SETTLEMENT_GRAPHS.values()))
        edge = next(iter(graph.edges))
        source = GridRoom.objects.filter_xyz(
            (edge.source.x, edge.source.y, graph.map_id)
        ).first()
        # A grid room on the declared surface but outside the authored identity
        # table is broken geometry, not an interior connector.
        stray, _ = GridRoom.create(
            key="未編目", xyz=(graph.max_x + 1, graph.max_y + 1, graph.map_id)
        )
        exit_obj = create_object(
            Exit, key="黑巷", location=source, destination=stray
        )
        self.char1.location = source
        before = get_world_clock().tick
        exit_obj.at_traverse(self.char1, stray)
        self.assertIs(self.char1.location, source)
        self.assertEqual(get_world_clock().tick, before)


class MovementCostMixinSourceTests(EvenniaTestCase):
    """Source-inspection: at_post_traverse delegates to the shared
    after_successful_movement completion helper, never an inline
    get_world_clock().advance."""

    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_mixin_delegates_to_shared_completion_helper(self):
        import inspect

        from typeclasses.exits import MovementCostMixin, after_successful_movement

        source = inspect.getsource(MovementCostMixin.at_post_traverse)
        self.assertIn("after_successful_movement(", source)
        self.assertIn("cost_key=self.movement_cost_key", source)
        self.assertNotIn("get_world_clock().advance", source)
        helper = inspect.getsource(after_successful_movement)
        self.assertIn("charge_movement(", helper)
        self.assertIn("source_location=source_location", helper)
        self.assertIn("record_arrival(traversing_object)", helper)
        self.assertNotIn("get_world_clock().advance", helper)

    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_mixin_at_traverse_delegates_to_the_settlement_boundary(self):
        import inspect

        from typeclasses.exits import MovementCostMixin

        source = inspect.getsource(MovementCostMixin.at_traverse)
        self.assertIn("settle_movement(", source)
        self.assertIn("super().at_traverse", source)
        self.assertNotIn("get_world_clock().advance", source)
        self.assertNotIn("after_successful_movement(", source)


class SleepingPartyExitTests(EvenniaTest):
    """A source-present sleeper of any posture makes party travel stationary."""

    def setUp(self):
        super().setUp()
        from world.rules.party import join_party

        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.companion = create_object(NPC, key="同伴", location=self.room1)
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        join_party(self.companion, self.char1)
        self.exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )

    def _gauges(self, entity):
        return tuple(
            getattr(entity.traits, key).current for key in ("hp", "mp", "sp")
        )

    @covers_requirement(
        "party-system::any-present-sleeper-makes-party-travel-stationary"
    )
    def test_every_sleep_posture_refuses_the_connector_before_any_write(self):
        """Scenario: Ordinary connectors and both gate directions."""
        from unittest.mock import patch as mock_patch

        from world.rules.fatigue import (
            SleepPosture,
            read_fatigue_state,
            write_fatigue_state,
        )

        for posture, reserve in (
            (SleepPosture.FORCED, 0),
            (SleepPosture.VOLUNTARY, 360000),
        ):
            with self.subTest(posture=posture):
                write_fatigue_state(self.companion, reserve, posture)
                before_state = read_fatigue_state(self.companion)
                before_gauges = self._gauges(self.char1)
                before = get_world_clock().tick
                with mock_patch(
                    "world.rules.travel_cost.log_traversal_refusal"
                ) as refusal:
                    result = self.exit_obj.at_traverse(self.char1, self.room2)
                self.assertIsNone(result)
                refusal.assert_called_once()
                self.assertEqual(refusal.call_args.args[2], "party_sleeping")
                self.assertIs(self.char1.location, self.room1)
                self.assertIs(self.companion.location, self.room1)
                self.assertEqual(get_world_clock().tick, before)
                self.assertEqual(self._gauges(self.char1), before_gauges)
                self.assertEqual(
                    read_fatigue_state(self.companion), before_state
                )

    @covers_requirement(
        "party-system::any-present-sleeper-makes-party-travel-stationary"
    )
    def test_an_all_awake_party_still_traverses_and_charges(self):
        """Scenario: All awake behavior remains."""
        from world.rules.fatigue import (
            SleepPosture,
            write_fatigue_state,
        )

        write_fatigue_state(self.companion, 360000, SleepPosture.AWAKE)
        before = get_world_clock().tick
        self.exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(self.companion.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)


class FlightRequiredExitTests(EvenniaTest):
    """Flight-required exits gate on ``flight``/``flash_step`` ownership."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        # Read the waiver grant set off the gate itself instead of restating
        # shipped skill keys (test-data-independence).
        self.waiver_keys = sorted(MovementCostMixin.movement_waiver_skill_keys)

    def _traverse_via_command(self, exit_obj, caller):
        from evennia.objects.objects import ExitCommand

        command = ExitCommand()
        command.obj = exit_obj
        command.caller = caller
        command.func()

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_flight_required_exit_denies_a_non_owner(self):
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        self.char1.db.skills = {"active": [], "passive": []}
        self.assertFalse(exit_obj.access(self.char1, "traverse"))
        before = get_world_clock().tick
        self._traverse_via_command(exit_obj, self.char1)
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_flight_required_exit_passes_a_flight_owner(self):
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        self.char1.db.skills = {"active": [], "passive": [self.waiver_keys[0]]}
        self.assertTrue(exit_obj.access(self.char1, "traverse"))
        before = get_world_clock().tick
        self._traverse_via_command(exit_obj, self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_flight_required_exit_passes_a_flash_step_owner(self):
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        self.char1.db.skills = {"active": [], "passive": [self.waiver_keys[1]]}
        self.assertTrue(exit_obj.access(self.char1, "traverse"))
        before = get_world_clock().tick
        self._traverse_via_command(exit_obj, self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_flight_required_exit_passes_a_superuser_without_ownership(self):
        from evennia.utils.create import create_account

        admin = create_account(
            "admin",
            email="admin@example.com",
            password="test-superuser-password-2026",
            is_superuser=True,
        )
        self.char1.db_account = admin
        self.assertTrue(self.char1.is_superuser)
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        self.char1.db.skills = {"active": [], "passive": []}
        self.assertTrue(exit_obj.access(self.char1, "traverse"))
        before = get_world_clock().tick
        self._traverse_via_command(exit_obj, self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement(
        "party-system::any-present-sleeper-makes-party-travel-stationary"
    )
    def test_a_lawful_waiver_owner_cannot_carry_a_sleeping_companion(self):
        """Scenario: Waiver cannot bypass sleep."""
        from unittest.mock import patch as mock_patch

        from world.rules.fatigue import (
            SleepPosture,
            write_fatigue_state,
        )
        from world.rules.party import join_party

        companion = create_object(NPC, key="同伴", location=self.room1)
        join_party(companion, self.char1)
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        for owner_key in self.waiver_keys:
            for posture, reserve in (
                (SleepPosture.FORCED, 0),
                (SleepPosture.VOLUNTARY, 360000),
            ):
                with self.subTest(owner_key=owner_key, posture=posture):
                    self.char1.db.skills = {
                        "active": [],
                        "passive": [owner_key],
                    }
                    write_fatigue_state(companion, reserve, posture)
                    # The waiver grants access; it never grants admission.
                    self.assertTrue(exit_obj.access(self.char1, "traverse"))
                    before = get_world_clock().tick
                    with mock_patch(
                        "world.rules.travel_cost.log_traversal_refusal"
                    ) as refusal:
                        self._traverse_via_command(exit_obj, self.char1)
                    refusal.assert_called_once()
                    self.assertEqual(
                        refusal.call_args.args[2], "party_sleeping"
                    )
                    self.assertIs(self.char1.location, self.room1)
                    self.assertIs(companion.location, self.room1)
                    self.assertEqual(get_world_clock().tick, before)

    @covers_requirement(
        "party-system::any-present-sleeper-makes-party-travel-stationary"
    )
    def test_an_all_awake_waiver_owner_still_traverses(self):
        """Scenario: All awake behavior remains (waiver unchanged)."""
        from world.rules.fatigue import (
            SleepPosture,
            write_fatigue_state,
        )
        from world.rules.party import join_party

        companion = create_object(NPC, key="同伴", location=self.room1)
        join_party(companion, self.char1)
        write_fatigue_state(companion, 360000, SleepPosture.AWAKE)
        exit_obj = create_object(
            FlightRequiredExit,
            key="sky",
            location=self.room1,
            destination=self.room2,
        )
        self.char1.db.skills = {"active": [], "passive": [self.waiver_keys[0]]}
        before = get_world_clock().tick
        self._traverse_via_command(exit_obj, self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(companion.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_no_shipped_exit_sets_requires_flight_by_default(self):
        from typeclasses.exits import CostedXYZExit, MovementCostMixin, WildernessGateExit

        for exit_class in (Exit, CostedXYZExit, WildernessGateExit):
            self.assertIs(exit_class.requires_flight, False, exit_class)
        self.assertIs(MovementCostMixin.requires_flight, False)
