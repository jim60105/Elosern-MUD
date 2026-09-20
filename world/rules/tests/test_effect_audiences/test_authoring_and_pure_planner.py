"""Slice of ``test_effect_audiences``: authoring validation and the pure
planner behavior.
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


from ._support import (
    MockContext,
)


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
