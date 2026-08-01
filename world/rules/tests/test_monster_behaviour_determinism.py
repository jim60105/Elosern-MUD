"""Determinism and offline-boundary tests for monster decisions."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import random
import unittest
from unittest.mock import patch

from world.rules import dice
from world.rules.monster_behaviour import (
    _choose_target,
    monster_behaviour_policy,
)

from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster, _field


class MonsterBehaviourDeterminismTests(unittest.TestCase):
    @covers_requirement("monster-action-policy::no-llm-or-generative-layer-involvement-anywhere-in-monster-decision-making")
    def test_unchanged_state_produces_identical_requests_without_roll(self):
        monster = FakeMonster(
            "monster",
            threat_tier="low",
            owned=["shadow_slash"],
        )
        enemy = FakeEntity("enemy", hp=50)
        battlefield = _field(monster, [enemy])
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100"
        ) as roller:
            first = monster_behaviour_policy(monster, battlefield)
            second = monster_behaviour_policy(monster, battlefield)
        roller.assert_not_called()
        self.assertEqual(first.skill_key, second.skill_key)
        self.assertEqual(first.targets, second.targets)

    def test_fixed_seed_replays_a_real_tie_break_roll(self):
        monster = FakeMonster("monster")
        enemies = [FakeEntity("first"), FakeEntity("second")]
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            wraps=dice.roll_d100,
        ) as roller:
            random.seed(913)
            first = _choose_target(monster, enemies, "lowest_hp")
            random.seed(913)
            second = _choose_target(monster, enemies, "lowest_hp")
        self.assertIs(first, second)
        self.assertEqual(roller.call_count, 2)

    def test_source_has_no_parallel_random_or_external_dependency(self):
        source = (
            Path(__file__).parents[1] / "monster_behaviour.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import random",
            "from random",
            "world.ai",
            "requests.",
            "httpx.",
            "urllib.",
        ):
            self.assertNotIn(forbidden, source)
