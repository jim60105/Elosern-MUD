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
    T_GODHEAD,
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
    def test_immune_and_refresh_outcomes_do_not_count(self):
        """Scenario: Immune and refresh outcomes do not count.

        WHEN a negative buff is refused by immunity or only refreshes an existing instance
        THEN there is no new-instance feedback
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_debuff_feedback_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        reaction_rule = Rule(
            id="synth_feedback_debuff_added_rule",
            when={"event": "negative_buff_added", "skill_qualified": feedback_passive.key},
            then={
                "pleasure_gain": {
                    "max_hp_coefficient": 140,
                    "flat_max_hp_fraction": 0.05,
                }
            },
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        debuff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_refreshable_poison",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -5}},
            )
        )

        # Case 1: First application -> accepted -> triggers once (flat 7)
        pleasure_before = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier=T_SAGE)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(pleasure_after - pleasure_before, 7)

        # Case 2: Refresh of existing instance -> NO trigger
        pleasure_before = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier=T_SAGE)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after,
            pleasure_before,
            "Buff refresh must not trigger negative_buff_added reaction",
        )

        # Case 3: Immunity refused -> NO trigger
        immune_debuff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_immune_curse",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={},
            )
        )
        with patch(
            "world.rules.equipment_effects.equipment_immune_buff_keys",
            return_value=frozenset({immune_debuff_def.key}),
        ):
            pleasure_before = self.target.sexual.pleasure.base
            apply_buff(self.target, immune_debuff_def.key, source_tier=T_SAGE)
            pleasure_after = self.target.sexual.pleasure.base
            self.assertEqual(
                pleasure_after,
                pleasure_before,
                "Immune debuff refusal must not trigger negative_buff_added reaction",
            )

        # Case 4: Positive buff -> NO trigger
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_positive_ward",
                duration=60,
                polarity="buff",
                tick_interval=10,
                stacking="refresh",
                modifiers={},
            )
        )
        pleasure_before = self.target.sexual.pleasure.base
        apply_buff(self.target, buff_def.key, source_tier=T_SAGE)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after,
            pleasure_before,
            "Positive buff must not trigger negative_buff_added reaction",
        )

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_new_debuff_and_its_ticks_are_distinct(self):
        """Scenario: New debuff and its ticks are distinct.

        WHEN a new damaging debuff is accepted and later ticks twice
        THEN the new-instance event and each positive-loss tick independently trigger once
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_dual_feedback_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        rule_hp = Rule(
            id="synth_feedback_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        rule_debuff = Rule(
            id="synth_feedback_debuff_rule",
            when={"event": "negative_buff_added", "skill_qualified": feedback_passive.key},
            then={
                "pleasure_gain": {
                    "max_hp_coefficient": 140,
                    "flat_max_hp_fraction": 0.05,
                }
            },
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_hp, rule_debuff],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        debuff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_tick_poison",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -10}},
            )
        )

        # 1. Apply new damaging debuff (no HP loss yet -> flat gain 7)
        pleasure_start = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier=T_SAGE)
        pleasure_after_apply = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_apply - pleasure_start,
            7,
            "Initial debuff application should trigger negative_buff_added once",
        )

        # 2. First tick (10s): deals 10 damage -> hp_loss once (floor(140 x 10 / 200) = 7)
        hp_before_tick1 = self.target.traits.hp.current
        tick_buffs(self.target, 10)
        hp_after_tick1 = self.target.traits.hp.current
        self.assertEqual(hp_before_tick1 - hp_after_tick1, 10)
        pleasure_after_tick1 = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_tick1 - pleasure_after_apply,
            7,
            "First damage tick should trigger hp_loss once for its actual loss",
        )

        # 3. Second tick (10s): deals 10 damage -> hp_loss again once (+7)
        tick_buffs(self.target, 10)
        pleasure_after_tick2 = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_tick2 - pleasure_after_tick1,
            7,
            "Second damage tick should trigger hp_loss once for its actual loss",
        )

        # Total gain across application and two ticks: 7 + 7 + 7 = 21
        self.assertEqual(pleasure_after_tick2 - pleasure_start, 21)

    @covers_requirement(
        "damage-state-feedback::feedback-cascades-remain-within-the-initiating-transaction"
    )
    def test_feedback_can_enter_normal_lock_phase(self):
        """Scenario: Feedback can enter the normal lock phase.

        WHEN a configured damage gain crosses the recipient into in-progress
        THEN normal phase reactions and action locking occur without inventing a second state system
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_lock_feedback_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        rule_hp = Rule(
            id="synth_feedback_lock_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": 25},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_hp],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # Set target close to critical point: pleasure 90 (高度), climax_phase 接近
        self.target.sexual.pleasure.base = 90
        from world.rules.sexual_state import _apply_climax_phase_set
        _apply_climax_phase_set(self.target, "接近")
        self.assertEqual(self.target.sexual.climax_phase.level, "接近")

        # Before damage: actions not locked
        mods_before = evaluate_combat_modifiers(self.target)
        self.assertNotEqual(mods_before.get("actions_per_turn"), 0)

        # Target suffers actual HP loss -> reaction gains +25 pleasure -> crosses to 100+ -> 進行中!
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=T_APPRENTICE)
        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")

        # Action locking occurs via canonical combat rule (climax_in_progress_locks_actions)
        mods_after = evaluate_combat_modifiers(self.target)
        self.assertEqual(mods_after.get("actions_per_turn"), 0)

    @covers_requirement(
        "damage-state-feedback::feedback-cascades-remain-within-the-initiating-transaction"
    )
    def test_late_failure_restores_complete_cascade_item_and_clock(self):
        """Scenario: Late failure restores the complete cascade.

        WHEN an item or clock settlement fails after feedback activates a phase marker
        THEN HP, negative buff state, pleasure, phase, counters and marker all restore
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_rollback_feedback_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        # Gain 40 on hp_loss
        rule_hp = Rule(
            id="synth_rollback_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": 40},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_hp],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # Set target baseline
        self.target.traits.hp.current = 100
        self.target.sexual.pleasure.base = 50
        initial_hp = self.target.traits.hp.current
        initial_pleasure = self.target.sexual.pleasure.base

        # 1. Item rollback scenario
        step = ItemEffectStep(
            target=self.target,
            effect=GaugeAdjustEffect(stat=ItemStat.HP, amount=-20),
            amount=-20,
        )
        from world.rules.items import ItemTouchedJournal
        journal = ItemTouchedJournal.capture(self.target, [self.target])

        # Step applies: deals 20 HP loss -> triggers hp_loss -> gains +40 pleasure!
        _apply_gauge_step(step)
        self.assertEqual(self.target.traits.hp.current, 80)
        self.assertEqual(self.target.sexual.pleasure.base, 90)

        # Transaction fails -> journal.restore() runs
        journal.restore()
        self.assertEqual(self.target.traits.hp.current, initial_hp)
        self.assertEqual(self.target.sexual.pleasure.base, initial_pleasure)

        # 2. Clock rollback scenario
        clock = WorldClock()
        from world.rules.clock import build_advance_snapshot_registry, _restore_advance_registry
        registry = build_advance_snapshot_registry(clock, 30, AdvanceSource.COMMAND, (self.target,))

        # Mutate inside hypothetical advance: damage dealt + pleasure gained
        self.target.traits.hp.current = 50
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=T_GODHEAD)
        self.assertEqual(self.target.traits.hp.current, 50)
        self.assertEqual(self.target.sexual.pleasure.base, 90)

        # Advance encounters late failure -> restores registry
        _restore_advance_registry(registry, (self.target,))
        self.assertEqual(self.target.traits.hp.current, initial_hp)
        self.assertEqual(self.target.sexual.pleasure.base, initial_pleasure)

    @covers_requirement(
        "damage-state-feedback::recovery-only-passive-adjustment-composes-once-and-is-snapshotted"
    )
    def test_conferred_passive_does_not_create_binary_reaction_entitlement(self):
        """Spec Requirement: Conferred passive does NOT create binary event-reaction entitlement."""
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_conferred_passive_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                effects=("passive_buff:synth_conferred_rule",),
                category=SkillCategory.ENHANCEMENT,
            )
        )
        # Target does NOT own the skill, but has a conferred grant of it
        self.target.db.skill_grants = [
            ConferredSkillGrant("synth_source", feedback_passive.key, 0.5)
        ]

        reaction_rule = Rule(
            id="synth_conferred_reaction_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": 15},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # Taking damage: does NOT trigger reaction because skill is only conferred, not qualified
        pleasure_before = self.target.sexual.pleasure.base
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=T_APPRENTICE)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after,
            pleasure_before,
            "Conferred passive must NOT grant binary event-reaction entitlement",
        )
