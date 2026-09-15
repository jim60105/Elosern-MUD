"""Synthetic behavior tests for canonical MP flow and depletion reactions.

Exercises:
- Writer clamping and signed actual delta
- Exactly-once mp_zero outcome reaction on positive-to-zero crossing via decrease
- No-dispatch on already-zero, increase, positive-residual, or clamped no-op
- Source-skill and source-tier attribution with apprentice rung fallback
- remove_mp drain-all entry behavior
- Buff engine rate {target: mp} tick routing and grant-time attribution persistence
- HP rate tick regression safety (TickRecord collection and hp_loss dispatch)
- Step-6 cast-cost deduction routing and self-cast suffocation behavior
- Rule-layer event_source_skill filtering (qualified vs unqualified vs missing source)
- Alternate synthetic rule proving generic non-water reuse without branching
- Debuff immunity blocking of mp-target DoT application
- Transactional rollback restoring MP and reaction-applied markers
"""

from copy import deepcopy
import importlib
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _handle_buff_apply,
    _stored_trait_value,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.mp_flow import apply_mp_change, remove_mp
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_outcome_reaction,
)
from world.rules.targeting import RoomActionContext
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")
_cost_mod = importlib.import_module("world.skills.cost_tiers")
_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")
_tier_names = list(_cost_tiers_table.keys())
T_APPRENTICE = _tier_names[0]
T_ADEPT = _tier_names[1]
T_MASTER = _tier_names[2]
T_SAGE = _tier_names[3]
T_SOVEREIGN = _tier_names[4]
T_GODHEAD = _tier_names[5]


