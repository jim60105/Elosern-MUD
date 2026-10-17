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

    @covers_requirement(
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor"
    )
    def test_weapon_damage_multiplier_physical_consumer_and_controls(self):
        from world.rules.combat import _handle_heal
        from world.lore.items import EquipmentSlot, EquipmentModifierKey
        from world.rules.equipment_effects import EquipmentEffectRule
        from world.tests.synthetic_data import make_item

        # Synthetic weapons
        synth_main = make_item(
            key="t_synth_main_sword",
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.PLAIN_SWORD,
        )
        rule_1_5 = EquipmentEffectRule(
            adjustments={},
            gauge_caps={},
            immune=(),
            attached_buffs=(),
            exposure_bias=0,
            weapon_damage_multiplier=1.5,
        )
        phys_actor = FakeEntity("phys_actor", atk_phys=60, magic_power=60, agility=10)
        phys_actor.db.equipment = {
            "weapon_main": synth_main.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        target = FakeEntity("target", hp=100, defense=20, agility=10)
        with patch.dict("world.rules.equipment_effects.ITEM_REGISTRY", {synth_main.key: synth_main}):
            with patch.dict("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", {EquipmentModifierKey.PLAIN_SWORD: rule_1_5}):
                with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
                    with patch("world.rules.combat.damage.roll_d100", return_value=60):
                        # Physical strike: attack=60 * 1.5 = 90. K=40, def=20 => 90 * 40 / 60 = 60.
                        phys_pending = _handle_damage(phys_actor, [target], "damage:fire:physical", {}, 1.0)[0]
                        # Magic strike: weapon factor is NOT applied => attack=60. 60 * 40 / 60 = 40.
                        mag_pending = _handle_damage(phys_actor, [target], "damage:fire:magic", {}, 1.0)[0]
                        # Healing control: magic_power=60 * heal mult 1.0 = 60
                        heal_target = FakeEntity("heal_target", hp=100, max_hp=100)
                        heal_target.traits.hp.current = 20
                        heal_pending = _handle_heal(phys_actor, [heal_target], "heal:single", {}, 1.0)[0]
                        self.assertEqual(int(heal_pending.description.split("|")[-1]), 60)

        # Scenario from spec: K=40, defense=20, attack before weapon factor=60, declared factor is 1.5
        # THEN physical damage before Defend is 60; matching magic control remains 40
        self.assertEqual(int(phys_pending.description.split("|")[-1]), 60)
        self.assertEqual(int(mag_pending.description.split("|")[-1]), 40)

    @covers_requirement(
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor"
    )
    def test_weapon_damage_multiplier_critical_conditional_and_multistrike(self):
        from world.lore.items import EquipmentSlot, EquipmentModifierKey
        from world.rules.equipment_effects import EquipmentEffectRule
        from world.skills.effects import DamagePolicy, EffectPolicy, ResolvedEffect
        from world.tests.synthetic_data import make_item

        synth_main = make_item(
            key="t_synth_ms_sword",
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.PLAIN_SWORD,
        )
        rule_1_5 = EquipmentEffectRule(
            adjustments={},
            gauge_caps={},
            immune=(),
            attached_buffs=(),
            exposure_bias=0,
            weapon_damage_multiplier=1.5,
        )
        phys_actor = FakeEntity("ms_actor", atk_phys=40, agility=10)
        phys_actor.db.equipment = {
            "weapon_main": synth_main.key,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        target = FakeEntity("ms_target", hp=500, defense=10, agility=10)
        target.db.combat_traits = ["dark"]
        policy = DamagePolicy(extra_strikes=1, predicate=("dark",), attack_multiplier=2.0)
        res_eff = ResolvedEffect(source_skill="test_ms", policy=EffectPolicy(damage=policy))
        with patch.dict("world.rules.equipment_effects.ITEM_REGISTRY", {synth_main.key: synth_main}):
            with patch.dict("world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", {EquipmentModifierKey.PLAIN_SWORD: rule_1_5}):
                with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
                    # Roll natural 100 -> critical hit (crit_multiplier = 2.0)
                    with patch("world.rules.combat.damage.roll_d100", return_value=100):
                        pending = _handle_damage(phys_actor, [target], "damage:none:physical", {"resolved_effect": res_eff}, 1.0)
        # Exactly 2 strikes generated
        self.assertEqual(len(pending), 2)
        # Arithmetic per strike: attack=40 * roll_mult 2.0 * matched_mult 2.0 * weapon_mult 1.5 = 240
        # Ratio mitigation: K=40, def=10 -> 240 * 40 / (40 + 10) = 240 * 40 / 50 = 192.
        for p in pending:
            self.assertEqual(int(p.description.split("|")[-1]), 192)

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
            # The remaining required sections are taken from the shipped
            # rulebook so this behaviour test names no catalog token.
            **{key: value for key, value in COMBAT_YAML.items() if key != "damage"},
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

    @covers_requirement(
        "combat-resolution::physical-damage-multiplies-the-rounded-attack-component-by-equipped-weapon-factor",
        "human-combat-calibration::equipment-growth-evidence-uses-real-construction-and-committed-reload",
    )
    def test_weapon_factor_defend_and_below_threshold_arithmetic(self):
        # Independent literal arithmetic for the equipment-growth evidence
        # (docs/development/human-combat-calibration-evidence.md), evaluated
        # directly on the scalar stage: expected values are fixed integers, so
        # the placement is never re-derived by calling the calculator under
        # test with its own formula.
        #
        # K = 40, rounded pre-mitigation attack 60 against defense 20 => 40,
        # the same strike under Defend (35% reduction, floored) => 26, and the
        # declared physical weapon factor 1.5 on the attack term => 60.
        self.assertEqual(
            strike_amount(
                attack=60.0, multiplier=1.0, coefficient=1.0, defense=20.0
            ),
            40,
        )
        self.assertEqual(
            strike_amount(
                attack=60.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=20.0,
                defending=True,
            ),
            26,
        )
        self.assertEqual(
            strike_amount(
                attack=60.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=20.0,
                weapon_multiplier=1.5,
            ),
            60,
        )
        # Below the retired subtraction threshold: attack 20 against defense
        # 30 is negative under subtraction, while ratio mitigation lands it
        # and a whole-point upgrade in the attack term grows it by 3.
        self.assertEqual(
            strike_amount(
                attack=20.0, multiplier=1.0, coefficient=1.0, defense=30.0
            ),
            11,
        )
        self.assertEqual(
            strike_amount(
                attack=20.0,
                multiplier=1.0,
                coefficient=1.0,
                defense=30.0,
                weapon_multiplier=1.25,
            ),
            14,
        )
