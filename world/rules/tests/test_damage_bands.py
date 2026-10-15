"""Damage band and floor tests."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules.combat import COMBAT_YAML, _handle_damage, _roll_multiplier
from world.rules.combat.battlefield import (
    CombatRulebookError,
    validate_combat_rulebook,
)
from world.rules.combat.scalars import (
    damage_rider,
    hit_margin,
    strike_amount,
)

from .combat_fixtures import FakeEntity


class DamageBandTests(unittest.TestCase):
    def test_bare_solid_and_critical_bands(self):
        damage = COMBAT_YAML["damage"]
        self.assertEqual(_roll_multiplier(50, 1), damage["base_multiplier"])
        self.assertEqual(
            _roll_multiplier(50, damage["solid_hit_margin"]),
            damage["solid_hit_multiplier"],
        )
        self.assertEqual(
            _roll_multiplier(100, 0), damage["crit_multiplier"]
        )
        # Non-default K consumption proof: K=80, attack=60, defense=20 => 60 * 80 / 100 = 48
        with patch.dict(COMBAT_YAML["damage"], {"mitigation_k": 80}):
            self.assertEqual(
                strike_amount(
                    attack=60.0,
                    multiplier=1.0,
                    coefficient=1.0,
                    defense=20.0,
                ),
                48,
            )

    @covers_requirement(
        "combat-resolution::ratio-mitigation-clamps-negative-defense-and-shares-settlement-and-estimation"
    )
    def test_ratio_mitigation_integration_properties(self):
        # 1. Physical and magic symmetry through _handle_damage
        phys_actor = FakeEntity("phys_a", atk_phys=50, agility=10)
        magic_actor = FakeEntity("mag_a", magic_power=50, agility=10)
        target = FakeEntity("target", hp=100, defense=30, agility=10)
        with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
            with patch("world.rules.combat.damage.roll_d100", return_value=60):
                phys_pending = _handle_damage(phys_actor, [target], "damage:dark:physical", {}, 1.0)[0]
                mag_pending = _handle_damage(magic_actor, [target], "damage:fire:magic", {}, 1.0)[0]
        self.assertEqual(phys_pending.description.split("|")[-1], mag_pending.description.split("|")[-1])
        # 50 * 1.0 * 1.0 = 50. 50 * 40 / (40 + 30) = 28.57... => 28
        self.assertEqual(phys_pending.description.split("|")[-1], "28")

        # 2. Explicit defense bypass sets defense to zero
        from world.skills.effects import DamagePolicy, EffectPolicy, ResolvedEffect
        bypass_policy = DamagePolicy(
            unconditional_defense_bypass=True,
        )
        with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
            with patch("world.rules.combat.damage.roll_d100", return_value=60):
                res_eff = ResolvedEffect(source_skill="test", policy=EffectPolicy(damage=bypass_policy))
                bypassed = _handle_damage(
                    phys_actor, [target], "damage:dark:physical", {"resolved_effect": res_eff}, 1.0
                )[0]
        # With defense=0: 50 * 40 / 40 = 50
        self.assertEqual(bypassed.description.split("|")[-1], "50")

        # 3. Miss deals no damage and applies no floor
        with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
            with patch("world.rules.combat.damage.roll_d100", return_value=1):
                missed = _handle_damage(phys_actor, [target], "damage:dark:physical", {}, 1.0)[0]
        self.assertEqual(missed.description.split("|")[-1], "0")
        missed.apply()
        self.assertEqual(target.traits.hp.value, 100)

        # 4. Devastation rider, scales, and conditional coefficients ordering
        # attack=30, mult=1.5, coeff=2.0, matched_multiplier=1.5 => attack_part=round(30*1.5*2.0*1.5)=135
        # defense=20 => retention=40/(40+20)=2/3 => 135 * 40 / 60 = 90
        # rider=10 => base_amount = 90 + 10 = 100
        # scale=0.5 => scaled_magnitude(100, 0.5) = 50
        self.assertEqual(
            strike_amount(
                attack=30.0,
                multiplier=1.5,
                coefficient=2.0,
                defense=20.0,
                rider=10,
                matched_multiplier=1.5,
                scale=0.5,
            ),
            50,
        )

        # 5. Nonlethal protection preservation with ratio mitigation
        protected_target = FakeEntity("prot_target", hp=10, defense=0, agility=10)
        with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
            with patch("world.rules.combat.damage.roll_d100", return_value=60):
                lethal_pending = _handle_damage(
                    phys_actor, [protected_target], "damage:dark:physical", {"nonlethal": True}, 1.0
                )[0]
        # Target has 10 HP, damage is 50 => floored at 1 HP
        lethal_pending.apply()
        self.assertEqual(protected_target.traits.hp.value, 1)

        # 6. Estimator parity with settlement on shared strike_amount
        # Evaluated at face roll 60 (margin > 0):
        estimated = strike_amount(
            attack=50.0,
            multiplier=1.0,
            coefficient=1.0,
            defense=30.0,
        )
        self.assertEqual(estimated, int(phys_pending.description.split("|")[-1]))

    @covers_requirement("combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a")
    def test_floor_shape_does_not_apply_to_a_miss(self):
        actor = FakeEntity("actor", atk_phys=1, agility=10)
        target = FakeEntity("target", hp=100, defense=99, agility=10)
        with patch(
            "world.rules.combat.damage.evaluate_combat_modifiers",
            return_value={},
        ):
            with patch("world.rules.combat.damage.roll_d100", return_value=51):
                hit = _handle_damage(
                    actor, [target], "damage:dark:physical", {}, 1.0
                )[0]
            with patch("world.rules.combat.damage.roll_d100", return_value=1):
                miss = _handle_damage(
                    actor, [target], "damage:dark:physical", {}, 1.0
                )[0]
        self.assertTrue(hit.description.endswith("|1|1"))
        self.assertTrue(miss.description.endswith("|0|0"))
        miss.apply()
        self.assertEqual(target.traits.hp.value, 100)

    @covers_requirement(
        "combat-resolution::ratio-mitigation-clamps-negative-defense-and-shares-settlement-and-estimation"
    )
    def test_ratio_scalar_independent_arithmetic_evidence(self):
        # Task 1.1 / Spec: K=40, rounded pre-mitigation attack=60, defense=20 => 40
        self.assertEqual(
            strike_amount(
                attack=60.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=20.0,
            ),
            40,
        )
        # Floating-point evaluation order preservation: 154 * 40 / (40 + 114) == 40
        self.assertEqual(
            strike_amount(
                attack=154.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=114.0,
            ),
            40,
        )
        # Negative defense clamped to zero: defense -10 behaves identically to 0
        self.assertEqual(
            strike_amount(
                attack=60.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=-10.0,
            ),
            60,
        )
        self.assertEqual(
            strike_amount(
                attack=60.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=0.0,
            ),
            60,
        )

    @covers_requirement(
        "combat-resolution::ratio-mitigation-clamps-negative-defense-and-shares-settlement-and-estimation"
    )
    def test_rulebook_validation_rejects_invalid_mitigation_k(self):
        valid_base = {
            "damage": {
                "crit_multiplier": 2.0,
                "solid_hit_margin": 40,
                "solid_hit_multiplier": 1.5,
                "base_multiplier": 1.0,
                "floor": 1,
                "mitigation_k": 40,
            },
        }
        # Valid passes
        self.assertEqual(validate_combat_rulebook(valid_base)["damage"]["mitigation_k"], 40)
        # Valid float passes
        with_float = dict(valid_base, damage=dict(valid_base["damage"], mitigation_k=40.5))
        self.assertEqual(validate_combat_rulebook(with_float)["damage"]["mitigation_k"], 40.5)

        # Non-mapping root rejects
        with self.assertRaises(CombatRulebookError):
            validate_combat_rulebook("not a dict")
        # Missing damage section rejects
        with self.assertRaises(CombatRulebookError):
            validate_combat_rulebook({"other_section": {}})
        # Missing mitigation_k rejects
        missing_k = dict(valid_base, damage=dict(valid_base["damage"]))
        del missing_k["damage"]["mitigation_k"]
        with self.assertRaises(CombatRulebookError):
            validate_combat_rulebook(missing_k)

        # Invalid values for mitigation_k
        for invalid in (
            0,
            -1,
            -40.0,
            False,
            True,
            "40",
            float("inf"),
            float("-inf"),
            float("nan"),
        ):
            with self.subTest(invalid=invalid):
                bad = dict(valid_base, damage=dict(valid_base["damage"], mitigation_k=invalid))
                with self.assertRaises(CombatRulebookError):
                    validate_combat_rulebook(bad)
