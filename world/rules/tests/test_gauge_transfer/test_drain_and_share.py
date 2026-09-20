"""Slice of ``test_gauge_transfer``: drain/settle settlement and the
caster-recovery share policy.
"""
import importlib
from typing import Any
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _handle_gauge_transfer,
    _stored_trait_value,
    plan_effect_audiences,
    stored_gauge_pair,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    active_stack_count,
    apply_buff,
)
from world.rules.clock import AdvanceSource, WorldClock, _settle_gauge_regen
from world.rules.clock import _settle_buffs_and_decay
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.mp_flow import apply_mp_change
from world.rules.targeting import RoomActionContext
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferEffect,
    GaugeTransferPolicy,
    parse_effect,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)


from ._support import (
    GaugeTransferTestBase,
    _APPRENTICE,
    _ELEMENT_MAP,
    _make_synth_transfer_skill,
)


class GaugeTransferDrainAndShareTests(GaugeTransferTestBase):
    """Behavior tests for drain legs and caster recovery share."""

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_mp_fraction_rounding_on_drain(self):
        """Scenario: Fraction drain rounds to integer, and caster share uses banker's rounding."""
        self.target.traits.mp.current = 33
        self.actor.traits.mp.current = 50

        skill = _make_synth_transfer_skill(
            "synth_fraction_rounding",
            effects=("gauge_transfer:mp:drain:fraction:0.2",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        result = self._cast(skill.key, [self.target])
        self.assertEqual(result.outcome, "success")

        # 33 * 0.2 = 6.6 -> round(6.6) = 7. Target 33 - 7 = 26 MP
        self.assertEqual(int(self.target.traits.mp.current), 26)
        # Actual drained = 7. Share = round(7 * 0.5) = round(3.5) = 4 (banker's round-half-to-even: 3.5 -> 4)
        # Caster 50 + 4 = 54 MP
        self.assertEqual(int(self.actor.traits.mp.current), 54)

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_mp_drain_half_share_on_clamped_pool(self):
        """Scenario: Half-share on a clamped drain: target has 3 MP, drain requested 5, caster gets half of actual 3."""
        self.target.traits.mp.current = 3
        self.actor.traits.mp.current = 50

        skill = _make_synth_transfer_skill(
            "synth_tide_pull",
            effects=("gauge_transfer:mp:drain:fixed:5",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction:
            result = self._cast(skill.key, [self.target])
            self.assertEqual(result.outcome, "success")

            # Target clamped from 3 to 0
            self.assertEqual(int(self.target.traits.mp.current), 0)
            # Caster gained round(3 * 0.5) = 2 MP (share on actual 3, not requested 5)
            self.assertEqual(int(self.actor.traits.mp.current), 52)

            # mp_zero event fired once with cast attribution
            mock_reaction.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=_APPRENTICE,
                source_skill=skill.key,
            )

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_mp_fraction_maw_empties_proportionally(self):
        """Scenario: Fractional maw empties proportionally: 20% of 100 MP = 20 MP into caster with 1.0 share."""
        self.target.traits.mp.current = 100
        self.actor.traits.mp.current = 20

        skill = _make_synth_transfer_skill(
            "synth_abyssal_maw",
            effects=("gauge_transfer:mp:drain:fraction:0.2",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=1.0)),
            ),
        )
        self._register_synth_skill(skill)

        result = self._cast(skill.key, [self.target])
        self.assertEqual(result.outcome, "success")

        # 100 * 0.2 = 20 MP drained
        self.assertEqual(int(self.target.traits.mp.current), 80)
        # Caster gains 20 MP: 20 + 20 = 40
        self.assertEqual(int(self.actor.traits.mp.current), 40)

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_mp_whole_pool_drain_dispatches_one_depletion_event(self):
        """Scenario: Whole-pool drain removes all MP and dispatches one depletion event."""
        self.target.traits.mp.current = 75

        skill = _make_synth_transfer_skill(
            "synth_drain_all",
            effects=("gauge_transfer:mp:drain:all",),
        )
        self._register_synth_skill(skill)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction:
            result = self._cast(skill.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(int(self.target.traits.mp.current), 0)

            mock_reaction.assert_called_once_with(
                self.target,
                "mp_zero",
                source_tier=_APPRENTICE,
                source_skill=skill.key,
            )

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_hp_drain_shares_actual_hp_taken(self):
        """Scenario: HP drain with caster share pays on ACTUAL drained HP and dispatches hp_loss."""
        self.target.traits.hp.current = 15
        self.actor.traits.hp.current = 50

        skill = _make_synth_transfer_skill(
            "synth_hp_leech",
            effects=("gauge_transfer:hp:drain:fixed:30",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction:
            result = self._cast(skill.key, [self.target])
            self.assertEqual(result.outcome, "success")

            # Target HP loses actual 15
            self.assertEqual(int(self.target.traits.hp.current), 0)
            # Caster gains round(15 * 0.5) = 8 HP
            self.assertEqual(int(self.actor.traits.hp.current), 58)

            # Dispatches hp_loss
            mock_reaction.assert_called_once_with(
                self.target,
                "hp_loss",
                source_tier=_APPRENTICE,
                hp_loss_amount=15,
            )

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_hp_drain_dead_caster_never_revived(self):
        """Dead caster with 0 HP is never revived by an HP recovery share."""
        self.target.traits.hp.current = 50
        self.actor.traits.hp.current = 0

        skill = _make_synth_transfer_skill(
            "synth_hp_no_revive",
            effects=("gauge_transfer:hp:drain:fixed:20",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        # Execute handler directly to simulate dead caster receiving share
        effs = _handle_gauge_transfer(
            self.actor,
            [self.target],
            "gauge_transfer:hp:drain:fixed:20",
            {
                "resolved_effect": type("Resolved", (), {
                    "policy": EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
                    "source_skill": skill,
                })()
            },
            1.0,
        )
        for eff in effs:
            eff.apply()

        # Target lost 20 HP
        self.assertEqual(int(self.target.traits.hp.current), 30)
        # Caster stays at 0 HP (never revived!)
        self.assertEqual(int(self.actor.traits.hp.current), 0)

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_hp_drain_to_zero_settles_single_death(self):
        """Scenario: HP drain-to-zero settles exactly one death through the combat pipeline."""
        self.target.traits.hp.current = 10

        skill = _make_synth_transfer_skill(
            "synth_hp_execute",
            effects=("gauge_transfer:hp:drain:fixed:10",),
        )
        self._register_synth_skill(skill)

        result = self._cast(skill.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.target.traits.hp.current), 0)

        # EventLog produced exactly one target_defeated entry
        defeated_entries = [e for e in result.event_log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeated_entries), 1)
        self.assertEqual(defeated_entries[0].target, str(self.target.key))

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_hp_drain_nonlethal_knockout_honored(self):
        """Scenario: HP drain under nonlethal context floors at 1 HP, shares actual loss, no defeat event."""
        self.target.traits.hp.current = 10
        self.actor.traits.hp.current = 50

        skill = _make_synth_transfer_skill(
            "synth_hp_nonlethal",
            effects=("gauge_transfer:hp:drain:fixed:10",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        ctx = RoomActionContext(self.room)
        ctx.event_context["nonlethal"] = True
        request = ActionRequest(self.actor, skill.key, [self.target], ctx)
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")

        # Under nonlethal projection, lethal crossing clamps to 1 HP
        self.assertEqual(int(self.target.traits.hp.current), 1)
        # Actual loss = 10 - 1 = 9 HP. Share = round(9 * 0.5) = round(4.5) = 4 (round-half-to-even: 4.5 -> 4)
        self.assertEqual(int(self.actor.traits.hp.current), 54)

        # No target_defeated entry in event log
        defeated = [e for e in result.event_log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeated), 0)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_alternate_schools_reuse_the_family(self):
        """Scenario: Non-water synthetic skill reuses gauge_transfer family without element-specific code."""
        self.target.traits.mp.current = 100
        self.actor.traits.mp.current = 50

        fire_skill = SkillDef(
            key="synth_fire_mana_burn",
            label="合成火能燃燒",
            description="非水系合成轉移技能。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=_ELEMENT_MAP.get("fire"),
            effects=["gauge_transfer:mp:drain:fixed:10"],
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
            category=SkillCategory.ELEMENTAL_MAGIC,
        )
        self._register_synth_skill(fire_skill)

        result = self._cast(fire_skill.key, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.target.traits.mp.current), 90)
        self.assertEqual(int(self.actor.traits.mp.current), 55)

    @covers_requirement(
        "action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated"
    )
    @covers_requirement("gauge-transfer-effects::drains-pay-through-their-gauge-s-canonical-writer-on-both-legs-and-share-on-the-actual-amount")
    def test_half_applied_leg_rollback_on_commit_failure(self):
        """Scenario: A failed commit restores both legs."""
        self.target.traits.mp.current = 50
        self.actor.traits.mp.current = 20

        skill = _make_synth_transfer_skill(
            "synth_failing_transfer",
            effects=("gauge_transfer:mp:drain:fixed:20",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        with patch("world.rules.action.resolver._commit", side_effect=RuntimeError("simulated commit failure")):
            with self.assertRaises(RuntimeError):
                self._cast(skill.key, [self.target])

        # Both entities are restored to exact pre-cast state
        self.assertEqual(int(self.target.traits.mp.current), 50)
        self.assertEqual(int(self.actor.traits.mp.current), 20)
    @covers_requirement(
        "combat-modifier-table::combat-modifiers-yaml-is-one-table-evaluated-by-one-condition-engine-with-no"
    )
    def test_mana_reflux_share_bonus_folds_additively(self):
        """Caster with active mana_reflux gains +10% recovery share folded additively."""
        self.target.traits.mp.current = 50
        self.actor.traits.mp.current = 20

        skill = _make_synth_transfer_skill(
            "synth_drain_reflux",
            effects=("gauge_transfer:mp:drain:fixed:10",),
            effect_policies=(
                EffectPolicy(transfer=GaugeTransferPolicy(caster_recovery_share=0.5)),
            ),
        )
        self._register_synth_skill(skill)

        # Without reflux: 50% of 10 = 5 MP recovered
        result1 = self._cast(skill.key, [self.target])
        self.assertEqual(result1.outcome, "success")
        self.assertEqual(int(self.actor.traits.mp.current), 25)

        # Apply mana_reflux buff to caster (+10% recovery_share_bonus)
        apply_buff(self.actor, "mana_reflux")
        self.target.traits.mp.current = 50
        self.actor.traits.mp.current = 20

        # With reflux: 50% + 10% = 60% of 10 = 6 MP recovered
        result2 = self._cast(skill.key, [self.target])
        self.assertEqual(result2.outcome, "success")
        self.assertEqual(int(self.actor.traits.mp.current), 26)
