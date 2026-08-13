"""Focused tests for the shared movement-cost charging function (map-movement-clock)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock
from world.rules.movement import charge_movement


class ChargeMovementTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()
        self.npc = create_object(NPC, key="npc", location=self.room1)

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_charge_movement_advances_clock_by_move_cost(self):
        before = get_world_clock().tick
        charge_movement(self.char1, "move")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["move"],
        )

    def test_charge_movement_is_a_noop_for_npc(self):
        before = get_world_clock().tick
        charge_movement(self.npc, "move")
        self.assertEqual(get_world_clock().tick, before)

    def test_charge_movement_always_uses_command_source(self):
        with patch("world.rules.clock.get_world_clock") as clock:
            charge_movement(self.char1, "move")
            charge_movement(self.char1, "wilderness_move")
        move_call = clock.return_value.advance.call_args_list[0]
        wild_call = clock.return_value.advance.call_args_list[1]
        self.assertEqual(move_call.args[0], CLOCK_YAML["command_defaults"]["move"])
        self.assertEqual(move_call.args[1], AdvanceSource.COMMAND)
        self.assertEqual(move_call.args[2], [self.char1])
        self.assertEqual(wild_call.args[0], CLOCK_YAML["command_defaults"]["wilderness_move"])
        self.assertEqual(wild_call.args[1], AdvanceSource.COMMAND)
        self.assertEqual(wild_call.args[2], [self.char1])

    def test_charge_movement_is_cost_key_generic(self):
        before = get_world_clock().tick
        charge_movement(self.char1, "wilderness_move")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["wilderness_move"],
        )

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_flight_owner_is_waived_the_wilderness_move_cost(self):
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        before = get_world_clock().tick
        charge_movement(self.char1, "wilderness_move")
        self.assertEqual(get_world_clock().tick, before)

    def test_flight_owner_still_pays_other_cost_keys(self):
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        before = get_world_clock().tick
        charge_movement(self.char1, "move")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["move"],
        )

    def test_non_flight_owner_pays_wilderness_move_normally(self):
        before = get_world_clock().tick
        charge_movement(self.char1, "wilderness_move")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["wilderness_move"],
        )

    def test_flash_step_owner_does_not_get_the_wilderness_waiver(self):
        self.char1.db.skills = {"active": [], "passive": ["flash_step"]}
        before = get_world_clock().tick
        charge_movement(self.char1, "wilderness_move")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["wilderness_move"],
        )
