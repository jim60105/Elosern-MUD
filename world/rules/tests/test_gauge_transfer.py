"""Synthetic behavior tests for the typed gauge_transfer effect family.

Exercises:
- Gauge transfer mode parsing and fail-closed validation (closed set {mp, hp}, sp rejected, hp drain-only)
- Policy fail-closed validation (recovery share in [0, 1], buff keys in BUFF_DEFINITIONS, bonuses on restore only)
- Unconditional defense bypass and execution-tier damage validation
- MP drain with caster share computed on actual drained amount (clamped pool)
- Fraction rounding on drain
- Whole-pool drain dispatching exactly one attributed mp_zero depletion event
- HP drain with caster share paying on actual HP loss with attributed hp_loss reaction
- HP drain dead-caster never-revive guard
- Fraction drain rounding and caster share banker's rounding
- HP drain to zero producing exactly one death settlement in combat pipeline
- Nonlethal HP drain flooring at 1 HP with knockout mark
- Alternate schools reusing gauge_transfer family generically
- Half-applied-leg transactional rollback on commit failure
- MP restore with active marker stack counts read on the caster (never recipient) and per-target clamping
- MP restore area batch clamping across multiple recipients without depletion event
- Deep-sea reflux (mana_reflux) share bonus folded additively into caster recovery share
- Audience condition gate (mp_max_zero / mp_positive) with synthetic disjoint-subset proof for 溺潮 redirect
- Stale preflight re-evaluation and gate composition with relation audiences
- Gate composition with relation audiences (filtering by both relation and gauge condition)
- Gapless target handling (missing traits/mp) matching neither gate without crashing
- Regen lock (mp_regen_lock) freezing clock regen without touching remainder and item grant bypass
- Regen lock expiry and resumption of closed-form regen with carried remainder intact
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

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")
_cost_mod = importlib.import_module("world.skills.cost_tiers")
_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")
_APPRENTICE = list(_cost_tiers_table.keys())[0]


def _make_synth_transfer_skill(
    key: str,
    effects: tuple[str, ...] | list[str],
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] | None = None,
    *,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    kind: SkillKind = SkillKind.ACTIVE,
) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP.get("water"),
        effects=list(effects),
        effect_policies=tuple(effect_policies) if effect_policies is not None else (),
        category=SkillCategory.ELEMENTAL_MAGIC,
    )


class GaugeTransferTestBase(EvenniaTest):
    """Base test case providing clean rooms, characters, and skill registration."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_transfer_room")
        self.actor = create_object(PlayerCharacter, key="synth_transfer_actor")
        self.target = create_object(PlayerCharacter, key="synth_transfer_target")
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
        self.actor.db.skills = {"active": [skill.key], "passive": []}
        return skill

    def _cast(self, skill_key: str, targets: list[Any], context_override: dict[str, Any] | None = None) -> Any:
        ctx = RoomActionContext(self.room)
        if context_override:
            for k, v in context_override.items():
                setattr(ctx, k, v)
        request = ActionRequest(self.actor, skill_key, targets, ctx)
        return ActionResolver.resolve(request)


