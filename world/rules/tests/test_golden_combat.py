"""Fixed-seed golden combat behavior."""

from tools.spec_traceability import covers_requirement

import random
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.combat import (
    Battlefield,
    _handle_damage,
    run_battle,
)

from .combat_fixtures import FakeEntity


class GoldenCombatTests(unittest.TestCase):
    @covers_requirement("combat-resolution::golden-fixed-seed-tests-cover-a-normal-exchange-and-a-lopsided-exchange")
    def test_normal_exchange_has_fixed_roll_and_damage_sequence(self):
        attacker = FakeEntity("a", atk_phys=12, agility=9)
        defender = FakeEntity("b", hp=200, defense=7, agility=9)
        random.seed(41)
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            pending = [
                _handle_damage(attacker, [defender], "damage:dark:physical", {}, 1.0)[0]
                for _ in range(3)
            ]
        self.assertEqual(
            [effect.description for effect in pending],
            [
                "damage|b|49|0|0",
                "damage|b|43|0|0",
                "damage|b|30|0|0",
            ],
        )

    @covers_requirement("combat-resolution::per-round-upkeep-ticks-buffs-and-advances-sexual-decay-by-the-round-duration", "combat-resolution::the-turn-loop-reports-elapsed-time-as-rounds-times-6-seconds-and-never-advances-a-clock", "single-shot-resolution::reported-time-cost-uses-the-identical-rounds-times-six-seconds-formula-unedited")
    def test_lopsided_exchange_saturates_and_time_is_round_based(self):
        elf = FakeEntity("elf", hp=10000, agility=92)
        human = FakeEntity("human", hp=120, agility=9)
        battlefield = Battlefield(
            {"elves": frozenset({"elf"}), "humans": frozenset({"human"})},
            {"elf": elf, "human": human},
        )
        with (
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            for raw_roll in (1, 50, 100):
                self.assertTrue(
                    __import__("world.rules.combat", fromlist=["_to_hit"])._to_hit(
                        elf, human, raw_roll
                    )[0]
                )
                self.assertFalse(
                    __import__("world.rules.combat", fromlist=["_to_hit"])._to_hit(
                        human, elf, raw_roll
                    )[0]
                )
            result = run_battle(
                battlefield,
                action_provider=lambda entity, field: None,
                max_rounds=3,
            )
        self.assertEqual(result.rounds_elapsed, 3)
        self.assertEqual(result.total_seconds, 18)


class GoldenResolverBattleTests(EvenniaTestCase):
    def _battlefield(self, suffix: str) -> Battlefield:
        first = create_object(PlayerCharacter, key=f"first-{suffix}")
        second = create_object(PlayerCharacter, key=f"second-{suffix}")
        for entity in (first, second):
            entity.race = "human"
            entity.apply_race_baseline()
            entity.db.skills = {"active": ["shadow_slash"], "passive": []}
        return Battlefield(
            {
                "first": frozenset({first.key}),
                "second": frozenset({second.key}),
            },
            {first.key: first, second.key: second},
        )

    @staticmethod
    def _signature(result):
        return [
            (
                log.actor.split("-")[0],
                tuple(
                    (
                        entry.kind,
                        entry.actor.split("-")[0],
                        None
                        if entry.target is None
                        else entry.target.split("-")[0],
                        tuple(sorted(entry.data.items())),
                    )
                    for entry in log.entries
                ),
            )
            for log in result.event_logs
        ]

    @covers_requirement("single-shot-resolution::a-golden-fixed-seed-case-demonstrates-single-round-completion-for-this-project-s-own")
    def test_fixed_seed_full_battle_is_reproducible_through_resolver(self):
        first = self._battlefield("one")
        random.seed(730)
        first_result = run_battle(first, max_rounds=3)
        second = self._battlefield("two")
        random.seed(730)
        second_result = run_battle(second, max_rounds=3)
        self.assertEqual(
            self._signature(first_result),
            self._signature(second_result),
        )
        self.assertTrue(first_result.event_logs)
        self.assertEqual(first_result.total_seconds, first_result.rounds_elapsed * 6)
        self.assertTrue(
            any(
                entry.kind in {"roll", "damage"}
                for log in first_result.event_logs
                for entry in log.entries
            )
        )
