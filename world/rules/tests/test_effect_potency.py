"""Effect potency policy and execution tests (light-effect-potency).

Verifies the immutable per-occurrence EffectPolicy contract, ActionResolver
trusted resolved_effect binding, pre-defense damage scaling, and pre-rounding
healing composition. Uses synthetic skills only.
"""

from copy import deepcopy
import importlib
import math
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    COMBAT_YAML,
    _handle_damage,
    _handle_heal,
    _handle_self_heal,
    _heal_magnitude,
)
from world.rules.tests.combat_fixtures import FakeEntity
from world.skills.effects import (
    DamageEffect,
    EffectPolicy,
    HealEffect,
    ResolvedEffect,
    SelfHealEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    _skill,
    _spell,
)
from world.tests.synthetic_data import REGISTRY_TARGETS


class EffectPolicyAuthoringTests(unittest.TestCase):
    """Immutable per-occurrence policy validation at definition time."""

    def test_effect_policy_defaults_to_identity(self):
        policy = EffectPolicy()
        self.assertEqual(policy.coefficient, 1.0)
        self.assertIsInstance(policy.coefficient, float)

    def test_effect_policy_normalizes_int_to_float(self):
        policy = EffectPolicy(coefficient=2)
        self.assertEqual(policy.coefficient, 2.0)
        self.assertIsInstance(policy.coefficient, float)

    def test_effect_policy_rejects_bool(self):
        with self.assertRaises(ValueError):
            EffectPolicy(coefficient=True)
        with self.assertRaises(ValueError):
            EffectPolicy(coefficient=False)

    def test_effect_policy_rejects_non_numeric_and_nonfinite(self):
        for bad in ("2.0", None, [], {}, float("nan"), float("inf"), float("-inf"), 10**400):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    EffectPolicy(coefficient=bad)

    def test_effect_policy_rejects_non_positive(self):
        for bad in (0, 0.0, -0.1, -1.0, -10):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    EffectPolicy(coefficient=bad)

    def test_resolved_effect_requires_effect_policy(self):
        valid = ResolvedEffect(policy=EffectPolicy(2.0))
        self.assertEqual(valid.policy.coefficient, 2.0)
        for bad in ("policy", None, 1.0, {}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ResolvedEffect(policy=bad)

    def test_skill_def_omitted_policies_normalize_to_identity_tuple(self):
        skill = SkillDef(
            key="t_potency_omitted",
            label="測試省略政策",
            description="省略效果政策應自動填補單位政策。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={"mp": 10},
            usable_out_of_combat=False,
            element=None,
            effects=["damage:fire:magic", "heal:single"],
            category=SkillCategory.UTILITY,
        )
        self.assertEqual(len(skill.effect_policies), 2)
        self.assertEqual(skill.effect_policies, (EffectPolicy(1.0), EffectPolicy(1.0)))

    def test_skill_def_empty_tuple_normalizes_to_identity_tuple(self):
        skill = SkillDef(
            key="t_potency_empty_tuple",
            label="測試空元組政策",
            description="空元組效果政策應自動填補單位政策。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={"mp": 10},
            usable_out_of_combat=False,
            element=None,
            effects=["damage:fire:magic"],
            category=SkillCategory.UTILITY,
            effect_policies=(),
        )
        self.assertEqual(skill.effect_policies, (EffectPolicy(1.0),))

    def test_skill_def_rejects_falsy_non_tuple_containers(self):
        for bad in (False, 0, "", [], {}, [EffectPolicy(1.0)]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_potency_bad_type",
                        label="測試不合法型別",
                        description="非 tuple 的政策宣告必須在建構時失敗。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.SINGLE,
                        cost={"mp": 10},
                        usable_out_of_combat=False,
                        element=None,
                        effects=["damage:fire:magic"],
                        category=SkillCategory.UTILITY,
                        effect_policies=bad,
                    )

    def test_skill_def_cardinality_mismatch_fails_construction(self):
        with self.assertRaises(ValueError):
            SkillDef(
                key="t_potency_mismatch",
                label="測試數量不符",
                description="政策數量與效果數量不符必須在建構時失敗。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic", "heal:single"],
                category=SkillCategory.UTILITY,
                effect_policies=(EffectPolicy(1.5),),
            )

    def test_skill_def_non_effect_policy_item_fails_construction(self):
        with self.assertRaises(ValueError):
            SkillDef(
                key="t_potency_bad_item",
                label="測試非政策項目",
                description="政策元素型別不符必須在建構時失敗。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic"],
                category=SkillCategory.UTILITY,
                effect_policies=("bad",),
            )

    def test_skill_def_rejects_non_identity_policy_on_unsupported_effects(self):
        for unsupported in ("cleanse:status", "buff_apply:brave", "pleasure:test"):
            with self.subTest(effect=unsupported):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_potency_unsupported",
                        label="測試不支援效果",
                        description="不支援威力的效果前綴宣告非 1.0 係數必須被拒絕。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.SINGLE,
                        cost={"mp": 10},
                        usable_out_of_combat=False,
                        element=None,
                        effects=[unsupported],
                        category=SkillCategory.UTILITY,
                        effect_policies=(EffectPolicy(2.0),),
                    )

    def test_skill_def_accepts_identity_policy_on_unsupported_effects(self):
        skill = SkillDef(
            key="t_potency_cleanse_identity",
            label="測試支援單位政策",
            description="不支援威力的效果宣告 1.0 係數可以合法建構。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={"mp": 10},
            usable_out_of_combat=False,
            element=None,
            effects=["cleanse:status"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(1.0),),
        )
        self.assertEqual(skill.effect_policies, (EffectPolicy(1.0),))

    def test_repeated_prefixes_retain_independent_policies(self):
        skill = SkillDef(
            key="t_potency_repeated",
            label="測試重複前綴",
            description="重複效果前綴依序數各自綁定相異係數。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={"mp": 15},
            usable_out_of_combat=False,
            element=None,
            effects=["damage:fire:magic", "damage:fire:magic"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(1.5), EffectPolicy(2.5)),
        )
        self.assertEqual(skill.effect_policies[0].coefficient, 1.5)
        self.assertEqual(skill.effect_policies[1].coefficient, 2.5)

    def test_authoring_helpers_forward_effect_policies(self):
        skill = _skill(
            "t_skill_helper",
            "測試輔助函式",
            "說明",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            category=SkillCategory.UTILITY,
            effects=["damage:fire:magic"],
            effect_policies=(EffectPolicy(1.8),),
        )
        self.assertEqual(skill.effect_policies[0].coefficient, 1.8)

        spell = _spell(
            "t_spell_helper",
            "測試法術輔助函式",
            "說明",
            TargetSpec.SINGLE,
            mp=20,
            element="fire",
            effects=("damage:fire:magic",),
            category=SkillCategory.ELEMENTAL_MAGIC,
            effect_policies=(EffectPolicy(3.2),),
        )
        self.assertEqual(spell.effect_policies[0].coefficient, 3.2)


