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
    def test_different_damage_sources_share_reaction_with_equal_gains(self):
        """Scenario: Different damage sources share the reaction.

        WHEN a synthetic passive owner suffers direct spell, item and periodic
            damage of equal actual loss
        THEN each actual loss causes the configured gain exactly once, and all
            three gains are equal because the gain reads the loss rather than
            the source
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_pain_feedback_skill",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        reaction_rule = Rule(
            id="synth_feedback_hp_loss_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # 1. Spell source: direct dispatch at godhead tier — the source tier
        #    must not affect a loss-proportional gain (max_hp is 200).
        self.target.sexual.pleasure.base = 0
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=T_GODHEAD, hp_loss_amount=20
        )
        pleasure_levels = [self.target.sexual.pleasure.base]
        self.assertEqual(pleasure_levels[-1], 14)  # floor(140 x 20 / 200)

        # 2. Item source: an item HP step through the real item write path.
        step = ItemEffectStep(
            target=self.target,
            effect=GaugeAdjustEffect(stat=ItemStat.HP, amount=-20),
            amount=-20,
        )
        self.assertEqual(_apply_gauge_step(step), -20)
        pleasure_levels.append(self.target.sexual.pleasure.base)
        self.assertEqual(
            pleasure_levels[-1] - pleasure_levels[-2], 14
        )

        # 3. Periodic source: a damaging rate tick through the clock path.
        tick_debuff = self._register_synth_buff(
            BuffDefinition(
                key="synth_equal_tick_poison",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={"rate": {"target": "hp", "delta": -20}},
            )
        )
        apply_buff(self.target, tick_debuff.key, source_tier=T_APPRENTICE)
        tick_buffs(self.target, 10)
        pleasure_levels.append(self.target.sexual.pleasure.base)
        self.assertEqual(
            pleasure_levels[-1] - pleasure_levels[-2], 14
        )

        # Equal actual loss (20 each) prices identically across sources.
        deltas = [b - a for a, b in zip(pleasure_levels, pleasure_levels[1:])]
        self.assertEqual(len(set(deltas)), 1)

        # 4. Engine-level spell damage resolved through ActionResolver on an
        #    unprotected target: the combat dispatch site threads its own
        #    actual_loss rather than a guessed amount.
        self.target.sexual.pleasure.base = 0
        self.target.traits.hp.current = 200
        sage_spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_engine_sage_spell",
                element="fire",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 75},
                effects=("damage:fire:magic",),
            )
        )
        self._grant_skill(self.actor, sage_spell.key, SkillKind.ACTIVE)
        battlefield = Battlefield(
            {
                "party": frozenset({self.actor.key}),
                "foes": frozenset({self.target.key}),
            },
            {self.actor.key: self.actor, self.target.key: self.target},
        )
        field_ctx = BattlefieldActionContext(battlefield)
        req = ActionRequest(self.actor, sage_spell.key, [self.target], field_ctx)
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        observed_loss = 200 - self.target.traits.hp.current
        self.assertGreater(observed_loss, 0)
        self.assertEqual(
            self.target.sexual.pleasure.base,
            math.floor(140 * observed_loss / 200),
            "Engine spell damage must thread its actual loss into the reaction",
        )

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_larger_loss_is_worth_proportionally_more(self):
        """Scenario: A larger loss is worth proportionally more.

        WHEN a synthetic passive owner suffers one loss of a tenth of maximum
            HP and, separately, one loss of half of maximum HP
        THEN the second gain is five times the first
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_proportional_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)
        reaction_rule = Rule(
            id="synth_proportional_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        self.target.sexual.pleasure.base = 0
        # A tenth of max HP (20 of 200).
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=None, hp_loss_amount=20
        )
        tenth_gain = self.target.sexual.pleasure.base
        self.assertEqual(tenth_gain, 14)
        # Half of max HP (100 of 200).
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=None, hp_loss_amount=100
        )
        half_gain = self.target.sexual.pleasure.base - tenth_gain
        self.assertEqual(half_gain, 70)
        self.assertEqual(half_gain, 5 * tenth_gain)

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_full_journey_costs_half_of_maximum_hp(self):
        """Scenario: A full journey costs half of maximum HP.

        WHEN a synthetic passive owner at the post-climax baseline suffers
            cumulative losses totalling half of maximum HP
        THEN the accumulated gain reaches the threshold band that opens the
            climax gate
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_journey_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)
        reaction_rule = Rule(
            id="synth_journey_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # Post-climax baseline: pleasure 15, phase neutral 未達.
        self.target.sexual.pleasure.base = 15
        self.assertEqual(self.target.sexual.climax_phase.level, "未達")

        # Five losses of a tenth of max HP (20 of 200) total half of max HP:
        # 15 + 5 x floor(140 x 20 / 200) = 15 + 70 = 85, the 極限 band floor.
        for _ in range(5):
            dispatch_outcome_reaction(
                self.target, "hp_loss", source_tier=None, hp_loss_amount=20
            )
        self.assertEqual(self.target.sexual.pleasure.base, 85)
        self.assertEqual(self.target.sexual.climax_phase.level, "接近")

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_no_loss_negative_instance_uses_the_flat_fraction(self):
        """Scenario: A no-loss negative instance uses the flat fraction.

        WHEN a synthetic passive owner newly accepts a negative buff instance
            that inflicts no HP loss
        THEN the gain equals the authored flat fraction of maximum HP, and is
            smaller than the gain from a loss of a tenth of maximum HP
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_flat_fraction_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)

        rule_debuff = Rule(
            id="synth_flat_fraction_rule",
            when={"event": "negative_buff_added", "skill_qualified": feedback_passive.key},
            then={
                "pleasure_gain": {
                    "max_hp_coefficient": 140,
                    "flat_max_hp_fraction": 0.05,
                }
            },
        )
        rule_hp = Rule(
            id="synth_flat_fraction_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule_debuff, rule_hp],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        curse = self._register_synth_buff(
            BuffDefinition(
                key="synth_no_hp_loss_curse",
                duration=60,
                polarity="debuff",
                tick_interval=10,
                stacking="refresh",
                modifiers={},
            )
        )
        self.target.sexual.pleasure.base = 0
        apply_buff(self.target, curse.key, source_tier=T_SAGE)
        flat_gain = self.target.sexual.pleasure.base
        self.assertEqual(flat_gain, 7)  # floor(140 x 0.05)

        # A loss of a tenth of maximum HP (20 of 200) is worth more.
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=T_SAGE, hp_loss_amount=20
        )
        self.assertEqual(self.target.sexual.pleasure.base - flat_gain, 14)
        self.assertLess(flat_gain, 14)

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_unreadable_maximum_produces_no_gain(self):
        """Scenario: An unreadable maximum produces no gain.

        WHEN a synthetic passive owner whose maximum HP is unreadable or not
            positive suffers an actual loss
        THEN no gain is applied and no state write occurs
        """
        feedback_passive = self._register_synth_skill(
            _make_synth_skill(
                "synth_indeterminate_passive",
                kind=SkillKind.PASSIVE,
                target_spec=TargetSpec.NONE,
                category=SkillCategory.ENHANCEMENT,
            )
        )
        self._grant_skill(self.target, feedback_passive.key)
        reaction_rule = Rule(
            id="synth_indeterminate_hp_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        self.target.sexual.pleasure.base = 0

        # 1. A loss-fraction rule with no loss amount applies nothing.
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=None)
        self.assertEqual(self.target.sexual.pleasure.base, 0)

        # 2. A zero maximum HP applies nothing (and raises nothing).
        self.target.traits.hp.base = 0
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=None, hp_loss_amount=20
        )
        self.assertEqual(self.target.sexual.pleasure.base, 0)

        # 3. An unreadable maximum (no hp trait at all) applies nothing.
        self.target.traits.remove("hp")
        dispatch_outcome_reaction(
            self.target, "hp_loss", source_tier=None, hp_loss_amount=20
        )
        self.assertEqual(self.target.sexual.pleasure.base, 0)
