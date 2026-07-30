"""Initiative dominance and per-round upkeep tests."""

import unittest
from unittest.mock import patch

from world.rules.combat import (
    Battlefield,
    default_attack_policy,
    roll_initiative,
    run_round,
)

from .combat_fixtures import FakeEntity


class InitiativeAndTurnLoopTests(unittest.TestCase):
    def battlefield(self, gap: int = 10):
        fast = FakeEntity("fast", agility=10 + gap)
        slow = FakeEntity("slow", agility=10)
        return Battlefield(
            {"a": frozenset({"fast"}), "b": frozenset({"slow"})},
            {"fast": fast, "slow": slow},
        )

    def test_ten_point_gap_dominates_every_roll_pair(self):
        battlefield = self.battlefield()
        with patch("world.rules.combat.roll_d100", side_effect=[1, 100]):
            self.assertEqual(roll_initiative(battlefield), ["fast", "slow"])

    def test_small_gap_can_be_reordered(self):
        battlefield = self.battlefield(gap=9)
        with patch("world.rules.combat.roll_d100", side_effect=[1, 100]):
            self.assertEqual(roll_initiative(battlefield), ["slow", "fast"])

    def test_action_lock_skips_resolver_and_upkeep_runs(self):
        battlefield = self.battlefield()
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "slow"]),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                side_effect=[{"actions_per_turn": 0}, {}],
            ),
            patch("world.rules.combat.ActionResolver.resolve") as resolve,
            patch("world.rules.combat.tick_buffs") as tick,
            patch("world.rules.combat.decay_tick") as decay,
        ):
            logs = run_round(battlefield, lambda entity, field: None)
        self.assertEqual(logs[0].entries[0].kind, "action_skipped")
        resolve.assert_not_called()
        self.assertEqual(tick.call_count, 2)
        self.assertEqual(decay.call_count, 2)
        for call in decay.call_args_list:
            self.assertEqual(call.args[1], 6)

    def test_default_policy_does_not_retry_an_unaffordable_skill(self):
        battlefield = self.battlefield()
        actor = battlefield.roster["fast"]
        actor.skills._owned = ["fire_ball"]
        actor.traits.mp = type(
            "Gauge",
            (),
            {
                "trait_type": "gauge",
                "_data": {"base": 0, "mod": 0, "mult": 1, "current": 0},
            },
        )()
        self.assertIsNone(default_attack_policy(actor, battlefield))