def _make_synth_skill(
    key: str,
    *,
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


class MpFlowTestBase(EvenniaTest):
    """Base setup providing synthetic entities and registration helpers."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_mp_room")
        self.actor = create_object(PlayerCharacter, key="synth_mp_actor")
        self.target = create_object(PlayerCharacter, key="synth_mp_target")
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
        self.actor.traits.mp.base = 100
        self.actor.traits.mp.current = 100
        self.target.traits.mp.base = 100
        self.target.traits.mp.current = 100

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

    def _add_synth_rule(self, rule: Rule) -> None:
        patcher = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [rule],
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class WriterClampingAndDeltaTests(MpFlowTestBase):
    """Scenario: Every authored MP decrease flows through one canonical writer returning the actual change."""

    def test_apply_mp_change_decreases_and_returns_signed_actual_delta(self):
        self.target.traits.mp.current = 50
        delta = apply_mp_change(self.target, -20)
        self.assertEqual(delta, -20)
        self.assertEqual(int(self.target.traits.mp.current), 30)

    def test_apply_mp_change_clamps_at_zero_and_reports_available_amount(self):
        self.target.traits.mp.current = 15
        delta = apply_mp_change(self.target, -50)
        self.assertEqual(delta, -15)
        self.assertEqual(int(self.target.traits.mp.current), 0)

    def test_apply_mp_change_clamps_at_maximum_and_returns_actual_gain(self):
        self.target.traits.mp.current = 80
        delta = apply_mp_change(self.target, 50)
        self.assertEqual(delta, 20)
        self.assertEqual(int(self.target.traits.mp.current), 100)

    def test_apply_mp_change_clamped_noop_returns_zero(self):
        self.target.traits.mp.current = 0
        delta = apply_mp_change(self.target, -10)
        self.assertEqual(delta, 0)
        self.assertEqual(int(self.target.traits.mp.current), 0)

        self.target.traits.mp.current = 100
        delta = apply_mp_change(self.target, 10)
        self.assertEqual(delta, 0)
        self.assertEqual(int(self.target.traits.mp.current), 100)

    def test_apply_mp_change_invalid_delta_type_raises(self):
        for invalid in (5.5, -3.2, True, False, "10"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    apply_mp_change(self.target, invalid)

    def test_apply_mp_change_missing_traits_fails_closed(self):
        class BareObject:
            pass

        with self.assertRaises(AttributeError):
            apply_mp_change(BareObject(), -10)

    def test_item_mp_step_routes_through_canonical_writer(self):
        from world.rules.items import GaugeAdjustEffect, ItemEffectStep, ItemStat, _apply_gauge_step

        self.target.traits.mp.current = 20
        step = ItemEffectStep(
            target=self.target,
            effect=GaugeAdjustEffect(stat=ItemStat.MP, amount=-20),
            amount=-20,
        )
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            applied = _apply_gauge_step(step)
            self.assertEqual(applied, -20)
            self.assertEqual(int(self.target.traits.mp.current), 0)
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_APPRENTICE,
                source_skill=None,
            )


class ExactlyOnceCrossingTests(MpFlowTestBase):
    """Scenario: MP reaching zero via a decrease dispatches one attributed outcome event exactly once."""

    def test_mp_zero_dispatches_once_on_crossing_from_positive_to_zero(self):
        self.target.traits.mp.current = 30
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = apply_mp_change(self.target, -30, source_skill="synth_skill")
            self.assertEqual(delta, -30)
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_APPRENTICE,
                source_skill="synth_skill",
            )

    def test_mp_zero_does_not_dispatch_when_already_zero(self):
        self.target.traits.mp.current = 0
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = apply_mp_change(self.target, -10, source_skill="synth_skill")
            self.assertEqual(delta, 0)
            mock_dispatch.assert_not_called()

    def test_mp_zero_does_not_dispatch_on_increase(self):
        self.target.traits.mp.current = 0
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = apply_mp_change(self.target, 20, source_skill="synth_skill")
            self.assertEqual(delta, 20)
            mock_dispatch.assert_not_called()

    def test_mp_zero_does_not_dispatch_when_delta_leaves_mp_positive(self):
        self.target.traits.mp.current = 50
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = apply_mp_change(self.target, -20, source_skill="synth_skill")
            self.assertEqual(delta, -20)
            mock_dispatch.assert_not_called()

    def test_mp_zero_dispatches_again_on_renewed_crossing(self):
        self.target.traits.mp.current = 30
        dispatches = []
        with patch(
            "world.rules.state_reactions.dispatch_outcome_reaction",
            side_effect=lambda *args, **kwargs: dispatches.append((args, kwargs)),
        ):
            # First crossing
            apply_mp_change(self.target, -30)
            self.assertEqual(len(dispatches), 1)

            # Further decrease while at 0 does not dispatch
            apply_mp_change(self.target, -10)
            self.assertEqual(len(dispatches), 1)

            # Healed back up
            apply_mp_change(self.target, 25)
            self.assertEqual(len(dispatches), 1)

            # Drained to zero again -> second crossing dispatches
            apply_mp_change(self.target, -25)
            self.assertEqual(len(dispatches), 2)


class SourceAttributionTests(MpFlowTestBase):
    """Scenario: Tier fallback matches the hp-loss convention and preserves attribution."""

    def test_mp_zero_event_carries_authored_source_skill_and_tier(self):
        self.target.traits.mp.current = 40
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            apply_mp_change(
                self.target,
                -40,
                source_skill="synth_custom_drain",
                source_tier=T_SAGE,
            )
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_SAGE,
                source_skill="synth_custom_drain",
            )

    def test_mp_zero_event_unattributed_falls_back_to_apprentice_rung(self):
        self.target.traits.mp.current = 20
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            apply_mp_change(self.target, -20)
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_APPRENTICE,
                source_skill=None,
            )

    def test_mp_zero_event_resolves_tier_from_elemental_spell(self):
        spell = self._register_synth_skill(
            _make_synth_skill(
                "synth_water_drain",
                element="water",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 78},
            )
        )
        self.target.traits.mp.current = 30
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            apply_mp_change(self.target, -30, source_skill=spell.key)
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_SAGE,
                source_skill=spell.key,
            )


class RemoveMpTests(MpFlowTestBase):
    """Scenario: remove_mp is the drain-all writer entry."""

    def test_remove_mp_drains_all_and_dispatches_crossing(self):
        self.target.traits.mp.current = 45
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = remove_mp(
                self.target,
                source_skill="synth_drain_all",
                source_tier=T_SOVEREIGN,
            )
            self.assertEqual(delta, -45)
            self.assertEqual(int(self.target.traits.mp.current), 0)
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_SOVEREIGN,
                source_skill="synth_drain_all",
            )

    def test_remove_mp_when_already_zero_returns_zero_and_no_dispatch(self):
        self.target.traits.mp.current = 0
        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            delta = remove_mp(self.target, source_skill="synth_drain_all")
            self.assertEqual(delta, 0)
            mock_dispatch.assert_not_called()


class BuffEngineMpRoutingTests(MpFlowTestBase):
    """Scenario: Buff engine mp-target ticks route through the writer with persisted attribution."""

    def test_buff_rate_mp_tick_routes_through_writer_and_dispatches_on_crossing(self):
        # Register synthetic mp-rate DoT buff
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_mp_dot",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="debuff",
                modifiers={"rate": {"target": "mp", "delta": -10}},
            )
        )
        self.target.traits.mp.current = 20

        # Apply buff with attribution
        apply_buff(
            self.target,
            buff_def.key,
            source_skill="synth_dot_caster_skill",
            source_tier=T_MASTER,
            source_pk=int(self.actor.pk),
        )

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            # Tick 1: 20 -> 10, no crossing
            records = tick_buffs(self.target, 10)
            self.assertEqual(int(self.target.traits.mp.current), 10)
            self.assertEqual(records, ())
            mock_dispatch.assert_not_called()

            # Tick 2: 10 -> 0, crosses to zero!
            records = tick_buffs(self.target, 10)
            self.assertEqual(int(self.target.traits.mp.current), 0)
            self.assertEqual(records, ())
            mock_dispatch.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=T_MASTER,
                source_skill="synth_dot_caster_skill",
            )

    def test_hp_rate_tick_dispatches_hp_loss_and_never_mp_zero(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_hp_dot",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="debuff",
                modifiers={"rate": {"target": "hp", "delta": -15}},
            )
        )
        self.target.traits.hp.current = 100
        apply_buff(self.target, buff_def.key, source_tier=T_ADEPT)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            records = tick_buffs(self.target, 10)
            self.assertEqual(int(self.target.traits.hp.current), 85)
            self.assertEqual(len(records), 1)
            mock_dispatch.assert_called_once_with(
                self.target,
                "hp_loss",
                source_tier=T_ADEPT,
            )

    def test_buff_rate_positive_mp_tick_does_not_dispatch(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_mp_regen",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="buff",
                modifiers={"rate": {"target": "mp", "delta": 10}},
            )
        )
        self.target.traits.mp.current = 0
        apply_buff(self.target, buff_def.key)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            tick_buffs(self.target, 10)
            self.assertEqual(int(self.target.traits.mp.current), 10)
            mock_dispatch.assert_not_called()

    def test_buff_cache_persists_grant_time_source_skill_and_source_pk(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_mp_dot_persisted",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="debuff",
                modifiers={"rate": {"target": "mp", "delta": -5}},
            )
        )
        skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_dot_granting_skill",
                element="water",
                cost={"mp": 24},
            )
        )
        from world.skills.effects import EffectPolicy, ResolvedEffect

        resolved = ResolvedEffect(
            policy=EffectPolicy(magnitude=None),
            source_skill=skill,
        )
        context = {"resolved_effect": resolved}
        effects = _handle_buff_apply(
            self.actor,
            [self.target],
            f"buff_apply:{buff_def.key}",
            context,
            1.0,
        )
        for eff in effects:
            eff.apply()

        buff_instance = self.target.buffs.all[buff_def.key]
        self.assertEqual(getattr(buff_instance, "source_pk", None), int(self.actor.pk))
        self.assertEqual(getattr(buff_instance, "source_skill", None), skill.key)

    def test_reapplication_replaces_source_skill_and_refresh_retains(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_mp_dot_reapply",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="debuff",
                modifiers={"rate": {"target": "mp", "delta": -5}},
            )
        )
        skill1 = self._register_synth_skill(_make_synth_skill("synth_skill_1", element="water", cost={"mp": 24}))
        skill2 = self._register_synth_skill(_make_synth_skill("synth_skill_2", element="water", cost={"mp": 24}))
        from world.skills.effects import EffectPolicy, ResolvedEffect

        # Caster 1 applies
        effects = _handle_buff_apply(
            self.actor,
            [self.target],
            f"buff_apply:{buff_def.key}",
            {"resolved_effect": ResolvedEffect(policy=EffectPolicy(magnitude=None), source_skill=skill1)},
            1.0,
        )
        for eff in effects:
            eff.apply()
        self.assertEqual(self.target.buffs.all[buff_def.key].source_skill, skill1.key)

        # Caster 2 reapplies before expiry
        other = create_object(PlayerCharacter, key="synth_other_caster")
        other.race = "human"
        other.apply_race_baseline()
        effects2 = _handle_buff_apply(
            other,
            [self.target],
            f"buff_apply:{buff_def.key}",
            {"resolved_effect": ResolvedEffect(policy=EffectPolicy(magnitude=None), source_skill=skill2)},
            1.0,
        )
        for eff in effects2:
            eff.apply()
        self.assertEqual(self.target.buffs.all[buff_def.key].source_skill, skill2.key)
        self.assertEqual(self.target.buffs.all[buff_def.key].source_pk, int(other.pk))

        # Direct refresh without source retains prior attribution
        apply_buff(self.target, buff_def.key)
        self.assertEqual(self.target.buffs.all[buff_def.key].source_skill, skill2.key)
        self.assertEqual(self.target.buffs.all[buff_def.key].source_pk, int(other.pk))

    def test_load_buff_definitions_rejects_non_integer_mp_rate_delta(self):
        from pathlib import Path
        import tempfile
        from world.rules.buffs import load_buff_definitions

        content = (
            "- key: invalid_mp_float_buff\n"
            "  duration: 60\n"
            "  tick_interval: 10\n"
            "  stacking: refresh\n"
            "  polarity: debuff\n"
            "  modifiers:\n"
            "    rate: {target: mp, delta: -5.5}\n"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)
        try:
            with self.assertRaises(ValueError) as ctx:
                load_buff_definitions(temp_path)
            self.assertIn("mp rate delta must be an integer", str(ctx.exception))
        finally:
            temp_path.unlink(missing_ok=True)


class CastCostDeductionTests(MpFlowTestBase):
    """Scenario: Cast-cost payment is a routed write on the staged deduction."""

    def test_cast_cost_payment_to_zero_dispatches_attributed_mp_zero(self):
        skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_cost_spell",
                element="water",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 50},
                effects=("buff_apply:focus",),
            )
        )
        self.actor.traits.mp.current = 50
        skills = dict(self.actor.db.skills or {})
        skills["active"] = [skill.key]
        self.actor.db.skills = skills

        context = RoomActionContext(self.room)
        request = ActionRequest(self.actor, skill.key, [self.target], context)

        with (
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch,
        ):
            result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "success")
            self.assertEqual(int(self.actor.traits.mp.current), 0)
            mock_dispatch.assert_called_once_with(
                self.actor,
                "mp_zero",
                source_tier=T_MASTER,
                source_skill=skill.key,
            )

    def test_cast_cost_rejection_mutates_no_mp_and_dispatches_no_event(self):
        skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_cost_spell_fail",
                element="water",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 60},
                effects=("buff_apply:focus",),
            )
        )
        self.actor.traits.mp.current = 50
        skills = dict(self.actor.db.skills or {})
        skills["active"] = [skill.key]
        self.actor.db.skills = skills

        context = RoomActionContext(self.room)
        request = ActionRequest(self.actor, skill.key, [self.target], context)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_dispatch:
            result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "rejected")
            self.assertIs(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
            self.assertEqual(int(self.actor.traits.mp.current), 50)
            mock_dispatch.assert_not_called()

    def test_self_cast_cost_payment_to_zero_suffocates_if_qualified(self):
        """Accepted global-fact given: payer and drain victim are not distinguished by rule layer."""
        skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_self_drown",
                element="water",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 30},
                effects=("buff_apply:focus",),
            )
        )
        # Reaction rule qualifying this skill
        rule = Rule(
            id="synth_self_drown_suffocation",
            when={"event": "mp_zero", "event_source_skill": skill.key},
            then={"apply_buff": "suffocated"},
        )
        self._add_synth_rule(rule)

        self.actor.traits.mp.current = 30
        skills = dict(self.actor.db.skills or {})
        skills["active"] = [skill.key]
        self.actor.db.skills = skills

        context = RoomActionContext(self.room)
        request = ActionRequest(self.actor, skill.key, [self.target], context)

        with patch("world.rules.combat.roll_d100", return_value=50):
            result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "success")
            self.assertEqual(int(self.actor.traits.mp.current), 0)
            self.assertIn("suffocated", entity_active_buffs(self.actor))
            self.assertEqual(evaluate_combat_modifiers(self.actor).get("actions_per_turn"), 0)


class RuleLayerSourceFilteringTests(MpFlowTestBase):
    """Scenario: Depletion rules filter the event's source at the rule layer, never by suppressing dispatch."""

    def test_rule_layer_source_filtering_qualified_vs_unqualified(self):
        drain_skill = self._register_synth_skill(
            _make_synth_skill("synth_qualifying_drain", element="water", cost={"mp": 24})
        )
        other_skill = self._register_synth_skill(
            _make_synth_skill("synth_other_drain", element="water", cost={"mp": 24})
        )
        rule = Rule(
            id="synth_qualified_suffocation",
            when={"event": "mp_zero", "event_source_skill": drain_skill.key},
            then={"apply_buff": "suffocated"},
        )
        self._add_synth_rule(rule)

        # 1. Unqualified skill drains to zero: event fires, but rule does NOT match
        self.target.traits.mp.current = 20
        apply_mp_change(self.target, -20, source_skill=other_skill.key)
        self.assertEqual(int(self.target.traits.mp.current), 0)
        self.assertNotIn("suffocated", entity_active_buffs(self.target))

        # 2. Unattributed drain to zero: event fires, rule does NOT match
        self.target.traits.mp.current = 20
        apply_mp_change(self.target, -20)
        self.assertEqual(int(self.target.traits.mp.current), 0)
        self.assertNotIn("suffocated", entity_active_buffs(self.target))

        # 3. Qualified skill drains to zero: event fires AND rule matches -> suffocated applied
        self.target.traits.mp.current = 20
        apply_mp_change(self.target, -20, source_skill=drain_skill.key)
        self.assertEqual(int(self.target.traits.mp.current), 0)
        self.assertIn("suffocated", entity_active_buffs(self.target))

    def test_event_source_skill_missing_source_fails_closed(self):
        drain_skill = self._register_synth_skill(
            _make_synth_skill("synth_qualifying_drain_2", element="water", cost={"mp": 24})
        )
        rule = Rule(
            id="synth_qualified_rule_2",
            when={"event": "mp_zero", "event_source_skill": drain_skill.key},
            then={"apply_buff": "suffocated"},
        )
        self._add_synth_rule(rule)

        self.target.traits.mp.current = 10
        apply_mp_change(self.target, -10, source_skill=None)
        self.assertNotIn("suffocated", entity_active_buffs(self.target))

    def test_alternate_synthetic_rule_reuses_event_source_skill(self):
        """Demonstrates alternate non-water source qualifications reuse the same key with no branching."""
        fire_skill = self._register_synth_skill(
            _make_synth_skill("synth_fire_burnout", element="fire", cost={"mp": 24})
        )
        rule = Rule(
            id="synth_fire_exhaustion",
            when={"event": "mp_zero", "event_source_skill": fire_skill.key},
            then={"apply_buff": "fear"},
        )
        self._add_synth_rule(rule)

        self.target.traits.mp.current = 10
        apply_mp_change(self.target, -10, source_skill=fire_skill.key)
        self.assertEqual(int(self.target.traits.mp.current), 0)
        self.assertIn("fear", entity_active_buffs(self.target))


class EquipmentImmunityTests(MpFlowTestBase):
    """Scenario: Immune targets never accumulate the drain."""

    def test_equipment_immunity_blocks_mp_dot_grant(self):
        self.assertIn("ebbing", BUFF_DEFINITIONS)

        # Mock target as immune to ebbing
        with patch(
            "world.rules.action.equipment_immune_buff_keys",
            return_value=frozenset({"ebbing"}),
        ):
            effects = _handle_buff_apply(
                self.actor,
                [self.target],
                "buff_apply:ebbing",
                {},
                1.0,
            )
            # Staged neutralization effect
            for eff in effects:
                eff.apply()

            self.assertNotIn("ebbing", entity_active_buffs(self.target))
            self.assertEqual(int(self.target.traits.mp.current), 100)


class TransactionalRollbackTests(MpFlowTestBase):
    """Scenario: Reaction cascades stay in the initiating transaction."""

    def test_action_pipeline_failure_rolls_back_mp_and_reaction_buff(self):
        skill = self._register_synth_skill(
            _make_synth_skill(
                "synth_failing_spell",
                element="water",
                target_spec=TargetSpec.SINGLE,
                cost={"mp": 50},
                effects=("buff_apply:focus",),
            )
        )
        rule = Rule(
            id="synth_failing_reaction",
            when={"event": "mp_zero", "event_source_skill": skill.key},
            then={"apply_buff": "suffocated"},
        )
        self._add_synth_rule(rule)

        self.actor.traits.mp.current = 50
        skills = dict(self.actor.db.skills or {})
        skills["active"] = [skill.key]
        self.actor.db.skills = skills

        context = RoomActionContext(self.room)
        request = ActionRequest(self.actor, skill.key, [self.target], context)

        # Inject failure during commit
        from world.rules.action import register_event_effect_planner, _EVENT_EFFECT_PLANNERS

        def failing_planner(req, log):
            raise RuntimeError("injected commit crash")

        patcher = patch.dict(_EVENT_EFFECT_PLANNERS, {"fail_plan": failing_planner}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        with patch("world.rules.combat.roll_d100", return_value=50):
            result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "rejected")
            # Both MP deduction and reaction-applied buff must be completely restored
            self.assertEqual(int(self.actor.traits.mp.current), 50)
            self.assertNotIn("suffocated", entity_active_buffs(self.actor))

    def test_clock_advance_failure_restores_mp_and_reaction_buff(self):
        buff_def = self._register_synth_buff(
            BuffDefinition(
                key="synth_clock_dot",
                duration=60,
                tick_interval=10,
                stacking="refresh",
                polarity="debuff",
                modifiers={"rate": {"target": "mp", "delta": -20}},
            )
        )
        drain_skill = self._register_synth_skill(
            _make_synth_skill("synth_clock_source", element="water", cost={"mp": 24})
        )
        rule = Rule(
            id="synth_clock_suffocation",
            when={"event": "mp_zero", "event_source_skill": drain_skill.key},
            then={"apply_buff": "suffocated"},
        )
        self._add_synth_rule(rule)

        self.target.traits.mp.current = 20
        apply_buff(
            self.target,
            buff_def.key,
            source_skill=drain_skill.key,
            source_tier=T_ADEPT,
        )
        initial_mp = int(self.target.traits.mp.current)
        self.assertNotIn("suffocated", entity_active_buffs(self.target))

        from world.rules.clock import (
            AdvanceSource,
            WorldClock,
            build_advance_snapshot_registry,
            _restore_advance_registry,
        )

        clock = WorldClock()
        registry = build_advance_snapshot_registry(clock, 10, AdvanceSource.COMMAND, (self.target,))

        # Clock advance ticks buff -> MP drops to 0 -> mp_zero dispatches -> suffocated applied
        tick_buffs(self.target, 10)
        self.assertEqual(int(self.target.traits.mp.current), 0)
        self.assertIn("suffocated", entity_active_buffs(self.target))

        # Late failure restores registry
        _restore_advance_registry(registry, (self.target,))
        self.assertEqual(int(self.target.traits.mp.current), initial_mp)
        self.assertNotIn("suffocated", entity_active_buffs(self.target))