class DirectHandlerPotencyTests(unittest.TestCase):
    """Formula and direct-handler behavior with effect potency."""

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_damage_scales_attack_component_before_defense_subtraction(self):
        actor = FakeEntity("actor", atk_phys=50, agility=10)
        target = FakeEntity("target", hp=100, agility=10, defense=20)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            # Roll 60 gives hit with base_multiplier 1.0.
            # Potency 1.0: round(50 * 1.0 * 1.0) - 20 = 30
            pending_1 = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": ResolvedEffect(EffectPolicy(1.0))},
                1.0,
            )[0]
            # Potency 2.0: round(50 * 1.0 * 2.0) - 20 = 80
            # (If it scaled after defense, it would be (50 - 20) * 2 = 60)
            pending_2 = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": ResolvedEffect(EffectPolicy(2.0))},
                1.0,
            )[0]

        amt_1 = int(pending_1.description.rsplit("|", 1)[1])
        amt_2 = int(pending_2.description.rsplit("|", 1)[1])
        self.assertEqual(amt_1, 30)
        self.assertEqual(amt_2, 80)

    def test_direct_damage_handler_defaults_to_identity_without_binding(self):
        actor = FakeEntity("actor", atk_phys=40, agility=10)
        target = FakeEntity("target", hp=100, agility=10, defense=10)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            pending_empty = _handle_damage(
                actor, [target], "damage:dark:physical", {}, 1.0
            )[0]
            pending_forged = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": "fake_string"},
                1.0,
            )[0]

        amt_empty = int(pending_empty.description.rsplit("|", 1)[1])
        amt_forged = int(pending_forged.description.rsplit("|", 1)[1])
        self.assertEqual(amt_empty, 30)  # 40 - 10
        self.assertEqual(amt_forged, 30)

    def test_miss_deals_zero_damage_and_no_floor_even_with_high_potency(self):
        actor = FakeEntity("actor", atk_phys=10, agility=10)
        target = FakeEntity("target", hp=100, agility=90, defense=50)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            pending = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": ResolvedEffect(EffectPolicy(5.0))},
                1.0,
            )[0]
        self.assertTrue(pending.description.endswith("|0|0"))
        pending.apply()
        self.assertEqual(target.traits.hp.value, 100)

    def test_sub_one_potency_respects_damage_floor_on_hit(self):
        actor = FakeEntity("actor", atk_phys=10, agility=10)
        target = FakeEntity("target", hp=100, agility=10, defense=50)
        floor = int(COMBAT_YAML["damage"]["floor"])
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            pending = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": ResolvedEffect(EffectPolicy(0.1))},
                1.0,
            )[0]
        amt = int(pending.description.rsplit("|", 1)[1])
        self.assertEqual(amt, floor)

    def test_crit_multiplier_composes_with_potency(self):
        actor = FakeEntity("actor", atk_phys=20, agility=10)
        target = FakeEntity("target", hp=100, agility=10, defense=5)
        crit_mult = float(COMBAT_YAML["damage"]["crit_multiplier"])
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            pending = _handle_damage(
                actor,
                [target],
                "damage:dark:physical",
                {"resolved_effect": ResolvedEffect(EffectPolicy(2.5))},
                1.0,
            )[0]
        amt = int(pending.description.rsplit("|", 1)[1])
        # round(20 * crit_mult * 2.5) - 5
        expected = round(20 * crit_mult * 2.5) - 5
        self.assertEqual(amt, expected)

    def test_heal_magnitude_inserts_coefficient_before_rounding_and_gain(self):
        actor = FakeEntity("actor", magic_power=35)
        mult = float(COMBAT_YAML["heal"]["multiplier"])
        floor = int(COMBAT_YAML["heal"]["floor"])

        # Baseline potency 1.0: max(round(35 * mult * 1.0), floor)
        self.assertEqual(_heal_magnitude(actor, 1.0), max(round(35 * mult), floor))
        # Potency 2.0: max(round(35 * mult * 2.0), floor)
        self.assertEqual(_heal_magnitude(actor, 2.0), max(round(35 * mult * 2.0), floor))

    def test_heal_magnitude_sub_one_potency_respects_floor(self):
        actor = FakeEntity("actor", magic_power=1)
        floor = int(COMBAT_YAML["heal"]["floor"])
        # magic 1 * mult 1.0 * coef 0.01 = 0.01 -> round is 0 -> clamped to floor (1)
        self.assertEqual(_heal_magnitude(actor, 0.01), floor)

    def test_heal_magnitude_discriminates_formula_ordering_with_heal_gain(self):
        # magic 33, mult 1.0, potency 2.0, heal_gain "+15%".
        # Correct order (potency before gain):
        #   round(33 * 1.0 * 2.0) = 66
        #   floor(66 * 1.15) = floor(75.9) = 75
        # Swapped order (gain before potency):
        #   floor(33 * 1.15) = 37
        #   round(37 * 2.0) = 74 != 75
        actor = FakeEntity("actor", magic_power=33)
        with patch("world.rules.combat.healing.evaluate_combat_modifiers", return_value={"heal_gain": "+15%"}), patch(
            "world.rules.combat.battlefield.evaluate_combat_modifiers", return_value={"heal_gain": "+15%"}
        ):
            mag = _heal_magnitude(actor, 2.0)
        self.assertEqual(mag, 75)
        self.assertNotEqual(mag, 74)

    def test_direct_heal_handler_defaults_to_identity_without_binding(self):
        actor = FakeEntity("actor", magic_power=30)
        target = FakeEntity("target", hp=20, max_hp=100)
        pending_empty = _handle_heal(
            actor, [target], "heal:single", {}, 1.0
        )[0]
        pending_forged = _handle_heal(
            actor, [target], "heal:single", {"resolved_effect": {"fake": 99}}, 1.0
        )[0]

        amt_empty = int(pending_empty.description.rsplit("|", 1)[1])
        amt_forged = int(pending_forged.description.rsplit("|", 1)[1])
        expected = _heal_magnitude(actor, 1.0)
        self.assertEqual(amt_empty, expected)
        self.assertEqual(amt_forged, expected)

    def test_heal_and_self_heal_clamp_at_hp_gap_and_never_revive(self):
        actor = FakeEntity("actor", hp=0, max_hp=100, magic_power=40)
        target = FakeEntity("target", hp=0, max_hp=100)

        # Target at 0 HP restores 0
        pending_heal = _handle_heal(
            actor,
            [target],
            "heal:single",
            {"resolved_effect": ResolvedEffect(EffectPolicy(3.0))},
            1.0,
        )[0]
        self.assertEqual(int(pending_heal.description.rsplit("|", 1)[1]), 0)
        pending_heal.apply()
        self.assertEqual(target.traits.hp.value, 0)

        # Actor at 0 HP restores 0
        pending_self = _handle_self_heal(
            actor,
            [],
            "self_heal",
            {"resolved_effect": ResolvedEffect(EffectPolicy(3.0))},
            1.0,
        )[0]
        self.assertEqual(int(pending_self.description.rsplit("|", 1)[1]), 0)
        pending_self.apply()
        self.assertEqual(actor.traits.hp.value, 0)