class GaugeTransferParseAndValidationTests(GaugeTransferTestBase):
    """Tests for parse_effect, GaugeTransferEffect, GaugeTransferPolicy, and SkillDef policy validation."""

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_gauge_transfer_modes_parse_into_typed_dataclasses(self):
        # MP modes
        eff1 = parse_effect("gauge_transfer:mp:drain:fixed:5")
        self.assertEqual(eff1, GaugeTransferEffect("mp", "drain", "fixed", 5))

        eff2 = parse_effect("gauge_transfer:mp:drain:fraction:0.2")
        self.assertEqual(eff2, GaugeTransferEffect("mp", "drain", "fraction", 0.2))

        eff3 = parse_effect("gauge_transfer:mp:drain:all")
        self.assertEqual(eff3, GaugeTransferEffect("mp", "drain", "all", None))

        eff4 = parse_effect("gauge_transfer:mp:restore:fixed:40")
        self.assertEqual(eff4, GaugeTransferEffect("mp", "restore", "fixed", 40))

        # HP drain modes
        eff5 = parse_effect("gauge_transfer:hp:drain:fixed:10")
        self.assertEqual(eff5, GaugeTransferEffect("hp", "drain", "fixed", 10))

        eff6 = parse_effect("gauge_transfer:hp:drain:fraction:0.5")
        self.assertEqual(eff6, GaugeTransferEffect("hp", "drain", "fraction", 0.5))

        eff7 = parse_effect("gauge_transfer:hp:drain:all")
        self.assertEqual(eff7, GaugeTransferEffect("hp", "drain", "all", None))

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_closed_gauge_set_rejects_sp_and_unknown_gauges(self):
        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:sp:drain:fixed:5")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:stamina:drain:fixed:5")

        with self.assertRaises(ValueError):
            GaugeTransferEffect(gauge="sp", direction="drain", magnitude_mode="fixed", magnitude=5)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_hp_restore_rejected_at_parse_and_construction(self):
        # HP restoration is the heal effect's exclusive verb; gauge_transfer:hp:restore is forbidden
        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:fixed:40")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:fraction:0.5")

        with self.assertRaises(ValueError):
            parse_effect("gauge_transfer:hp:restore:all")

        with self.assertRaises(ValueError):
            GaugeTransferEffect(gauge="hp", direction="restore", magnitude_mode="fixed", magnitude=40)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_malformed_modes_and_magnitudes_fail_closed(self):
        malformed = [
            "gauge_transfer:mp:drain",
            "gauge_transfer:mp:drain:half",
            "gauge_transfer:mp:drain:fraction:1.5",
            "gauge_transfer:mp:drain:fraction:0.0",
            "gauge_transfer:mp:drain:fraction:-0.2",
            "gauge_transfer:mp:drain:fixed:0",
            "gauge_transfer:mp:drain:fixed:-5",
            "gauge_transfer:mp:drain:fixed:abc",
            "gauge_transfer:mp:drain:all:extra",
            "gauge_transfer",
            "gauge_transfer:mp",
        ]
        for m in malformed:
            with self.subTest(m=m):
                with self.assertRaises(ValueError):
                    parse_effect(m)

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    @covers_requirement("gauge-transfer-effects::gauge-transfer-is-one-typed-effect-family-with-a-closed-gauge-set-and-validated-magnitude-modes")
    def test_gauge_transfer_policy_fail_closed_validation(self):
        # Invalid caster_recovery_share
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share=-0.1)
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share=1.5)
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(caster_recovery_share="0.5")  # not numeric

        # Valid share
        policy = GaugeTransferPolicy(caster_recovery_share=0.5)
        self.assertEqual(policy.caster_recovery_share, 0.5)

        # Unknown buff key in restore_bonus_per_stack
        with self.assertRaises(ValueError):
            GaugeTransferPolicy(restore_bonus_per_stack=(("nonexistent_buff_key", 10),))

        # Valid restore_bonus_per_stack with ebbing keys
        policy_bonus = GaugeTransferPolicy(
            restore_bonus_per_stack=(("ebbing", 10), ("ebbing_deep", 10), ("ebbing_maelstrom", 10))
        )
        self.assertEqual(len(policy_bonus.restore_bonus_per_stack), 3)

        # Bonus on drain direction rejected at SkillDef construction
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_drain_with_bonus",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(
                    EffectPolicy(
                        transfer=GaugeTransferPolicy(restore_bonus_per_stack=(("ebbing", 10),))
                    ),
                ),
            )

        # Non-identity potency coefficient rejected at SkillDef construction
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_scaled_transfer",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(EffectPolicy(coefficient=1.5),),
            )

        # DamagePolicy on GaugeTransferEffect rejected
        with self.assertRaises(ValueError):
            _make_synth_transfer_skill(
                "invalid_dmg_on_transfer",
                effects=["gauge_transfer:mp:drain:fixed:5"],
                effect_policies=(EffectPolicy(damage=DamagePolicy(predicate=())),),
            )

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_every_shipped_registry_effect_still_parses(self):
        for skill in _SKILL_MAP.values():
            for effect_id in skill.effects:
                parsed = parse_effect(effect_id)
                self.assertIsNotNone(parsed)


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


