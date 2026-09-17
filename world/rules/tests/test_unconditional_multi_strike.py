"""Synthetic behavior tests for unconditional multi-strike DamagePolicy (unconditional-multi-strike)."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.action_evidence import has_action_evidence, stage_action_evidence
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _stored_hp,
)
from world.rules.tests.combat_fixtures import grant_lineage
from world.rules.traits import restore_gauges_to_full
from world.skills.effects import DamagePolicy, EffectPolicy
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import make_skill, synthetic_registries

# Synthetic skills for unconditional multi-strike tests
_T_UNCONDITIONAL_MULTI = make_skill(
    "t_unconditional_multi",
    element="fire",
    cost={"mp": 12},
    effects=("damage:fire:magic",),
    target_spec=TargetSpec.SINGLE,
    effect_policies=(
        EffectPolicy(
            damage=DamagePolicy(extra_strikes=1),
        ),
    ),
)

_T_CONTROL_SINGLE = make_skill(
    "t_control_single",
    element="fire",
    cost={"mp": 5},
    effects=("damage:fire:magic",),
    target_spec=TargetSpec.SINGLE,
)

_EXTRA_SKILLS = {
    _T_UNCONDITIONAL_MULTI.key: _T_UNCONDITIONAL_MULTI,
    _T_CONTROL_SINGLE.key: _T_CONTROL_SINGLE,
}

_SCOPE = synthetic_registries("skills", extra={"skills": _EXTRA_SKILLS})


class UnconditionalMultiStrikeConstructionTests(unittest.TestCase):
    """Validation and construction matrix tests for DamagePolicy."""

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_well_formed_shapes_construct(self):
        """WHEN valid policies declare extra strikes with or without predicate, they construct."""
        # Unconditional extra strike
        p1 = DamagePolicy(extra_strikes=1)
        self.assertEqual(p1.extra_strikes, 1)
        self.assertIsNone(p1.repeat_when)

        # Unconditional explicit None repeat_when
        p2 = DamagePolicy(extra_strikes=1, repeat_when=None)
        self.assertEqual(p2.extra_strikes, 1)
        self.assertIsNone(p2.repeat_when)

        # Evidence-conditional extra strike
        p3 = DamagePolicy(repeat_when="forced_interaction")
        self.assertEqual(p3.extra_strikes, 1)
        self.assertEqual(p3.repeat_when, "forced_interaction")

        # Default single strike policy
        p4 = DamagePolicy()
        self.assertEqual(p4.extra_strikes, 0)
        self.assertIsNone(p4.repeat_when)

        # Unconditional two extra strikes
        p5 = DamagePolicy(extra_strikes=2)
        self.assertEqual(p5.extra_strikes, 2)
        self.assertIsNone(p5.repeat_when)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_malformed_shapes_raise_value_error(self):
        """WHEN policies declare invalid extra_strikes or repeat_when combinations, they raise."""
        # Unknown evidence kind
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="unknown_kind")
        self.assertIn("unknown DamagePolicy repeat_when predicate", str(ctx.exception))

        # Non-string repeat_when
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when=123)
        self.assertIn("must be a string or None", str(ctx.exception))

        # Boolean extra_strikes rejected
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(extra_strikes=True)
        self.assertIn("must be an int", str(ctx.exception))

        # Out-of-cap extra_strikes > 2
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(extra_strikes=3)
        self.assertIn("must be in (0, 1, 2)", str(ctx.exception))

        # Negative extra_strikes
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(extra_strikes=-1)
        self.assertIn("must be in (0, 1, 2)", str(ctx.exception))

        # repeat_when requiring extra_strikes=1
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=0)
        self.assertIn("requires extra_strikes=1", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=2)
        self.assertIn("requires extra_strikes=1", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=3)
        self.assertIn("must be in (0, 1, 2)", str(ctx.exception))


@_SCOPE
class UnconditionalMultiStrikeSettlementTests(EvenniaTestCase):
    """Behavior tests for unconditional multi-strike settlement mechanics."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="multi_actor")
        self.target = create_object(PlayerCharacter, key="multi_target")
        for ent in (self.actor, self.target):
            ent.race = "human"
            ent.apply_race_baseline()
            restore_gauges_to_full(ent)
            ent.db.skills = {"active": [], "passive": []}
        self.actor.traits.magic_power.base = 40
        self.actor.traits.atk_phys.base = 40
        self.target.traits.defense.base = 10
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)

        grant_lineage(
            self.actor,
            [_T_UNCONDITIONAL_MULTI.key, _T_CONTROL_SINGLE.key],
        )

    def _make_bf(self, nonlethal: bool = False, nonlethal_keys: tuple[str, ...] = ()):
        bf = Battlefield(
            {"party": frozenset({"multi_actor"}), "foes": frozenset({"multi_target"})},
            {"multi_actor": self.actor, "multi_target": self.target},
        )
        event_ctx = {"now": 100}
        if nonlethal:
            event_ctx["nonlethal"] = True
        if nonlethal_keys:
            event_ctx["nonlethal_keys"] = nonlethal_keys
        return bf, BattlefieldActionContext(bf, event_context=event_ctx)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_roll_matrix_hit_hit_records_two_rolls_and_deals_equal_damage(self):
        """WHEN both rolls hit, exactly two rolls are recorded, equal damage is dealt, and cost/practice paid once."""
        initial_hp = _stored_hp(self.target)
        initial_mp = self.actor.traits.mp.current
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]), patch(
            "world.rules.action.grant_skill_practice_xp"
        ) as mock_practice:
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        # Exactly 2 rolls recorded
        self.assertEqual(len(rolls), 2)
        self.assertTrue(rolls[0].data["hit"])
        self.assertTrue(rolls[1].data["hit"])

        # Exactly 2 damage entries with identical damage
        self.assertEqual(len(damages), 2)
        self.assertGreater(damages[0].data["amount"], 0)
        self.assertEqual(damages[0].data["amount"], damages[1].data["amount"])
        self.assertEqual(
            initial_hp - _stored_hp(self.target),
            damages[0].data["amount"] + damages[1].data["amount"],
        )

        # Single MP cost paid
        self.assertEqual(initial_mp - self.actor.traits.mp.current, 12)
        # Practice awarded exactly once
        mock_practice.assert_called_once()

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_roll_matrix_miss_hit_first_miss_does_not_suppress_second_hit(self):
        """WHEN strike 1 misses and strike 2 hits, strike 2 damages target and both rolls are recorded."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[1, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 2)
        self.assertFalse(rolls[0].data["hit"])
        self.assertTrue(rolls[1].data["hit"])

        self.assertEqual(len(damages), 1)
        self.assertEqual(initial_hp - _stored_hp(self.target), damages[0].data["amount"])

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_roll_matrix_hit_miss_first_hit_second_miss(self):
        """WHEN strike 1 hits and strike 2 misses, strike 1 damages target and both rolls are recorded."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[80, 1]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 2)
        self.assertTrue(rolls[0].data["hit"])
        self.assertFalse(rolls[1].data["hit"])

        self.assertEqual(len(damages), 1)
        self.assertEqual(initial_hp - _stored_hp(self.target), damages[0].data["amount"])

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_roll_matrix_miss_miss_deals_zero_damage(self):
        """WHEN both strikes miss, zero damage is dealt and target HP is unchanged."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[1, 1]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 2)
        self.assertFalse(rolls[0].data["hit"])
        self.assertFalse(rolls[1].data["hit"])

        self.assertEqual(len(damages), 0)
        self.assertEqual(_stored_hp(self.target), initial_hp)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_unconditional_policy_ignores_target_action_evidence(self):
        """WHEN target carries fresh evidence or none, an unconditional policy always resolves two strikes."""
        # Case A: target has no evidence
        self.target.db.action_evidence = {}
        self.assertFalse(has_action_evidence(self.target, "forced_interaction", now=100))
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)
        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]):
            res_clean = ActionResolver.resolve(req)
        rolls_clean = [e for e in res_clean.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(rolls_clean), 2)

        # Case B: target has fresh evidence
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()
        self.assertTrue(has_action_evidence(self.target, "forced_interaction", now=100))
        bf2, ctx2 = self._make_bf()
        req2 = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx2)
        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]):
            res_ev = ActionResolver.resolve(req2)
        rolls_ev = [e for e in res_ev.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(rolls_ev), 2)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_ordered_hp_projection_and_single_terminal_defeat(self):
        """WHEN two strikes cross target HP lethally, exactly one target_defeated entry is emitted."""
        self.target.traits.hp.base = 25
        restore_gauges_to_full(self.target)
        self.assertEqual(_stored_hp(self.target), 25)

        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        defeats = [e for e in res.event_log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeats), 1)
        self.assertEqual(defeats[0].target, str(self.target.key))

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_nonlethal_floors_at_1_hp_with_single_knockout_mark(self):
        """WHEN two strikes cross HP in nonlethal combat, HP floors at 1 with exactly one knockout mark."""
        self.target.traits.hp.base = 20
        restore_gauges_to_full(self.target)

        bf, ctx = self._make_bf(nonlethal=True, nonlethal_keys=(str(self.target.key),))
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertEqual(_stored_hp(self.target), 1)

        kos = [e for e in res.event_log.entries if e.kind == "target_knocked_out"]
        self.assertEqual(len(kos), 1)
        self.assertEqual(kos[0].target, str(self.target.key))
        self.assertIn(str(self.target.key), bf.knocked_out)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_atomic_rollback_restores_hp_on_commit_failure(self):
        """WHEN a commit step fails after two strikes, atomic rollback restores HP fully."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_UNCONDITIONAL_MULTI.key, [self.target], ctx)

        def bomb_apply():
            raise RuntimeError("commit explosion")

        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]), patch.dict(
            "world.rules.action._EVENT_EFFECT_PLANNERS",
            {
                "boom": lambda r, l: [
                    PendingEffect(self.target, "boom", frozenset({"traits"}), bomb_apply)
                ]
            },
        ):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(_stored_hp(self.target), initial_hp)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_control_skill_without_damage_policy_resolves_single_strike(self):
        """WHEN a policy-free control skill resolves, it executes exactly one strike."""
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_CONTROL_SINGLE.key, [self.target], ctx)

        with patch("world.rules.combat.roll_d100", side_effect=[80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(rolls), 1)
