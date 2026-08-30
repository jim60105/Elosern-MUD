"""Tests for deterministic overwhelm classification signals."""

from tools.spec_traceability import covers_requirement

import math
import unittest
from unittest.mock import patch

from world.rules.combat import Battlefield, effective_power
from world.rules.overwhelm import (
    _agility_saturation,
    _decided_direction,
    _expected_damage_per_attack,
    classify_overwhelm,
    estimated_rounds_to_conclude,
    hit_rate_verdict,
    power_ratio_verdict,
    team_effective_power,
)

from .combat_fixtures import FakeEntity


def battlefield(
    first: list[FakeEntity],
    second: list[FakeEntity],
) -> Battlefield:
    members = first + second
    return Battlefield(
        {
            "first": frozenset(entity.key for entity in first),
            "second": frozenset(entity.key for entity in second),
        },
        {entity.key: entity for entity in members},
    )


class PowerRatioTests(unittest.TestCase):
    def test_ratio_comparable_zero_and_inactive_members(self):
        giant = FakeEntity("giant", hp=10000, max_hp=10000, defense=100)
        small = FakeEntity("small", hp=10, max_hp=10)
        field = battlefield([giant], [small])
        self.assertEqual(power_ratio_verdict(field, "first", "second"), "first")

        peer = FakeEntity("peer", hp=10000, max_hp=10000, defense=100)
        comparable = battlefield([giant], [peer])
        self.assertIsNone(
            power_ratio_verdict(comparable, "first", "second")
        )

        small.traits.hp.value = 0
        self.assertEqual(power_ratio_verdict(field, "first", "second"), "first")
        self.assertEqual(team_effective_power(field, "second"), 0)

        ally = FakeEntity("ally", hp=100, max_hp=100)
        mixed = battlefield([giant, ally], [peer])
        giant.traits.hp.value = 0
        self.assertEqual(team_effective_power(mixed, "first"), effective_power(ally))

    @covers_requirement("overwhelm-threshold::classify-overwhelm-is-a-pure-query-recomputable-every-round-with-no-stale-state")
    def test_living_member_power_ignores_current_hp(self):
        entity = FakeEntity("entity", hp=100, max_hp=100)
        field = battlefield([entity], [FakeEntity("other")])
        before = team_effective_power(field, "first")
        entity.traits.hp.value = 1
        self.assertEqual(team_effective_power(field, "first"), before)


class HitRateTests(unittest.TestCase):
    def test_saturation_and_cross_pair_requirement(self):
        fast = FakeEntity("fast", agility=60)
        slow = FakeEntity("slow", agility=10)
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertEqual(_agility_saturation(fast, slow), "hit")
            self.assertEqual(_agility_saturation(slow, fast), "miss")
            field = battlefield([fast], [slow])
            self.assertEqual(
                hit_rate_verdict(field, "first", "second"),
                "first",
            )
            field = battlefield(
                [fast, FakeEntity("middling", agility=20)],
                [slow],
            )
            self.assertIsNone(
                hit_rate_verdict(field, "first", "second")
            )

    def test_accuracy_is_evaluated_independently(self):
        first = FakeEntity("first", agility=10)
        second = FakeEntity("second", agility=10)

        def modifiers(entity):
            return {"accuracy": 50} if entity is first else {}

        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            side_effect=modifiers,
        ):
            self.assertEqual(_agility_saturation(first, second), "hit")
            self.assertEqual(
                _agility_saturation(second, first),
                "contested",
            )
            self.assertIsNone(
                hit_rate_verdict(
                    battlefield([first], [second]),
                    "first",
                    "second",
                )
            )

    def test_fractional_modifier_matches_integer_d100_boundaries(self):
        attacker = FakeEntity("attacker", agility=59)
        defender = FakeEntity("defender", agility=100)

        def modifiers(entity):
            return {"agility": "-15%"} if entity is attacker else {}

        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            side_effect=modifiers,
        ):
            self.assertEqual(
                _agility_saturation(attacker, defender),
                "miss",
            )
            self.assertEqual(
                _expected_damage_per_attack(attacker, defender),
                0,
            )

    @covers_requirement(
        "combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math"
    )
    def test_estimate_terms_include_the_flat_bundle_bonuses(self):
        attacker = FakeEntity(
            "attacker", atk_phys=20, agility=10
        )
        attacker.skills._owned = ["retainer_martial_training"]
        defender = FakeEntity("defender", defense=5, agility=10)
        defender.skills._owned = ["guardian_instinct"]
        estimate = _expected_damage_per_attack(attacker, defender)
        self.assertAlmostEqual(estimate, 0.5 * (round((20 + 5) * 1.0) - (5 + 5)))