class GaugeTransferRestoreTests(GaugeTransferTestBase):
    """Behavior tests for MP restore and active marker stack bonus."""

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::restores-clamp-per-target-and-add-the-caster-s-active-marker-stack-bonus")
    def test_mp_restore_stack_bonus_reads_caster_not_recipient(self):
        """Scenario: Per-stack bonus reads the caster: caster holds markers, recipient gains base + bonus."""
        self.target.traits.mp.current = 10
        self.actor.traits.mp.current = 100

        # Apply ebbing markers to caster (1 each of ebbing, ebbing_deep, ebbing_maelstrom)
        apply_buff(self.actor, "ebbing")
        apply_buff(self.actor, "ebbing_deep")
        apply_buff(self.actor, "ebbing_maelstrom")

        skill = _make_synth_transfer_skill(
            "synth_ring_of_reflux",
            effects=("gauge_transfer:mp:restore:fixed:40",),
            effect_policies=(
                EffectPolicy(
                    transfer=GaugeTransferPolicy(
                        restore_bonus_per_stack=(("ebbing", 10), ("ebbing_deep", 10), ("ebbing_maelstrom", 10))
                    )
                ),
            ),
        )
        self._register_synth_skill(skill)

        # Caster has 3 markers -> +30 bonus -> 40 + 30 = 70 MP restored
        result = self._cast(skill.key, [self.target])
        self.assertEqual(result.outcome, "success")
        # 10 + 70 = 80 MP
        self.assertEqual(int(self.target.traits.mp.current), 80)

        # Same cast from a marker-free caster gains base only
        self.actor.buffs.clear()
        self.target.traits.mp.current = 10
        result_free = self._cast(skill.key, [self.target])
        self.assertEqual(result_free.outcome, "success")
        # 10 + 40 (base only) = 50 MP
        self.assertEqual(int(self.target.traits.mp.current), 50)

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::restores-clamp-per-target-and-add-the-caster-s-active-marker-stack-bonus")
    def test_mp_restore_overflow_clamps_without_depletion_event(self):
        """Scenario: Overflow clamps at maximum without dispatching depletion."""
        self.target.traits.mp.current = 90

        skill = _make_synth_transfer_skill(
            "synth_restore_overflow",
            effects=("gauge_transfer:mp:restore:fixed:40",),
        )
        self._register_synth_skill(skill)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction:
            result = self._cast(skill.key, [self.target])
            self.assertEqual(result.outcome, "success")
            self.assertEqual(int(self.target.traits.mp.current), 100)
            mock_reaction.assert_not_called()

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement("gauge-transfer-effects::restores-clamp-per-target-and-add-the-caster-s-active-marker-stack-bonus")
    def test_mp_restore_area_batch_clamping_without_depletion(self):
        """Scenario: Area restore pushes one ally over max while another gains fully without depletion event."""
        ally_a = self.target
        ally_a.traits.mp.current = 90
        ally_b = create_object(PlayerCharacter, key="synth_restore_ally_b")
        ally_b.location = self.room
        ally_b.race = "human"
        ally_b.apply_race_baseline()
        ally_b.traits.mp.base = 100
        ally_b.traits.mp.current = 20

        skill = _make_synth_transfer_skill(
            "synth_area_restore",
            effects=("gauge_transfer:mp:restore:fixed:40",),
            target_spec=TargetSpec.AREA,
        )
        self._register_synth_skill(skill)

        with patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction:
            result = self._cast(skill.key, [ally_a, ally_b])
            self.assertEqual(result.outcome, "success")

            # ally_a clamped to 100
            self.assertEqual(int(ally_a.traits.mp.current), 100)
            # ally_b gained full 40 -> 60
            self.assertEqual(int(ally_b.traits.mp.current), 60)

            # Neither triggered depletion event
            mock_reaction.assert_not_called()


