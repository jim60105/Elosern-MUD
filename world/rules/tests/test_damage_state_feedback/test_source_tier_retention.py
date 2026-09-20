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
    T_SAGE,
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
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_periodic_buff_retains_source_tier_across_clock_advance(self):
        """Spec Requirement: Periodic buff retains source tier across clock advances."""
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_clock_tier_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        reaction_rule = Rule(
            id="synth_clock_tier_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        debuff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_clock_poison",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10}},
            )
        )

        # Apply buff with tier 賢者
        apply_buff(self.target, debuff_def.key, source_tier=T_SAGE)
        self.assertEqual(self.target.buffs.all[debuff_def.key].source_tier, T_SAGE)

        # Advance clock by 10s -> fires tick 1 (10 damage -> floor(140 x 10 / 200) = 7)
        pleasure_before = self.target.sexual.pleasure.base
        WorldClock().advance(10, AdvanceSource.COMMAND, [self.target])
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after - pleasure_before,
            7,
            "Tick after clock advance prices its actual loss",
        )

        # Retained across second advance
        WorldClock().advance(10, AdvanceSource.COMMAND, [self.target])
        self.assertEqual(
            self.target.sexual.pleasure.base - pleasure_after,
            7,
            "Second tick after clock advance prices its actual loss",
        )
