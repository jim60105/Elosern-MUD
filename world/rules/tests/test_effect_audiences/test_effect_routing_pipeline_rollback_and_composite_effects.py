"""Slice of ``test_effect_audiences``: EffectRoutingPipelineTests.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import unittest
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.objects.models import ObjectDB
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
    _EVENT_EFFECT_PLANNERS,
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
from world.rules.clock import get_world_clock
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

    @covers_requirement("skill-registry::light-spell-progression-composes-executable-recovery-and-judgment-behavior")
    def test_ordinary_recovery_and_mixed_policy_remain_distinct(self):
        """Scenario: Ordinary recovery and mixed policy remain distinct.

        WHEN ordinary recovery targets an enemy while a mixed spell selects both teams
        THEN ordinary recovery still applies and the mixed spell follows its explicitly separate effect audiences
        """
        # 1. Ordinary recovery (SELECTED audience) targeting an enemy in battle
        heal_skill = self._register_skill(
            SkillDef(
                key="t_synth_ord_heal",
                label="普通治療測試",
                description="單體治療。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 10},
                usable_out_of_combat=True,
                element=None,
                effects=["heal:single"],
                category=SkillCategory.ELEMENTAL_MAGIC,
            )
        )
        self.target.traits.hp.current = 50
        req_heal = ActionRequest(self.caster, heal_skill.key, [self.target], self.context)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
        ):
            res_heal = ActionResolver.resolve(req_heal)
        self.assertEqual(res_heal.outcome, "success")
        self.assertGreater(self.target.traits.hp.current, 50)

        # 2. Mixed spell selects both teams -> damage to enemy, cleanse to ally
        debuff_key = self._register_synth_debuff("t_synth_distinct_debuff")
        apply_buff(self.companion, debuff_key)
        self.assertEqual(len(entity_active_buffs(self.companion)), 1)
        mixed_skill = self._register_skill(
            SkillDef(
                key="t_synth_mixed_distinct",
                label="混編法術測試",
                description="敵方傷害我方淨化。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 20},
                usable_out_of_combat=True,
                element=None,
                effects=["damage:light:magic", "cleanse:status"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=2.0),
                    EffectPolicy(audience=EffectAudience.ALLIES),
                ),
            )
        )
        target_hp_before = self.target.traits.hp.current
        companion_hp_before = self.companion.traits.hp.current
        req_mixed = ActionRequest(self.caster, mixed_skill.key, [self.target, self.companion], self.context)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
        ):
            res_mixed = ActionResolver.resolve(req_mixed)
        self.assertEqual(res_mixed.outcome, "success")
        self.assertLess(self.target.traits.hp.current, target_hp_before)
        self.assertEqual(self.companion.traits.hp.current, companion_hp_before)
        self.assertEqual(len(entity_active_buffs(self.companion)), 0)

    @covers_requirement(
        "skill-registry::light-spell-progression-composes-executable-recovery-and-judgment-behavior",
        "monster-resource-abilities::穗鳴雀-payment-and-atomicity-retain-the-shared-transaction",
        "monster-resource-abilities::潮燈蟹-payment-and-atomicity-retain-the-shared-transaction",
    )
    def test_composite_effects_are_actual_state_changes_with_atomic_rollback(self):
        """Scenario: Composite effects are actual state changes."""
        debuff = self._register_synth_debuff()
        composite_skill = self._register_skill(
            SkillDef(
                key="t_synth_composite_atomic",
                label="複合狀態法術",
                description="友方治療敵方傷害。",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.AREA,
                cost={"mp": 25},
                usable_out_of_combat=True,
                element=None,
                effects=["heal:area", "damage:fire:magic", f"buff_apply:{debuff}"],
                category=SkillCategory.ELEMENTAL_MAGIC,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ALLIES, coefficient=2.0),
                    EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.5),
                    EffectPolicy(audience=EffectAudience.ENEMIES, requires_hit_from=1),
                ),
            )
        )
        self.companion.traits.hp.current = 50
        caster_mp_before = self.caster.traits.mp.current
        req = ActionRequest(self.caster, composite_skill.key, [self.companion, self.target], self.context)
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertEqual(self.caster.traits.mp.current, caster_mp_before - 25)
        self.assertGreater(self.companion.traits.hp.current, 50)
        self.assertLess(self.target.traits.hp.current, 100)
        self.assertEqual(self.bystander.traits.hp.current, 100)
        self.assertIn(debuff, entity_active_buffs(self.target))
        for untouched in (self.caster, self.companion, self.bystander):
            self.assertNotIn(debuff, entity_active_buffs(untouched))

        entities = (self.caster, self.companion, self.target, self.bystander)
        before = {
            entity.pk: (
                entity.traits.hp.current,
                entity.traits.mp.current,
                deepcopy(entity.db.buffs),
                deepcopy(entity.db.skill_proficiency),
            )
            for entity in entities
        }
        observed = []
        clock = get_world_clock()
        before_tick = clock.tick

        def fail_after_writes():
            observed.append((
                self.caster.traits.mp.current,
                self.companion.traits.hp.current,
                self.target.traits.hp.current,
            ))
            raise RuntimeError("injected after composite writes")

        def late_fault(_request, _log):
            return [PendingEffect(
                self.caster, "late composite fault",
                frozenset({"progression"}), fail_after_writes,
            )]

        with patch.dict(_EVENT_EFFECT_PLANNERS, {"t_late_fault": late_fault}), (
            patch("world.rules.combat.damage.roll_d100", return_value=60)
        ):
            failed = ActionResolver.resolve(req)
        self.assertNotEqual(failed.outcome, "success")
        self.assertIsNone(failed.event_log)
        self.assertIsNone(failed.time_cost_seconds)
        self.assertEqual(failed.notifications, ())
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(len(observed), 1)
        self.assertLess(observed[0][0], before[self.caster.pk][1])
        self.assertLess(observed[0][2], before[self.target.pk][0])
        for entity in entities:
            for actual in (entity, ObjectDB.objects.get(pk=entity.pk)):
                self.assertEqual((
                    actual.traits.hp.current,
                    actual.traits.mp.current,
                    actual.db.buffs,
                    actual.db.skill_proficiency,
                ), before[entity.pk])