class AudienceConditionTests(GaugeTransferTestBase):
    """Tests for EffectPolicy.audience_condition and plan_effect_audiences filtering."""

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-changing-skill-faction-constraints"
    )
    @covers_requirement("gauge-transfer-effects::a-component-s-audience-gate-selects-its-recipients-by-stored-target-state")
    def test_audience_condition_validation_and_rejection(self):
        # Unknown fact raises
        with self.assertRaises(ValueError):
            EffectPolicy(audience_condition="unknown_fact")

        # Contradictory facts raise
        with self.assertRaises(ValueError):
            EffectPolicy(audience_condition={"mp_max_zero": True, "mp_positive": True})

        with self.assertRaises(ValueError):
            EffectPolicy(audience_condition=("mp_max_zero", "mp_positive"))

        # Valid string
        p1 = EffectPolicy(audience_condition="mp_max_zero")
        self.assertEqual(p1.audience_condition, "mp_max_zero")

        # Valid mapping
        p2 = EffectPolicy(audience_condition={"mp_positive": True})
        self.assertEqual(p2.audience_condition, "mp_positive")

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    @covers_requirement("gauge-transfer-effects::a-component-s-audience-gate-selects-its-recipients-by-stored-target-state")
    def test_disjoint_subset_proof_drowned_surging_redirect(self):
        """Synthetic disjoint-subset proof: ungated component to all + zero-max rider to matching subset.

        Proves 溺潮's redirect is expressible as pure catalog data (design D4).
        """
        # Target A has normal MP (max 100)
        target_a = self.target
        target_a.traits.mp.base = 100
        target_a.traits.mp.current = 50

        # Target B has max MP = 0
        target_b = create_object(PlayerCharacter, key="synth_zero_max_target")
        target_b.location = self.room
        target_b.race = "human"
        target_b.apply_race_baseline()
        target_b.traits.hp.base = 200
        target_b.traits.hp.current = 200
        target_b.traits.mp.base = 0
        target_b.traits.mp.current = 0

        # Skill has 2 components:
        # 1. Drain 5 MP (ungated, SELECTED audience)
        # 2. Damage (gated by mp_max_zero)
        skill = _make_synth_transfer_skill(
            "synth_drowned_surging_proof",
            effects=(
                "gauge_transfer:mp:drain:fixed:5",
                "damage:water:magic",
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.SELECTED),
                EffectPolicy(
                    audience=EffectAudience.SELECTED,
                    audience_condition="mp_max_zero",
                ),
            ),
        )

        ctx = RoomActionContext(self.room)
        routed = plan_effect_audiences(self.actor, ctx, skill, [target_a, target_b])

        # Component 1 (drain) lands on BOTH target_a and target_b
        self.assertEqual(routed[0], [target_a, target_b])
        # Component 2 (damage rider) lands ONLY on target_b (zero-max)
        self.assertEqual(routed[1], [target_b])

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    @covers_requirement("gauge-transfer-effects::a-component-s-audience-gate-selects-its-recipients-by-stored-target-state")
    def test_stale_preflight_reevaluates_identical_gate(self):
        """Preflight and final resolution evaluate current stored state identically."""
        target = self.target
        target.traits.mp.base = 100

        skill = _make_synth_transfer_skill(
            "synth_gate_stale_test",
            effects=(
                "damage:water:magic",
                "damage:water:magic",
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.SELECTED),
                EffectPolicy(audience=EffectAudience.SELECTED, audience_condition="mp_max_zero"),
            ),
        )

        ctx = RoomActionContext(self.room)
        # Preflight: Target has MP > 0, so gated component excludes it; ungated includes it
        routed1 = plan_effect_audiences(self.actor, ctx, skill, [target])
        self.assertEqual(routed1[0], [target])
        self.assertEqual(routed1[1], [])

        # Target max MP becomes 0 before final execution
        target.traits.mp.base = 0
        routed2 = plan_effect_audiences(self.actor, ctx, skill, [target])
        self.assertEqual(routed2[0], [target])
        self.assertEqual(routed2[1], [target])

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    @covers_requirement("gauge-transfer-effects::a-component-s-audience-gate-selects-its-recipients-by-stored-target-state")
    def test_gate_composition_with_relation_audiences(self):
        """Scenario: Gate composition with relation audiences filters by relation AND gauge state."""
        from world.rules.combat import Battlefield, BattlefieldActionContext

        ally_with_mp = self.target
        ally_with_mp.traits.mp.base = 100
        ally_with_mp.traits.mp.current = 50

        ally_zero_mp = create_object(PlayerCharacter, key="synth_ally_zero_mp")
        ally_zero_mp.location = self.room
        ally_zero_mp.race = "human"
        ally_zero_mp.apply_race_baseline()
        ally_zero_mp.traits.mp.base = 0
        ally_zero_mp.traits.mp.current = 0

        enemy_with_mp = create_object(PlayerCharacter, key="synth_enemy_with_mp")
        enemy_with_mp.location = self.room
        enemy_with_mp.race = "human"
        enemy_with_mp.apply_race_baseline()
        enemy_with_mp.traits.mp.base = 100
        enemy_with_mp.traits.mp.current = 50

        enemy_zero_mp = create_object(PlayerCharacter, key="synth_enemy_zero_mp")
        enemy_zero_mp.location = self.room
        enemy_zero_mp.race = "human"
        enemy_zero_mp.apply_race_baseline()
        enemy_zero_mp.traits.mp.base = 0
        enemy_zero_mp.traits.mp.current = 0

        actor_key = str(self.actor.key)
        ally_with_mp_key = str(ally_with_mp.key)
        ally_zero_mp_key = str(ally_zero_mp.key)
        enemy_with_mp_key = str(enemy_with_mp.key)
        enemy_zero_mp_key = str(enemy_zero_mp.key)

        battlefield = Battlefield(
            {
                "party": frozenset({actor_key, ally_with_mp_key, ally_zero_mp_key}),
                "foes": frozenset({enemy_with_mp_key, enemy_zero_mp_key}),
            },
            {
                actor_key: self.actor,
                ally_with_mp_key: ally_with_mp,
                ally_zero_mp_key: ally_zero_mp,
                enemy_with_mp_key: enemy_with_mp,
                enemy_zero_mp_key: enemy_zero_mp,
            },
        )
        ctx = BattlefieldActionContext(battlefield)

        skill = _make_synth_transfer_skill(
            "synth_composed_gate_skill",
            effects=("gauge_transfer:mp:restore:fixed:40",),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ALLIES,
                    audience_condition="mp_positive",
                ),
            ),
        )

        all_targets = [ally_with_mp, ally_zero_mp, enemy_with_mp, enemy_zero_mp]
        routed = plan_effect_audiences(self.actor, ctx, skill, all_targets)

        # Only ally_with_mp satisfies BOTH Relation.ALLY and mp_positive
        self.assertEqual(routed[0], [ally_with_mp])
        self.assertNotIn(ally_zero_mp, routed[0])
        self.assertNotIn(enemy_with_mp, routed[0])
        self.assertNotIn(enemy_zero_mp, routed[0])

    @covers_requirement(
        "action-resolution-pipeline::audience-planning-agrees-between-preflight-and-final-resolution"
    )
    def test_gapless_target_matches_neither_gate_without_crashing(self):
        """An entity lacking traits or an MP gauge matches neither gate and does not crash resolution."""
        gapless = create_object(Room, key="gapless_entity")  # Room has no character traits

        skill = _make_synth_transfer_skill(
            "synth_gapless_test",
            effects=(
                "damage:water:magic",
                "damage:water:magic",
            ),
            effect_policies=(
                EffectPolicy(audience=EffectAudience.SELECTED),  # ungated
                EffectPolicy(audience=EffectAudience.SELECTED, audience_condition="mp_max_zero"),  # gated
            ),
        )

        ctx = RoomActionContext(self.room)
        routed = plan_effect_audiences(self.actor, ctx, skill, [gapless, self.target])

        # Ungated hits both gapless and target
        self.assertIn(gapless, routed[0])
        self.assertIn(self.target, routed[0])

        # Gated excludes gapless (lacks MP gauge) and excludes normal target (has positive MP max)
        self.assertNotIn(gapless, routed[1])


