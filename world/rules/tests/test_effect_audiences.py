"""Unit and integration behavior tests for effect audience routing.

Covers:
- EffectAudience enum values and EffectPolicy validation (skill-effect-model).
- Contradictory audience rejection on actor-bound and target-only effects (skill-effect-model).
- Pure audience planning function for preflight and resolution (action-resolution-pipeline).
- Per-effect subset delivery over validated selection (mixed damage + cleanse).
- Ordinary friendly fire on companion attacks and enemy healing reachability.
- Independent explicit self binding with presence/alive/range checks.
- One-empty audience skipping without roll and single cost payment.
- All-empty audiences rejection before resource, time, or practice deduction.
- Dynamic relationship updates between preflight and resolve.
- Late commit rollback restoring all touched recipients including self-bound actor.
- Practice deduplication per distinct delivered recipient.
- Second synthetic configuration for alternate-element generic mechanics reuse.
- ActionPreview and shorthand integration for audience-routed skills.
"""

from copy import deepcopy
from dataclasses import replace
import importlib
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    RejectedAction,
    _stored_trait_value,
    plan_effect_audiences,
)
from world.rules.action_preview import (
    _applicable_shorthands,
    preview_skill,
    revalidate_submission,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)
from world.rules.targeting import (
    ActionContext,
    Relation,
    RoomActionContext,
    TargetRequirement,
)
from world.rules.tests.combat_fixtures import FakeEntity
from world.skills.effects import (
    ActorSexualEventEffect,
    ClampShameEffect,
    ClimaxExtensionStageEffect,
    DamageEffect,
    DivinePleasureMaxEffect,
    EffectAudience,
    EffectPolicy,
    HealEffect,
    MarkSubmissionEffect,
    RestorePurityEffect,
    SaturateSensitivityEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualDrainEffect,
    TargetSexualEventEffect,
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


class MockContext:
    """Lightweight ActionContext implementation for pure planning unit tests."""

    def __init__(
        self,
        relations: dict[tuple[str, str], Relation] | None = None,
        present: set[tuple[str, str]] | None = None,
        in_range: set[tuple[str, str]] | None = None,
        battlefield: Battlefield | None = None,
    ):
        self.relations = relations or {}
        self.present = present
        self.in_range = in_range
        self.battlefield = battlefield
        self.event_context: dict = {}

    def is_present(self, actor: FakeEntity, target: FakeEntity) -> bool:
        if self.present is None:
            return True
        return (actor.key, target.key) in self.present

    def relation_to(self, actor: FakeEntity, target: FakeEntity) -> Relation:
        if actor is target or actor.key == target.key:
            return Relation.SELF
        return self.relations.get((actor.key, target.key), Relation.ENEMY)

    def is_in_range(self, actor: FakeEntity, target: FakeEntity) -> bool:
        if self.in_range is None:
            return True
        return (actor.key, target.key) in self.in_range


class EffectAudienceAuthoringTests(unittest.TestCase):
    """Immutable per-occurrence policy validation for effect audiences."""

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_effect_policy_defaults_to_selected_audience(self):
        policy = EffectPolicy()
        self.assertEqual(policy.coefficient, 1.0)
        self.assertIs(policy.audience, EffectAudience.SELECTED)

    def test_effect_policy_normalizes_string_to_enum(self):
        policy = EffectPolicy(audience="allies")
        self.assertIs(policy.audience, EffectAudience.ALLIES)
        self.assertEqual(policy.audience, "allies")

        policy_self = EffectPolicy(audience="self")
        self.assertIs(policy_self.audience, EffectAudience.SELF)

        policy_enemies = EffectPolicy(audience="enemies")
        self.assertIs(policy_enemies.audience, EffectAudience.ENEMIES)

    def test_effect_policy_rejects_invalid_audience_types_and_values(self):
        for bad in (None, 123, True, False, [], {}, "unknown_audience", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    EffectPolicy(audience=bad)

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_inherently_actor_bound_effects_reject_allies_and_enemies(self):
        # SelfHealEffect, ActorSexualEventEffect, SelfBuffApplyEffect
        for bad_aud in (EffectAudience.ALLIES, EffectAudience.ENEMIES):
            with self.subTest(bad_aud=bad_aud):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_bad_self_heal",
                        label="測試無效自療",
                        description="測試不合法受眾配置。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.SELF,
                        cost={},
                        usable_out_of_combat=True,
                        element=None,
                        effects=["self_heal"],
                        category=SkillCategory.UTILITY,
                        effect_policies=(EffectPolicy(audience=bad_aud),),
                    )

                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_bad_self_buff",
                        label="測試無效自身增益",
                        description="測試不合法受眾配置。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.NONE,
                        cost={},
                        usable_out_of_combat=True,
                        element=None,
                        effects=["self_buff_apply:focus"],
                        category=SkillCategory.ENHANCEMENT,
                        effect_policies=(EffectPolicy(audience=bad_aud),),
                    )

    def test_inherently_actor_bound_effects_accept_self_and_selected(self):
        skill_self = SkillDef(
            key="t_ok_self_heal",
            label="合法自療",
            description="合法自身受眾自療。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["self_heal"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(audience=EffectAudience.SELF),),
        )
        self.assertIs(skill_self.effect_policies[0].audience, EffectAudience.SELF)

        skill_selected = SkillDef(
            key="t_ok_self_buff",
            label="合法自身增益",
            description="合法默認受眾自身增益。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.NONE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["self_buff_apply:focus"],
            category=SkillCategory.ENHANCEMENT,
            effect_policies=(EffectPolicy(audience=EffectAudience.SELECTED),),
        )
        self.assertIs(skill_selected.effect_policies[0].audience, EffectAudience.SELECTED)

    def test_target_only_effects_reject_self_audience(self):
        target_only_prefixes = [
            "sexual_event_target:stimulus_applied",
            "divine_pleasure_max:神之極致快感",
            "divine_climax_extension_stage:1",
            "divine_drain:神之汲取",
            "divine_saturate_sensitivity:神之敏感重塑",
            "divine_clamp_shame:神之羞恥剝奪",
            "divine_mark_submission:神之絕對從屬",
            "divine_restore_purity:神之純潔回歸",
        ]
        for effect_str in target_only_prefixes:
            with self.subTest(effect_str=effect_str):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_bad_target_only",
                        label="測試目標專用",
                        description="測試不合法受眾配置。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.SINGLE,
                        cost={},
                        usable_out_of_combat=True,
                        element=None,
                        effects=[effect_str],
                        category=SkillCategory.DIVINE_MYSTERY,
                        effect_policies=(EffectPolicy(audience=EffectAudience.SELF),),
                    )

    def test_target_spec_self_skill_rejects_enemies_audience(self):
        with self.assertRaises(ValueError):
            SkillDef(
                key="t_bad_self_enemies",
                label="測試自我技能聲明敵人受眾",
                description="測試矛盾配置。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=True,
                element=None,
                effects=["heal:single"],
                category=SkillCategory.UTILITY,
                effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
            )

    def test_target_spec_self_skill_accepts_allies_self_selected(self):
        for aud in (EffectAudience.SELF, EffectAudience.ALLIES, EffectAudience.SELECTED):
            with self.subTest(aud=aud):
                skill = SkillDef(
                    key=f"t_ok_self_{aud}",
                    label="合法自我技能",
                    description="合法自我受眾配置。",
                    kind=SkillKind.ACTIVE,
                    target_spec=TargetSpec.SELF,
                    cost={},
                    usable_out_of_combat=True,
                    element=None,
                    effects=["heal:single"],
                    category=SkillCategory.UTILITY,
                    effect_policies=(EffectPolicy(audience=aud),),
                )
                self.assertIs(skill.effect_policies[0].audience, aud)

    def test_target_spec_none_rejects_allies_and_enemies(self):
        for bad_aud in (EffectAudience.ALLIES, EffectAudience.ENEMIES):
            with self.subTest(bad_aud=bad_aud):
                with self.assertRaises(ValueError):
                    SkillDef(
                        key="t_bad_none_routed",
                        label="測試無目標聲明隊友或敵人",
                        description="測試矛盾配置。",
                        kind=SkillKind.ACTIVE,
                        target_spec=TargetSpec.NONE,
                        cost={},
                        usable_out_of_combat=True,
                        element=None,
                        effects=["heal:area"],
                        category=SkillCategory.UTILITY,
                        effect_policies=(EffectPolicy(audience=bad_aud),),
                    )

    def test_replace_renormalizes_default_effect_policies(self):
        skill = SkillDef(
            key="t_single",
            label="單一效果",
            description="測試單效果。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["damage:fire:magic"],
            category=SkillCategory.ELEMENTAL_MAGIC,
        )
        self.assertEqual(len(skill.effect_policies), 1)
        doubled = replace(skill, key="t_doubled", effects=["damage:fire:magic", "damage:fire:magic"])
        self.assertEqual(len(doubled.effect_policies), 2)
        self.assertEqual(doubled.effect_policies, (EffectPolicy(), EffectPolicy()))


