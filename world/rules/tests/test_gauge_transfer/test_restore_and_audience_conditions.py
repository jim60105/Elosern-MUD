"""Slice of ``test_gauge_transfer``: gauge restore and the
audience-condition gating.
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
    _make_synth_transfer_skill,
)


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