class RegenLockAndClockTests(GaugeTransferTestBase):
    """Behavior tests for mp_regen_lock, closed-form regen scale, and item bypass."""

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_mp_regen_lock_freezes_regen_and_preserves_remainder(self):
        """Scenario: Locked gauge regenerates nothing while the lock lives."""
        self.target.traits.mp.current = 20
        self.target.traits.mp.regen_remainder = 0.5

        # Apply mp_regen_lock debuff
        apply_buff(self.target, "mp_regen_lock")

        # Verify combat modifier reports mp_regen_scale: 0
        mods = evaluate_combat_modifiers(self.target)
        self.assertEqual(mods.get("mp_regen_scale"), 0)

        # Advance gauge regen
        _settle_gauge_regen([self.target], 30)
        self.assertEqual(int(self.target.traits.mp.current), 20)
        self.assertEqual(self.target.traits.mp.regen_remainder, 0.5)

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_authored_grants_bypass_regen_lock(self):
        """Scenario: Authored grants bypass the lock: direct MP changes work while regen is locked."""
        self.target.traits.mp.current = 20
        apply_buff(self.target, "mp_regen_lock")

        # Authored restore / direct change
        apply_mp_change(self.target, 30)
        self.assertEqual(int(self.target.traits.mp.current), 50)

    @covers_requirement(
        "world-clock::gauge-regen-is-a-closed-form-computation-never-a-per-second-or-per-quantum-loop"
    )
    @covers_requirement("gauge-transfer-effects::regen-lock-is-a-bounded-marker-consumed-by-the-clock-s-closed-form-regen")
    def test_mp_regen_lock_expiry_resumes_closed_form_regen(self):
        """Scenario: Locked gauge freezes regen, and expiry resumes closed-form regen with remainder intact."""
        self.target.traits.mp.current = 20
        self.target.traits.mp.rate = 1.0
        self.target.traits.mp.regen_remainder = 0.35

        apply_buff(self.target, "mp_regen_lock")

        # Locked: 30s yields 0 gain, remainder untouched
        _settle_gauge_regen([self.target], 30)
        self.assertEqual(int(self.target.traits.mp.current), 20)
        self.assertEqual(self.target.traits.mp.regen_remainder, 0.35)

        # Decay buffs past duration (60s duration -> 61s elapsed)
        _settle_buffs_and_decay([self.target], 61)
        mods = evaluate_combat_modifiers(self.target)
        self.assertNotIn("mp_regen_scale", mods)

        # Lock expired: 10s yields +10 MP, remainder preserved
        _settle_gauge_regen([self.target], 10)
        self.assertEqual(int(self.target.traits.mp.current), 30)
        self.assertAlmostEqual(self.target.traits.mp.regen_remainder, 0.35, places=5)