class PureAudiencePlannerTests(unittest.TestCase):
    """Pure side-effect-free audience planning unit tests."""

    def setUp(self):
        self.actor = FakeEntity("actor", hp=100)
        self.ally = FakeEntity("ally", hp=100)
        self.enemy = FakeEntity("enemy", hp=100)
        self.bystander = FakeEntity("bystander", hp=100)
        self.context = MockContext(
            relations={
                (self.actor.key, self.ally.key): Relation.ALLY,
                (self.actor.key, self.enemy.key): Relation.ENEMY,
                (self.actor.key, self.bystander.key): Relation.ALLY,
            }
        )

    def test_selected_audience_uses_full_validated_pool(self):
        skill = SkillDef(
            key="t_selected",
            label="全體測試",
            description="全選受眾測試。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["heal:area"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(audience=EffectAudience.SELECTED),),
        )
        targets = [self.enemy, self.ally]
        routed = plan_effect_audiences(self.actor, self.context, skill, targets)
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0], targets)

    def test_allies_audience_filters_to_self_and_allies_without_adding_unselected(self):
        skill = SkillDef(
            key="t_allies",
            label="隊友受眾",
            description="隊友受眾測試。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["heal:area"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
        )
        # Selection has enemy and ally. Actor is not in targets.
        targets = [self.enemy, self.ally]
        routed = plan_effect_audiences(self.actor, self.context, skill, targets)
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0], [self.ally])
        # Crucial check: unselected bystander and unselected actor are NOT added!
        self.assertNotIn(self.actor, routed[0])
        self.assertNotIn(self.bystander, routed[0])

    def test_enemies_audience_filters_to_enemies_without_adding_unselected(self):
        skill = SkillDef(
            key="t_enemies",
            label="敵方受眾",
            description="敵方受眾測試。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["damage:fire:magic"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
        )
        targets = [self.ally, self.enemy]
        routed = plan_effect_audiences(self.actor, self.context, skill, targets)
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0], [self.enemy])

    def test_self_audience_binds_actor_once_independently(self):
        skill = SkillDef(
            key="t_self",
            label="自身受眾",
            description="自身受眾獨立綁定測試。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["heal:single"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(audience=EffectAudience.SELF),),
        )
        # Actor not in explicit targets
        routed = plan_effect_audiences(self.actor, self.context, skill, [self.enemy])
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0], [self.actor])

        # Actor already in targets
        routed_with_actor = plan_effect_audiences(
            self.actor, self.context, skill, [self.actor, self.enemy]
        )
        self.assertEqual(routed_with_actor[0], [self.actor])

    def test_self_audience_empty_when_actor_not_alive_or_not_present(self):
        skill = SkillDef(
            key="t_self_dead",
            label="自身測試",
            description="死者或不在場不滿足受眾。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["heal:single"],
            category=SkillCategory.UTILITY,
            effect_policies=(EffectPolicy(audience=EffectAudience.SELF),),
        )
        dead_actor = FakeEntity("dead_actor", hp=0)
        with self.assertRaises(RejectedAction) as cm_dead:
            plan_effect_audiences(dead_actor, self.context, skill, [dead_actor])
        self.assertEqual(cm_dead.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        not_present_context = MockContext(present=set())
        with self.assertRaises(RejectedAction) as cm_absent:
            plan_effect_audiences(self.actor, not_present_context, skill, [self.actor])
        self.assertEqual(cm_absent.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    def test_mixed_selected_and_non_selected_policy_combo(self):
        mixed_combo = SkillDef(
            key="t_mixed_combo",
            label="全選與路由混用",
            description="一項全選，一項限定敵人。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["heal:area", "damage:fire:magic"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            effect_policies=(
                EffectPolicy(audience=EffectAudience.SELECTED),
                EffectPolicy(audience=EffectAudience.ENEMIES),
            ),
        )
        # When targets has only allies: heal gets allies, damage gets empty list
        routed = plan_effect_audiences(self.actor, self.context, mixed_combo, [self.ally])
        self.assertEqual(routed[0], [self.ally])
        self.assertEqual(routed[1], [])

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_mixed_spell_one_empty_and_all_empty(self):
        mixed_skill = SkillDef(
            key="t_mixed",
            label="混合法術",
            description="敵傷友癒。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.AREA,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["damage:fire:magic", "heal:area"],
            category=SkillCategory.ELEMENTAL_MAGIC,
            effect_policies=(
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
        )
        # Both present
        routed_both = plan_effect_audiences(
            self.actor, self.context, mixed_skill, [self.enemy, self.ally]
        )
        self.assertEqual(routed_both[0], [self.enemy])
        self.assertEqual(routed_both[1], [self.ally])

        # Only allies present: damage audience is empty, heal is not
        routed_allies = plan_effect_audiences(
            self.actor, self.context, mixed_skill, [self.ally]
        )
        self.assertEqual(routed_allies[0], [])
        self.assertEqual(routed_allies[1], [self.ally])

        # All empty (e.g. empty target list for routed skill): raises rejection
        with self.assertRaises(Exception) as cm:
            plan_effect_audiences(self.actor, self.context, mixed_skill, [])
        self.assertEqual(cm.exception.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)


class EffectRoutingPipelineTests(EvenniaTestCase):
    """End-to-end action pipeline resolution and preview tests with effect audiences."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="test_room")
        self.caster = create_object(PlayerCharacter, key="caster")
        self.target = create_object(PlayerCharacter, key="target")
        self.companion = create_object(PlayerCharacter, key="companion")
        self.bystander = create_object(PlayerCharacter, key="bystander")

        for char in (self.caster, self.target, self.companion, self.bystander):
            char.location = self.room
            char.race = "human"
            char.apply_race_baseline()
            char.db.skills = {"active": [], "passive": []}
            char.traits.agility.base = 10
            char.traits.defense.base = 5
            char.traits.hp.current = 100

        self.caster.traits.atk_phys.base = 30
        self.caster.traits.magic_power.base = 30
        self.caster.traits.mp.current = 100

        self.battlefield = Battlefield(
            {
                "party": frozenset({"caster", "companion", "bystander"}),
                "foes": frozenset({"target"}),
            },
            {
                "caster": self.caster,
                "target": self.target,
                "companion": self.companion,
                "bystander": self.bystander,
            },
        )
        self.context = BattlefieldActionContext(self.battlefield)

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

    def _register_synth_debuff(self, key: str = "t_synth_debuff") -> str:
        definition = BuffDefinition(
            key=key,
            duration=60,
            tick_interval=10,
            stacking="refresh",
            modifiers={},
            polarity="debuff",
        )
        BUFF_DEFINITIONS[key] = definition
        self.addCleanup(lambda: BUFF_DEFINITIONS.pop(key, None))
        return key

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_mixed_spell_damages_enemies_and_cleanses_allies(self):
        # Scenario: ENEMIES damage + ALLIES cleanse
        debuff_key = self._register_synth_debuff()
        apply_buff(self.target, debuff_key)
        apply_buff(self.companion, debuff_key)
        apply_buff(self.bystander, debuff_key)

        self.assertEqual(len(entity_active_buffs(self.target)), 1)
        self.assertEqual(len(entity_active_buffs(self.companion)), 1)
        self.assertEqual(len(entity_active_buffs(self.bystander)), 1)

        target_hp_before = self.target.traits.hp.current
        comp_hp_before = self.companion.traits.hp.current

        skill = self._register_skill(
            SkillDef(
                key="t_radiance_mixed",
                label="測試耀光",
                description="對敵人造成傷害，淨化隊友負面狀態。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic", "cleanse:status"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(audience=EffectAudience.ALLIES),
                ),
            )
        )

        req = ActionRequest(
            self.caster,
            skill.key,
            [self.target, self.companion],
            self.context,
        )

        with (
            patch("world.rules.combat.roll_d100", return_value=60),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        # Target (enemy): took damage, debuff NOT cleansed
        self.assertLess(self.target.traits.hp.current, target_hp_before)
        self.assertEqual(len(entity_active_buffs(self.target)), 1)

        # Companion (ally): took NO damage, debuff IS cleansed!
        self.assertEqual(self.companion.traits.hp.current, comp_hp_before)
        self.assertEqual(len(entity_active_buffs(self.companion)), 0)

        # Bystander (unselected): untouched
        self.assertEqual(len(entity_active_buffs(self.bystander)), 1)

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_unconfigured_attack_damages_companion(self):
        # Scenario: unconfigured attack targets a companion -> companion takes damage
        skill = self._register_skill(
            SkillDef(
                key="t_atk_free",
                label="無受眾攻擊",
                description="自由攻擊目標。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 5},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic"],
                category=SkillCategory.ELEMENTAL_MAGIC,
            )
        )
        comp_hp = self.companion.traits.hp.current
        req = ActionRequest(self.caster, skill.key, [self.companion], self.context)
        with (
            patch("world.rules.combat.roll_d100", return_value=60),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertLess(self.companion.traits.hp.current, comp_hp)

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_unconfigured_heal_heals_enemy(self):
        # Scenario: unconfigured heal targets an enemy -> enemy recovers
        skill = self._register_skill(
            SkillDef(
                key="t_heal_free",
                label="無受眾治療",
                description="自由治療目標。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 5},
                usable_out_of_combat=True,
                element=None,
                effects=["heal:single"],
                category=SkillCategory.UTILITY,
            )
        )
        self.target.traits.hp.current = 40
        req = ActionRequest(self.caster, skill.key, [self.target], self.context)
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertGreater(self.target.traits.hp.current, 40)

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_explicit_self_binding_independent_of_pool(self):
        # Scenario: caster not in pool, but one effect is self-bound -> caster receives it once
        skill = self._register_skill(
            SkillDef(
                key="t_strike_self_heal",
                label="吸取突刺",
                description="打擊敵人並治癒自身。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic", "heal:single"],
                category=SkillCategory.MARTIAL_ARTS,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(audience=EffectAudience.SELF),
                ),
            )
        )
        self.caster.traits.hp.current = 50
        req = ActionRequest(self.caster, skill.key, [self.target], self.context)
        with (
            patch("world.rules.combat.roll_d100", return_value=60),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertGreater(self.caster.traits.hp.current, 50)
        # Verify caster appears in event log
        self.assertIn("caster", res.event_log.targets)

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_one_audience_empty_skips_without_roll_and_pays_once(self):
        # Scenario: authored mixed spell has allies in selection but no enemies
        skill = self._register_skill(
            SkillDef(
                key="t_mixed_one_empty",
                label="混合單空",
                description="敵傷友癒。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic", "heal:area"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(audience=EffectAudience.ALLIES),
                ),
            )
        )
        self.companion.traits.hp.current = 50
        mp_before = self.caster.traits.mp.current
        req = ActionRequest(self.caster, skill.key, [self.companion], self.context)

        with (
            patch("world.rules.combat.roll_d100") as mock_roll,
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        # Damage was skipped: roll_d100 was NEVER called
        mock_roll.assert_not_called()
        # Heal was applied
        self.assertGreater(self.companion.traits.hp.current, 50)
        # MP deducted once
        self.assertEqual(self.caster.traits.mp.current, mp_before - 10)

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_all_audiences_empty_rejects_before_resources_time_practice(self):
        # Scenario: every configured component has no valid recipient -> action rejected
        skill = self._register_skill(
            SkillDef(
                key="t_enemy_only_aoe",
                label="純敵人群體",
                description="僅對敵人造成傷害。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 15},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
            )
        )
        mp_before = self.caster.traits.mp.current
        req = ActionRequest(self.caster, skill.key, [self.companion], self.context)

        # Preflight rejects
        pre = ActionResolver.preflight(req)
        self.assertEqual(pre.outcome, "rejected")
        self.assertEqual(pre.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        # Resolve rejects
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(res.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        # No MP deducted, time is None, no event log
        self.assertEqual(self.caster.traits.mp.current, mp_before)
        self.assertIsNone(res.time_cost_seconds)
        self.assertIsNone(res.event_log)

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_relationship_change_between_preflight_and_resolve(self):
        # Scenario: preflight succeeds against enemy; relation flips before resolve -> resolve rejects
        skill = self._register_skill(
            SkillDef(
                key="t_enemies_dynamic",
                label="動態敵方",
                description="僅對敵人施放。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
            )
        )
        req = ActionRequest(self.caster, skill.key, [self.target], self.context)
        pre = ActionResolver.preflight(req)
        self.assertEqual(pre.outcome, "success")

        # Now target flips teams to the caster's party
        self.battlefield.teams["party"] = frozenset({"caster", "companion", "target"})
        self.battlefield.teams["foes"] = frozenset()

        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(res.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_late_failure_rollback_restores_all_recipients_including_self(self):
        # Scenario: late error restores all actual recipients including self-bound actor
        skill = self._register_skill(
            SkillDef(
                key="t_late_fail_mixed",
                label="回滾測試",
                description="中途失敗應回滾全體受眾狀態。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic", "heal:area"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(audience=EffectAudience.SELF),
                ),
            )
        )
        self.caster.traits.hp.current = 60
        target_before = self.target.traits.hp.current
        caster_before = self.caster.traits.hp.current
        mp_before = self.caster.traits.mp.current

        req = ActionRequest(self.caster, skill.key, [self.target], self.context)

        # Inject an error in event effect planners (commit stage)
        with (
            patch("world.rules.combat.roll_d100", return_value=60),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch.dict(
                "world.rules.action._EVENT_EFFECT_PLANNERS",
                {
                    "test_bomb": lambda req, log: [
                        PendingEffect(
                            self.target,
                            "invalid_unsupported_surface",
                            frozenset({"unsupported_surface_bomb"}),
                            lambda: None,
                        )
                    ]
                },
            ),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "rejected")
        # Verify rollback restored target, caster hp, and caster mp
        self.assertEqual(self.target.traits.hp.current, target_before)
        self.assertEqual(self.caster.traits.hp.current, caster_before)
        self.assertEqual(self.caster.traits.mp.current, mp_before)

    def test_practice_deduplicated_per_distinct_delivered_recipient(self):
        # Mixed spell with two effects both landing on the same companion
        skill = self._register_skill(
            SkillDef(
                key="t_multi_ally",
                label="多重隊友技能",
                description="同時治癒並淨化隊友。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["heal:area", "cleanse:status"],
                category=SkillCategory.UTILITY,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ALLIES),
                    EffectPolicy(audience=EffectAudience.ALLIES),
                ),
            )
        )
        self.companion.traits.hp.current = 60
        req = ActionRequest(self.caster, skill.key, [self.companion], self.context)
        with patch("world.rules.action.grant_skill_practice_xp", return_value=True) as mock_grant:
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Companion received TWO effects (heal + cleanse), but grant_skill_practice_xp was called ONCE for companion!
        self.assertEqual(mock_grant.call_count, 1)
        args, kwargs = mock_grant.call_args
        self.assertIs(kwargs.get("target") or args[2], self.companion)

    def test_none_spec_actor_binding_skill_resolves_and_practices(self):
        # TargetSpec.NONE with self_buff_apply applies buff to actor and awards practice vs None
        skill = self._register_skill(
            SkillDef(
                key="t_none_buff",
                label="自身專注",
                description="無目標技能對自身生效。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.NONE,
                cost={"mp": 5},
                usable_out_of_combat=True,
                element=None,
                effects=["self_buff_apply:focus"],
                category=SkillCategory.ENHANCEMENT,
            )
        )
        req = ActionRequest(self.caster, skill.key, [], RoomActionContext(self.room))
        with patch("world.rules.action.grant_skill_practice_xp", return_value=True) as mock_grant:
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Verified practiced vs None
        args, kwargs = mock_grant.call_args
        self.assertIsNone(kwargs.get("target"))

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    def test_second_synthetic_configuration_alternate_element(self):
        # Alternate element (water/earth) synthetic configuration proving generic mechanism reuse
        debuff_key = self._register_synth_debuff("t_water_debuff")
        apply_buff(self.target, debuff_key)
        apply_buff(self.companion, debuff_key)

        water_spell = self._register_skill(
            SkillDef(
                key="t_azure_tide",
                label="碧潮洗滌",
                description="水系複合效果：對敵人造成水傷害，洗滌隊友負面狀態。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 12},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:water:magic", "cleanse:status"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(audience=EffectAudience.ALLIES),
                ),
            )
        )
        req = ActionRequest(self.caster, water_spell.key, [self.target, self.companion], self.context)
        with (
            patch("world.rules.combat.roll_d100", return_value=60),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        # Target took water damage and kept debuff
        damage_entry = [e for e in res.event_log.entries if e.kind == "damage"][0]
        self.assertEqual(damage_entry.target, "target")
        self.assertEqual(len(entity_active_buffs(self.target)), 1)
        # Companion was cleansed and took no damage
        self.assertEqual(len(entity_active_buffs(self.companion)), 0)

    def test_preview_and_shorthand_filtering(self):
        skill = self._register_skill(
            SkillDef(
                key="t_enemy_preview",
                label="預覽敵方測試",
                description="敵方限定範圍技能。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 10},
                usable_out_of_combat=False,
                element=None,
                effects=["damage:fire:magic"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(EffectPolicy(audience=EffectAudience.ENEMIES),),
            )
        )
        # Candidates with only allies -> preview disabled with NO_VALID_TARGETS_IN_AREA
        preview_allies = preview_skill(
            self.caster, skill.key, self.context, candidates=[self.companion]
        )
        self.assertFalse(preview_allies.enabled)
        self.assertEqual(preview_allies.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)

        # Candidates with enemy -> preview enabled
        preview_enemy = preview_skill(
            self.caster, skill.key, self.context, candidates=[self.target]
        )
        self.assertTrue(preview_enemy.enabled)
        self.assertEqual(preview_enemy.valid_targets, (self.target,))

        # Shorthands: all-allies expands only to allies, so it must NOT be an applicable shorthand for ENEMIES skill
        shorthands = _applicable_shorthands(self.caster, skill.key, self.context, skill)
        self.assertNotIn("all-allies", shorthands)
        self.assertIn("all-enemies", shorthands)
        self.assertIn("all", shorthands)

        # Revalidate submission: all-allies submission rejects
        reval_fail = revalidate_submission(
            self.caster, skill.key, self.context, targets=[self.companion]
        )
        self.assertFalse(reval_fail.enabled)
        self.assertEqual(reval_fail.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)
