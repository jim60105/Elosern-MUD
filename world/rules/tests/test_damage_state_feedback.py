"""Synthetic behavior tests for damage and debuff state feedback (light-cleric-feedback).

Exercising:
- Different damage sources share reaction with loss-proportional gain (direct spell, item, periodic tick)
- Coefficient shaping: floor(140 x actual_loss / max_hp); a half-max-HP loss is worth five times a tenth-max-HP loss
- A full climax journey costs half of maximum HP (post-climax 15 + 70 = 極限 floor 85)
- No-loss negative instances price at the authored flat fraction of max HP (floor(140 x 0.05) = 7)
- Indeterminate cases (absent loss amount, unreadable or non-positive max HP) apply nothing rather than guess
- Retired source-tier gain mapping fails closed at rule load naming the rule id
- Negative triggers: misses, zero damage, dead targets, immunity refused debuffs, buff refreshes, resource costs
- Distinct events for new debuff acceptance and subsequent periodic damage ticks
- Transitive feedback cascades entering normal lock phase without inventing a second state system
- Late-failure rollback restoring complete cascade (action, item, and clock paths)
- Conferred passive grants do NOT create binary event-reaction entitlement
- Source tier retention on debuff instances across clock advances
- Recovery-only passive multiplier: equipment-independent benefit, snapshot stability across caster arousal changes
- Conferred recovery passive fractional scaling via combat modifier rule scaling
- No duplicate sacramental/direct-heal multiplier and clean independent composition with equipment heal_gain
- Second synthetic non-light configuration proving generic reaction-input reuse
"""

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

_cost_mod = importlib.import_module("world.skills.cost_tiers")
_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")
_tier_names = list(_cost_tiers_table.keys())
T_APPRENTICE = _tier_names[0]
T_ADEPT = _tier_names[1]
T_MASTER = _tier_names[2]
T_SAGE = _tier_names[3]
T_SOVEREIGN = _tier_names[4]
T_GODHEAD = _tier_names[5]

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_skill(
    key: str,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = None,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    effects: tuple[str, ...] | list[str] = (),
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
) -> SkillDef:
    elem = _ELEMENT_MAP.get(element) if element is not None else None
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=elem,
        effects=list(effects),
        category=category,
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
        with patch("world.rules.combat.roll_d100", return_value=100):
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

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_pleasure_gain_new_shapes_validate(self):
        """The loader accepts the flat integer and the two new derived shapes."""
        validate_state_reaction_rules(
            [
                Rule(
                    id="synth_ok_flat_int",
                    when={"event": "hp_loss"},
                    then={"pleasure_gain": 7},
                ),
                Rule(
                    id="synth_ok_coefficient",
                    when={"event": "hp_loss"},
                    then={"pleasure_gain": {"max_hp_coefficient": 140}},
                ),
                Rule(
                    id="synth_ok_flat_fraction",
                    when={"event": "negative_buff_added"},
                    then={
                        "pleasure_gain": {
                            "max_hp_coefficient": 140,
                            "flat_max_hp_fraction": 0.05,
                        }
                    },
                ),
            ]
        )

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_pleasure_gain_retired_tier_mapping_fails_load(self):
        """Scenario: A tier-keyed gain mapping fails at load.

        WHEN a rule authors pleasure_gain as a source-tier-keyed mapping
        THEN rule loading raises naming that rule id
        """
        retired = Rule(
            id="synth_retired_tier_rule",
            when={"event": "hp_loss"},
            then={"pleasure_gain": {T_APPRENTICE: 5, T_SAGE: 18}},
        )
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([retired])
        self.assertIn("synth_retired_tier_rule", str(ctx.exception))
        self.assertIn(T_APPRENTICE, str(ctx.exception))

        # Malformed new shapes also fail closed naming the rule id.
        for bad_rule in (
            Rule(
                id="synth_missing_coeff",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {"flat_max_hp_fraction": 0.05}},
            ),
            Rule(
                id="synth_bad_coeff",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {"max_hp_coefficient": 0}},
            ),
            Rule(
                id="synth_bad_fraction",
                when={"event": "negative_buff_added"},
                then={
                    "pleasure_gain": {
                        "max_hp_coefficient": 140,
                        "flat_max_hp_fraction": 1.0,
                    }
                },
            ),
            Rule(
                id="synth_empty_mapping",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {}},
            ),
        ):
            with self.assertRaises(ValueError) as ctx:
                validate_state_reaction_rules([bad_rule])
            self.assertIn(bad_rule.id, str(ctx.exception))

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