class RoundEstimateTests(unittest.TestCase):
    def test_calibration_examples(self):
        elf = FakeEntity(
            "elf",
            hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
        )
        human = FakeEntity(
            "human",
            hp=120,
            atk_phys=8,
            agility=9,
            defense=7,
            magic_power=40,
        )
        monsters = [
            FakeEntity(
                f"monster-{index}",
                hp=90,
                atk_phys=6,
                agility=6,
                defense=6,
                magic_power=0,
            )
            for index in range(3)
        ]
        calamity = FakeEntity("calamity", hp=10000, atk_phys=100, agility=92)
        humans = [
            FakeEntity(
                f"human-{index}",
                hp=120,
                agility=9,
                defense=7,
            )
            for index in range(3)
        ]
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([elf], [human]),
                    "first",
                    "second",
                ),
                120 / 81,
            )
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([elf], monsters),
                    "first",
                    "second",
                ),
                270 / 82,
            )
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([calamity], humans),
                    "first",
                    "second",
                ),
                360 / 93,
            )
            weak = FakeEntity("weak", atk_phys=1, agility=60)
            wall = FakeEntity(
                "wall",
                hp=10000,
                max_hp=10000,
                agility=10,
                defense=999,
            )
            self.assertEqual(
                estimated_rounds_to_conclude(
                    battlefield([weak], [wall]),
                    "first",
                    "second",
                ),
                10000,
            )

    def test_estimate_uses_current_hp_and_handles_no_damage(self):
        attacker = FakeEntity("attacker", atk_phys=20, agility=60)
        defender = FakeEntity("defender", hp=100, max_hp=100, agility=10)
        field = battlefield([attacker], [defender])
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            power = team_effective_power(field, "second")
            first = estimated_rounds_to_conclude(field, "first", "second")
            defender.traits.hp.value = 50
            self.assertLess(
                estimated_rounds_to_conclude(field, "first", "second"),
                first,
            )
            self.assertEqual(team_effective_power(field, "second"), power)
            self.assertGreater(_expected_damage_per_attack(attacker, defender), 0)
            # A modifier-blind negative raw agility is clamped at 0 by the
            # shared adjusted-agility path, so unreachable comes from the
            # defender's agility instead (required roll beyond 100).
            defender.skills.values["agility"] = 1000
            self.assertTrue(
                math.isinf(
                    estimated_rounds_to_conclude(
                        field,
                        "first",
                        "second",
                    )
                )
            )


class CombinedSignalTests(unittest.TestCase):
    def test_signal_combinations_and_round_gate(self):
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            ratio = battlefield(
                [
                    FakeEntity(
                        "large",
                        hp=10000,
                        max_hp=10000,
                        atk_phys=3000,
                        agility=10,
                    )
                ],
                [FakeEntity("small", hp=10, agility=10)],
            )
            self.assertEqual(
                power_ratio_verdict(ratio, "first", "second"),
                "first",
            )
            self.assertIsNone(
                hit_rate_verdict(ratio, "first", "second")
            )
            self.assertEqual(classify_overwhelm(ratio), "first")

            rate = battlefield(
                [FakeEntity("fast", atk_phys=100, agility=60)],
                [FakeEntity("slow", hp=100, agility=10)],
            )
            self.assertIsNone(
                power_ratio_verdict(rate, "first", "second")
            )
            self.assertEqual(
                hit_rate_verdict(rate, "first", "second"),
                "first",
            )
            self.assertEqual(classify_overwhelm(rate), "first")

            contested = battlefield(
                [FakeEntity("a")],
                [FakeEntity("b")],
            )
            self.assertIsNone(classify_overwhelm(contested))

            grind = battlefield(
                [
                    FakeEntity(
                        "durable",
                        hp=100000000,
                        max_hp=100000000,
                        atk_phys=1,
                        agility=10,
                    )
                ],
                [
                    FakeEntity(
                        "wall",
                        hp=10000,
                        max_hp=10000,
                        agility=10,
                        defense=999,
                    )
                ],
            )
            self.assertEqual(
                power_ratio_verdict(grind, "first", "second"),
                "first",
            )
            self.assertIsNone(classify_overwhelm(grind))

    def test_disagreement_does_not_consult_estimate(self):
        field = battlefield([FakeEntity("a")], [FakeEntity("b")])
        with (
            patch(
                "world.rules.overwhelm.power_ratio_verdict",
                return_value="first",
            ),
            patch(
                "world.rules.overwhelm.hit_rate_verdict",
                return_value="second",
            ),
            patch(
                "world.rules.overwhelm.estimated_rounds_to_conclude"
            ) as estimate,
        ):
            self.assertIsNone(
                _decided_direction(field, "first", "second")
            )
            self.assertIsNone(classify_overwhelm(field))
            estimate.assert_not_called()

    def test_classification_recomputes_without_cached_state(self):
        strong = FakeEntity(
            "strong",
            hp=10000,
            max_hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
        )
        weak = FakeEntity("weak", hp=120, agility=9, defense=7)
        field = battlefield([strong], [weak])
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertEqual(classify_overwhelm(field), "first")
            self.assertEqual(classify_overwhelm(field), "first")
            strong.skills.values.update(
                atk_phys=1,
                agility=10,
                defense=1,
                magic_power=1,
            )
            self.assertIsNone(classify_overwhelm(field))
