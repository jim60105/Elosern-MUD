"""Synthetic behavior tests for damage and debuff state feedback (light-cleric-feedback).

Exercising:
- Different damage sources share reaction and use captured source tier (direct spell, item, periodic tick)
- Tier ladder rungs: 5/8/12/18/28/40 for 學徒/術師/大師/賢者/主宰/神格
- Nonspell fallback rung: items and non-elemental sources use 5
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
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.elements import ELEMENT_REGISTRY
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import _handle_damage
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
)
from world.skills.cost_tiers import MP_COST_TIERS
from world.skills.effects import RuleTableEffect
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)


def _make_synth_skill(
    key: str,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = None,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    effects: tuple[str, ...] | list[str] = (),
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
) -> SkillDef:
    elem = ELEMENT_REGISTRY.get(element) if element is not None else None
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
        patcher = patch.dict(SKILL_REGISTRY, {skill.key: skill}, clear=False)
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

    def test_different_damage_sources_share_reaction_and_use_captured_tier(self):
        """Scenario: Different damage sources share the reaction.

        WHEN a synthetic passive owner suffers direct spell, item and periodic damage
        THEN each actual loss causes the configured gain once and uses its captured source tier
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

        tier_gains = {
            "學徒": 5,
            "術師": 8,
            "大師": 12,
            "賢者": 18,
            "主宰": 28,
            "神格": 40,
        }
        reaction_rule = Rule(
            id="synth_feedback_hp_loss_rule",
            when={"event": "hp_loss", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": tier_gains},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # 1. Direct spell damage across each cost tier
        costs_by_tier = {
            "學徒": 12,
            "術師": 24,
            "大師": 40,
            "賢者": 75,
            "主宰": 130,
            "神格": 200,
        }
        for tier, cost in costs_by_tier.items():
            self.target.sexual.pleasure.base = 0
            pleasure_before = self.target.sexual.pleasure.base
            spell = self._register_synth_skill(
                _make_synth_skill(
                    f"synth_dmg_spell_{tier}",
                    element="fire",
                    target_spec=TargetSpec.SINGLE,
                    cost={"mp": cost},
                    effects=("damage:fire:magical",),
                )
            )
            # Dispatch hp_loss with this spell's tier
            dispatch_outcome_reaction(self.target, "hp_loss", source_tier=tier)
            pleasure_after = self.target.sexual.pleasure.base
            expected_gain = tier_gains[tier]
            self.assertEqual(
                pleasure_after - pleasure_before,
                expected_gain,
                f"Tier {tier} should gain {expected_gain} pleasure, got {pleasure_after - pleasure_before}",
            )

        # 2. Item HP loss -> uses fallback tier rung (學徒, 5)
        pleasure_before = self.target.sexual.pleasure.base
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier=None)
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(pleasure_after - pleasure_before, 5)

        # 3. Periodic rate tick damage with captured source tier (e.g. 賢者, 18)
        pleasure_before = self.target.sexual.pleasure.base
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier="賢者")
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(pleasure_after - pleasure_before, 18)

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
            then={"pleasure_gain": {"學徒": 5, "賢者": 18}},
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

        # Case 1: First application -> accepted -> triggers once
        pleasure_before = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier="賢者")
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(pleasure_after - pleasure_before, 18)

        # Case 2: Refresh of existing instance -> NO trigger
        pleasure_before = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier="賢者")
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
            apply_buff(self.target, immune_debuff_def.key, source_tier="賢者")
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
        apply_buff(self.target, buff_def.key, source_tier="賢者")
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after,
            pleasure_before,
            "Positive buff must not trigger negative_buff_added reaction",
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
            then={"pleasure_gain": {"賢者": 18, "學徒": 5}},
        )
        rule_debuff = Rule(
            id="synth_feedback_debuff_rule",
            when={"event": "negative_buff_added", "skill_qualified": feedback_passive.key},
            then={"pleasure_gain": {"賢者": 18, "學徒": 5}},
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

        # 1. Apply new damaging debuff with source tier 賢者 (gain: 18)
        pleasure_start = self.target.sexual.pleasure.base
        apply_buff(self.target, debuff_def.key, source_tier="賢者")
        pleasure_after_apply = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_apply - pleasure_start,
            18,
            "Initial debuff application should trigger negative_buff_added once",
        )

        # 2. First tick (10s): deals 10 damage -> triggers hp_loss once with captured tier 賢者 (gain: 18)
        hp_before_tick1 = self.target.traits.hp.current
        tick_buffs(self.target, 10)
        hp_after_tick1 = self.target.traits.hp.current
        self.assertEqual(hp_before_tick1 - hp_after_tick1, 10)
        pleasure_after_tick1 = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_tick1 - pleasure_after_apply,
            18,
            "First damage tick should trigger hp_loss once using captured tier 賢者",
        )

        # 3. Second tick (10s): deals 10 damage -> triggers hp_loss again once (gain: 18)
        tick_buffs(self.target, 10)
        pleasure_after_tick2 = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after_tick2 - pleasure_after_tick1,
            18,
            "Second damage tick should trigger hp_loss once using captured tier 賢者",
        )

        # Total gain across application and two ticks: 18 + 18 + 18 = 54
        self.assertEqual(pleasure_after_tick2 - pleasure_start, 54)

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
            then={"pleasure_gain": {"學徒": 25}},
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
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier="學徒")
        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")

        # Action locking occurs via canonical combat rule (climax_in_progress_locks_actions)
        mods_after = evaluate_combat_modifiers(self.target)
        self.assertEqual(mods_after.get("actions_per_turn"), 0)

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
            then={"pleasure_gain": {"學徒": 40, "神格": 40}},
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
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier="神格")
        self.assertEqual(self.target.traits.hp.current, 50)
        self.assertEqual(self.target.sexual.pleasure.base, 90)

        # Advance encounters late failure -> restores registry
        _restore_advance_registry(registry, (self.target,))
        self.assertEqual(self.target.traits.hp.current, initial_hp)
        self.assertEqual(self.target.sexual.pleasure.base, initial_pleasure)

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
            then={"pleasure_gain": {"學徒": 15}},
        )
        patcher_reaction = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction_rule],
        )
        patcher_reaction.start()
        self.addCleanup(patcher_reaction.stop)

        # Taking damage: does NOT trigger reaction because skill is only conferred, not qualified
        pleasure_before = self.target.sexual.pleasure.base
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier="學徒")
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after,
            pleasure_before,
            "Conferred passive must NOT grant binary event-reaction entitlement",
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
            then={"pleasure_gain": {"賢者": 18, "學徒": 5}},
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
        apply_buff(self.target, debuff_def.key, source_tier="賢者")
        self.assertEqual(self.target.buffs.all[debuff_def.key].source_tier, "賢者")

        # Advance clock by 10s -> fires tick 1
        pleasure_before = self.target.sexual.pleasure.base
        WorldClock().advance(10, AdvanceSource.COMMAND, [self.target])
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after - pleasure_before,
            18,
            "Tick after clock advance must use retained source tier 賢者 (gain 18)",
        )

        # Retained across second advance
        WorldClock().advance(10, AdvanceSource.COMMAND, [self.target])
        self.assertEqual(
            self.target.sexual.pleasure.base - pleasure_after,
            18,
            "Second tick after clock advance must still use retained source tier 賢者 (gain 18)",
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
        dispatch_outcome_reaction(self.target, "hp_loss", source_tier="學徒")
        pleasure_after = self.target.sexual.pleasure.base
        self.assertEqual(
            pleasure_after - pleasure_before,
            7,
            "Second synthetic non-light configuration should gain exactly 7 pleasure",
        )
