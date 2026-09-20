"""Slice of ``test_damage_state_feedback``: DamageStateFeedbackBehaviorTests."""
import math
import importlib
from typing import Any
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield, BattlefieldActionContext, _handle_damage
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.items import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemEffectStep,
    ItemStat,
    ItemTargetScope,
    ItemUseError,
    ItemUsePlan,
    _apply_gauge_step,
)
from world.rules.pleasure import apply_pleasure_gain
from world.rules.rulebook.schema import Rule
from world.rules.sexual_state import EXPOSURE_LEVELS
from world.rules.targeting import RoomActionContext
from world.skills.handler import ConferredSkillGrant
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_outcome_reaction,
    validate_state_reaction_rules,
)
from world.skills.effects import RuleTableEffect
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

from ._support import (
    T_APPRENTICE,
    _SKILL_MAP,
    _make_synth_skill,
)


class DamageStateFeedbackBehaviorTests(EvenniaTest):
    """Behavior tests for damage-state-feedback mechanics using synthetic fixtures."""
    def setUp(self):
        super().setUp()
        from typeclasses.rooms import Room
        self.room = create_object(Room, key="synth_room")
        self.actor = create_object(PlayerCharacter, key="synth_actor")
        self.target = create_object(PlayerCharacter, key="synth_target")
        self.actor.location = self.room
        self.target.location = self.room
        self.actor.race = "human"
        self.target.race = "human"
        self.actor.apply_race_baseline()
        self.target.apply_race_baseline()
        self.actor.traits.hp.base = 200
        self.actor.traits.hp.current = 200
        self.target.traits.hp.base = 200
        self.target.traits.hp.current = 200
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.target.traits.mp.base = 500
        self.target.traits.mp.current = 500

    def _register_synth_skill(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def _register_synth_buff(self, buff: BuffDefinition) -> BuffDefinition:
        patcher = patch.dict(BUFF_DEFINITIONS, {buff.key: buff}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return buff

    def _grant_skill(self, entity: Any, skill_key: str, kind: SkillKind = SkillKind.PASSIVE) -> None:
        skills = dict(entity.db.skills or {"active": [], "passive": []})
        skills["active"] = list(skills.get("active", []))
        skills["passive"] = list(skills.get("passive", []))
        bucket = "passive" if kind == SkillKind.PASSIVE else "active"
        if skill_key not in skills[bucket]:
            skills[bucket].append(skill_key)
        entity.db.skills = skills

    @covers_requirement(
        "damage-state-feedback::recovery-only-passive-adjustment-composes-once-and-is-snapshotted"
    )
    def test_recovery_only_passive_multiplier_equipment_independent_and_snapshotted(self):
        """Scenario: Equipment-independent recovery.

        WHEN a synthetic passive owner with no equipment applies a recovery profile at a nonzero state ordinal
        THEN ticks include the configured captured benefit even after source state changes
        """
        passive_skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_grace_passive_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                effects=("passive_buff:synth_grace_rule",),
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.actor, passive_skill.key)

        # Rule in combat_modifiers: recovery_arousal_scale = 0.1
        rule_grace = Rule(
            id="synth_grace_modifier_rule",
            when={"skill_owned": passive_skill.key},
            then={"recovery_arousal_scale": 0.1},
        )
        patcher_combat = patch(
            "world.rules.combat_modifiers._RULES",
            _RULES + [rule_grace],
        )
        patcher_combat.start()
        self.addCleanup(patcher_combat.stop)

        recovery_buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_sustained_grace_buff",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 20,
                            "exposure_percent_per_ordinal": 0.0,
                        }
                    }
                },
            )
        )

        recovery_spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_cast_recovery_spell",
                element="holy",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 20},
                effects=(f"buff_apply:{recovery_buff_def.key}",),
            )
        )
        self._grant_skill(self.actor, recovery_spell.key, SkillKind.ACTIVE)

        # Actor has NO equipment, but has arousal ordinal 3 (中等)
        self.actor.sexual.pleasure.base = 70
        self.assertEqual(self.actor.sexual.arousal.value, 3)
        self.target.traits.hp.current = 50

        # Cast recovery spell on target
        req = ActionRequest(self.actor, recovery_spell.key, [self.target], RoomActionContext(self.room))
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")

        # Verify snapshotted grace multiplier: 1 + 0.1 * 3 = 1.3
        buff_inst = self.target.buffs.all[recovery_buff_def.key]
        self.assertAlmostEqual(buff_inst.snapshot_grace_multiplier, 1.3, places=2)

        # Now caster's arousal drops to 0 (平靜)
        self.actor.sexual.pleasure.base = 0
        self.assertEqual(self.actor.sexual.arousal.value, 0)

        # Tick recovery: base 20 * 1.3 = 26 HP restored (proves snapshot stability!)
        hp_before = self.target.traits.hp.current
        tick_buffs(self.target, 10)
        hp_after = self.target.traits.hp.current
        self.assertEqual(
            hp_after - hp_before,
            26,
            "Recovery tick must use snapshotted 1.3 grace multiplier despite caster arousal dropping to 0",
        )

    @covers_requirement(
        "damage-state-feedback::recovery-only-passive-adjustment-composes-once-and-is-snapshotted"
    )
    def test_recovery_passive_multiplier_fractional_conferred_scaling(self):
        """Spec Requirement: Numeric conferred adjustments retain fractional scaling."""
        passive_skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_conferred_grace_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                effects=("passive_buff:synth_conferred_grace",),
                category=SkillCategory.ENHANCEMENT,
            )
        )
        # Actor does NOT own skill, but has conferred grant of scale 0.5
        self.actor.db.skill_grants = [
            ConferredSkillGrant("synth_source", passive_skill.key, 0.5)
        ]

        rule_grace = Rule(
            id="synth_conferred_grace_rule",
            when={"skill_owned": passive_skill.key},
            then={"recovery_arousal_scale": 0.1},
        )
        patcher_combat = patch(
            "world.rules.combat_modifiers._RULES",
            _RULES + [rule_grace],
        )
        patcher_combat.start()
        self.addCleanup(patcher_combat.stop)

        recovery_buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_fractional_grace_buff",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 50,
                            "exposure_percent_per_ordinal": 0.0,
                        }
                    }
                },
            )
        )

        recovery_spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_cast_fractional_spell",
                element="holy",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 20},
                effects=(f"buff_apply:{recovery_buff_def.key}",),
            )
        )
        self._grant_skill(self.actor, recovery_spell.key, SkillKind.ACTIVE)

        # Actor has arousal ordinal 4 (高度, ordinal 4)
        # Fractional scale 0.5 -> recovery_arousal_scale = 0.05
        # Grace multiplier = 1.0 + 0.05 * 4 = 1.2
        self.actor.sexual.pleasure.base = 85
        self.assertEqual(self.actor.sexual.arousal.value, 4)
        self.target.traits.hp.current = 10

        req = ActionRequest(self.actor, recovery_spell.key, [self.target], RoomActionContext(self.room))
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")

        buff_inst = self.target.buffs.all[recovery_buff_def.key]
        self.assertAlmostEqual(buff_inst.snapshot_grace_multiplier, 1.2, places=2)

        # Tick: floor(50 * 1.2) = 60 HP restored
        hp_before = self.target.traits.hp.current
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.current - hp_before, 60)

    @covers_requirement(
        "damage-state-feedback::recovery-only-passive-adjustment-composes-once-and-is-snapshotted"
    )
    def test_no_duplicate_sacramental_multiplier_and_clean_equipment_composition(self):
        """Scenario: No duplicate sacramental multiplier and clean equipment composition.

        WHEN the same owner uses a direct state-scaled heal and a periodic recovery profile
        THEN only the configured recovery profile receives the extra recovery-only modifier
        """
        passive_skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_no_dup_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                effects=("passive_buff:synth_no_dup_rule",),
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.actor, passive_skill.key)

        rule_grace = Rule(
            id="synth_no_dup_rule",
            when={"skill_owned": passive_skill.key},
            then={"recovery_arousal_scale": 0.1},
        )
        patcher_combat = patch(
            "world.rules.combat_modifiers._RULES",
            _RULES + [rule_grace],
        )
        patcher_combat.start()
        self.addCleanup(patcher_combat.stop)

        recovery_buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_comp_recovery_buff",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                modifiers={
                    "rate": {
                        "recovery": {
                            "target": "hp",
                            "base": 100,
                            "exposure_percent_per_ordinal": 0.0,
                        }
                    }
                },
            )
        )

        recovery_spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_comp_recovery_spell",
                element="holy",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 20},
                effects=(f"buff_apply:{recovery_buff_def.key}",),
            )
        )
        self._grant_skill(self.actor, recovery_spell.key, SkillKind.ACTIVE)

        direct_heal_spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_direct_heal_spell",
                element="holy",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 20},
                effects=("heal:single",),
            )
        )
        self._grant_skill(self.actor, direct_heal_spell.key, SkillKind.ACTIVE)

        # Actor has arousal ordinal 2 (輕度, ordinal 2 -> grace factor = 1.2)
        self.actor.sexual.pleasure.base = 40
        self.assertEqual(self.actor.sexual.arousal.value, 2)

        # Equipment heal_gain +15% mocked
        with patch(
            "world.rules.combat_modifiers.equipment_adjustments",
            return_value={"heal_gain": "+15%"},
        ):
            # 1. Direct heal: only receives heal_gain (+15%), NOT recovery grace factor!
            from world.rules.combat import _heal_magnitude
            mag = _heal_magnitude(self.actor, coefficient=1.0)
            # base = round(magic_power * 1.0) -> scaled by heal_gain +15% only!
            base_expected = int(round(self.actor.traits.magic_power.value * 1.0))
            expected_direct = math.floor(base_expected * 1.15)
            self.assertEqual(mag, expected_direct)

            # 2. Recovery profile: composes heal_gain (+15%) and grace factor (1.2) independently!
            req = ActionRequest(self.actor, recovery_spell.key, [self.target], RoomActionContext(self.room))
            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            buff_inst = self.target.buffs.all[recovery_buff_def.key]
            self.assertEqual(buff_inst.snapshot_heal_gain, 15.0)
            self.assertAlmostEqual(buff_inst.snapshot_grace_multiplier, 1.2, places=2)

            # Recovery tick amount = floor(100 * 1.0 * (1 + 0.15) * 1.2) = floor(100 * 1.15 * 1.2) = floor(138) = 138
            self.target.traits.hp.current = 10
            tick_buffs(self.target, 10)
            expected_recovery = math.floor(100 * (1.0 + 15.0 / 100.0) * 1.2)
            self.assertEqual(self.target.traits.hp.current - 10, expected_recovery)

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_second_synthetic_non_light_configuration_proves_generic_engine_reuse(self):
        """Spec Requirement: Verify a second synthetic non-light configuration uses the same generic mechanism."""
        blood_masochism = self._register_synth_skill(
            _make_synth_skill(
                "synth_blood_masochism_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, blood_masochism.key)

        # Non-light flat integer pleasure gain
        alt_rule = Rule(
            id="synth_blood_masochism_rule",
            when={"event": "hp_loss", "skill_qualified": blood_masochism.key},
            then={"pleasure_gain": 7},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [alt_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        pleasure_before = self.target.sexual.pleasure.base
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=T_APPRENTICE)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after - pleasure_before,
            7,
            "Second synthetic non-light configuration should gain exactly 7 pleasure",
        )