class ActionResolverPotencyPipelineTests(EvenniaTestCase):
    """End-to-end ActionResolver preflight and resolution with potency."""

    def setUp(self):
        super().setUp()
        self.caster = create_object(PlayerCharacter, key="caster")
        self.target = create_object(PlayerCharacter, key="target")
        self.ally = create_object(PlayerCharacter, key="ally")
        for char in (self.caster, self.target, self.ally):
            char.race = "human"
            char.apply_race_baseline()
            char.db.skills = {"active": [], "passive": []}
            char.traits.agility.base = 10
            char.traits.defense.base = 5
        self.caster.traits.atk_phys.base = 30
        self.caster.traits.magic_power.base = 30
        self.caster.traits.mp.current = 100
        self.target.traits.hp.current = 100
        self.target.traits.defense.base = 10
        self.ally.traits.hp.current = 40

        self.battlefield = Battlefield(
            {
                "party": frozenset({"caster", "ally"}),
                "foes": frozenset({"target"}),
            },
            {
                "caster": self.caster,
                "target": self.target,
                "ally": self.ally,
            },
        )

    def _register_skill(self, skill: SkillDef) -> SkillDef:
        mod_name, attr = REGISTRY_TARGETS["skills"]
        registry = getattr(importlib.import_module(mod_name), attr)
        previous = registry.get(skill.key)

        def _cleanup():
            if previous is None:
                registry.pop(skill.key, None)
            else:
                registry[skill.key] = previous

        self.addCleanup(_cleanup)
        registry[skill.key] = skill
        self.caster.db.skills["active"].append(skill.key)
        return skill

    @covers_requirement(
        "skill-effect-model::per-effect-potency-is-validated-independently-of-effect-identity"
    )
    def test_repeated_effects_retain_independent_potency(self):
        # A synthetic skill with two damage strikes of coefficients 1.0 and 2.0.
        skill = self._register_skill(
            SkillDef(
                key="t_double_strike",
                label="雙重突刺",
                description="兩段獨立威力的連續打擊。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:dark:physical", "damage:dark:physical"],
                category=SkillCategory.MARTIAL_ARTS,
                effect_policies=(EffectPolicy(1.0), EffectPolicy(2.0)),
            )
        )
        req = ActionRequest(
            self.caster,
            skill.key,
            [self.target],
            BattlefieldActionContext(self.battlefield),
        )
        pre = ActionResolver.preflight(req)
        self.assertEqual(pre.outcome, "success")

        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        # Verify event log contains two distinct damage amounts:
        # Base multiplier at roll 60 is 1.0. Attack = 30, Target defense = 10.
        # Strike 1 (pot 1.0): 30 * 1.0 * 1.0 - 10 = 20
        # Strike 2 (pot 2.0): 30 * 1.0 * 2.0 - 10 = 50
        damage_entries = [e for e in res.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(damage_entries), 2)
        self.assertEqual(damage_entries[0].data["amount"], 20)
        self.assertEqual(damage_entries[1].data["amount"], 50)
        # Total HP loss on target = 20 + 50 = 70 (100 -> 30)
        self.assertEqual(self.target.traits.hp.current, 30)

    def test_forged_context_is_overwritten_by_authored_policy(self):
        skill = self._register_skill(
            SkillDef(
                key="t_single_strike",
                label="單次突刺",
                description="單次標準威力打擊。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:dark:physical"],
                category=SkillCategory.MARTIAL_ARTS,
                effect_policies=(EffectPolicy(1.0),),
            )
        )
        # Attacker tries to inject a 999.0 coefficient in event_context:
        forged_context = BattlefieldActionContext(
            self.battlefield,
            event_context={"resolved_effect": ResolvedEffect(EffectPolicy(999.0))},
        )
        req = ActionRequest(self.caster, skill.key, [self.target], forged_context)

        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        damage_entries = [e for e in res.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(damage_entries), 1)
        # Should be authored 1.0 potency (amount 20), NOT forged 999.0:
        self.assertEqual(damage_entries[0].data["amount"], 20)
        # Verify forged_context.event_context was not mutated:
        self.assertEqual(
            forged_context.event_context["resolved_effect"].policy.coefficient,
            999.0,
        )

    def test_healing_composes_with_potency_and_remains_capped(self):
        skill = self._register_skill(
            SkillDef(
                key="t_potent_heal",
                label="強力治癒",
                description="高係數治療法術。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 15},
                usable_out_of_combat=False,
                element=None,
                effects=["heal:single"],
                category=SkillCategory.UTILITY,
                effect_policies=(EffectPolicy(2.0),),
            )
        )
        # Target has hp 40, max 100 (gap = 60).
        self.ally.traits.hp.current = 40
        req = ActionRequest(
            self.caster,
            skill.key,
            [self.ally],
            BattlefieldActionContext(self.battlefield),
        )

        with patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        heal_entries = [e for e in res.event_log.entries if e.kind == "heal"]
        self.assertEqual(len(heal_entries), 1)
        expected_heal = _heal_magnitude(self.caster, 2.0)
        # Expected heal should be applied, clamped to gap 60:
        applied = min(60, expected_heal)
        self.assertEqual(heal_entries[0].data["amount"], applied)
        self.assertEqual(self.ally.traits.hp.current, 40 + applied)

    def test_healing_composes_potency_equipment_gain_and_freeform_scale(self):
        # Caster magic_power = 33, ally hp gap = 100.
        # Skill: heal:single with potency 2.0. Scale = 0.5.
        # heal_gain = "+15%".
        # Magnitude = 75 (tested above).
        # Scaled magnitude = scaled_magnitude(75, 0.5) = round(75 * 0.5) = round(37.5) = 38.
        self.caster.traits.magic_power.base = 33
        self.ally.traits.hp.current = 20
        self.ally.traits.hp.base = 100
        skill = self._register_skill(
            SkillDef(
                key="t_scale_heal",
                label="縮放治癒",
                description="測試威力、裝備與自由施法比例的完整合成。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 20},
                usable_out_of_combat=True,
                element="light",
                effects=["heal:single"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(EffectPolicy(2.0),),
            )
        )
        req = ActionRequest(
            self.caster,
            skill.key,
            [self.ally],
            BattlefieldActionContext(self.battlefield),
            scale=0.5,
        )
        with (
            patch("world.rules.combat.healing.evaluate_combat_modifiers", return_value={"heal_gain": "+15%"}),
            patch("world.rules.combat.battlefield.evaluate_combat_modifiers", return_value={"heal_gain": "+15%"}),
            patch("world.rules.action.gates.is_freeform_eligible", return_value=True),
            patch("world.rules.action.gates.freeform_scales_for", return_value=(0.5, 1.0)),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        heal_entries = [e for e in res.event_log.entries if e.kind == "heal"]
        self.assertEqual(len(heal_entries), 1)
        self.assertEqual(heal_entries[0].data["amount"], 38)
        self.assertEqual(self.ally.traits.hp.current, 20 + 38)

    def test_potency_does_not_alter_mp_deduction(self):
        skill = self._register_skill(
            SkillDef(
                key="t_cost_check",
                label="魔力消耗檢驗",
                description="檢驗威力係數不影響 MP 消耗。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 25},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:dark:physical"],
                category=SkillCategory.MARTIAL_ARTS,
                effect_policies=(EffectPolicy(3.5),),
            )
        )
        initial_mp = self.caster.traits.mp.current
        req = ActionRequest(
            self.caster,
            skill.key,
            [self.target],
            BattlefieldActionContext(self.battlefield),
        )
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.caster.traits.mp.current, initial_mp - 25)

    def test_transaction_rollback_restores_state_on_late_failure(self):
        skill = self._register_skill(
            SkillDef(
                key="t_rollback_strike",
                label="回滾測試突刺",
                description="測試後續失敗時的狀態回滾。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:dark:physical"],
                category=SkillCategory.MARTIAL_ARTS,
                effect_policies=(EffectPolicy(2.0),),
            )
        )
        initial_hp = self.target.traits.hp.current
        initial_mp = self.caster.traits.mp.current
        req = ActionRequest(
            self.caster,
            skill.key,
            [self.target],
            BattlefieldActionContext(self.battlefield),
        )

        def _failing_planner(request, event_log):
            def _raise():
                raise RuntimeError("simulated late commit failure")
            return [
                PendingEffect(
                    entity=self.target,
                    description="failing_late_effect",
                    surfaces=frozenset({"traits"}),
                    apply=_raise,
                )
            ]

        self.addCleanup(_EVENT_EFFECT_PLANNERS.pop, "test_failing_late", None)
        _EVENT_EFFECT_PLANNERS["test_failing_late"] = _failing_planner

        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.damage.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(self.target.traits.hp.current, initial_hp)
        self.assertEqual(self.caster.traits.mp.current, initial_mp)
