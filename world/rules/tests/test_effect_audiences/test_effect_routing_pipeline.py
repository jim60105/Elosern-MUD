"""Slice of ``test_effect_audiences``: EffectRoutingPipelineTests.
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
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
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
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
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
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
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
            patch("world.rules.combat.damage.roll_d100") as mock_roll,
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
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
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
            patch.dict(
                "world.rules.action.contracts._EVENT_EFFECT_PLANNERS",
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
        with patch("world.rules.action.costs.grant_skill_practice_xp", return_value=True) as mock_grant:
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
        with patch("world.rules.action.costs.grant_skill_practice_xp", return_value=True) as mock_grant:
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
            patch("world.rules.combat.damage.roll_d100", return_value=60),
            patch("world.rules.combat.rounds.evaluate_combat_modifiers", return_value={}),
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        # Target took water damage and kept debuff
        damage_entry = [e for e in res.event_log.entries if e.kind == "damage"][0]
        self.assertEqual(damage_entry.target, "target")
        self.assertEqual(len(entity_active_buffs(self.target)), 1)
        # Companion was cleansed and took no damage
        self.assertEqual(len(entity_active_buffs(self.companion)), 0)
