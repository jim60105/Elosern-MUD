"""Integration tests for MovementCostMixin exit charging (map-movement-clock)."""

from tools.spec_traceability import covers_requirement

from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import CostedXYZExit, Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.rules.clock import CLOCK_YAML, get_world_clock

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

    @covers_requirement("movement-cost-charging::movement-charges-only-for-a-playercharacter-traverser-never-for-an-autonomous-npc")
    def test_npc_traversal_moves_but_does_not_advance_clock(self):
        exit_obj = create_object(Exit, key="npc_door", location=self.room1, destination=self.room2)
        npc = create_object(NPC, key="npc", location=self.room1)
        before = get_world_clock().tick
        exit_obj.at_traverse(npc, self.room2)
        self.assertIs(npc.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)

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


class MovementCostMixinSourceTests(EvenniaTest):
    """Source-inspection: at_post_traverse delegates to the shared
    after_successful_movement completion helper (onboarding-skip coverage
    design D1), never an inline get_world_clock().advance."""

    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_mixin_delegates_to_shared_completion_helper(self):
        import inspect

        from typeclasses.exits import MovementCostMixin, after_successful_movement

        source = inspect.getsource(MovementCostMixin.at_post_traverse)
        self.assertIn("after_successful_movement(", source)
        self.assertIn("cost_key=self.movement_cost_key", source)
        self.assertNotIn("get_world_clock().advance", source)
        helper = inspect.getsource(after_successful_movement)
        self.assertIn("charge_movement(traversing_object, cost_key)", helper)
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


class FlightRequiredExitTests(EvenniaTest):
    """Flight-required exits gate on ``flight``/``flash_step`` ownership."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

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
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
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
        self.char1.db.skills = {"active": [], "passive": ["flash_step"]}
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

    @covers_requirement("movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners")
    def test_no_shipped_exit_sets_requires_flight_by_default(self):
        from typeclasses.exits import CostedXYZExit, MovementCostMixin, WildernessGateExit

        for exit_class in (Exit, CostedXYZExit, WildernessGateExit):
            self.assertIs(exit_class.requires_flight, False, exit_class)
        self.assertIs(MovementCostMixin.requires_flight, False)
