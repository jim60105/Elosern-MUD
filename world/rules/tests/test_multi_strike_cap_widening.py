"""Synthetic behavior tests for multi-strike cap widening (multi-strike-cap-widening).

Covers:
1. Fixed-seed 3-roll count and order across hit/mix sweeps (hit-hit-hit, miss-hit-hit, hit-miss-hit, miss-miss-miss)
2. Once-paid resource and practice accounting for a 3-strike cast
3. Ordered HP projection across all three strikes
4. Three-strike divert cap and gauge ledger discipline (cap and MP bounds respected across sweep)
5. Singular terminal defeat emission across a lethal three-strike sweep
6. Nonlethal single-knockout mark and 1 HP flooring across three strikes
7. Atomic rollback restoring HP, MP, and divert state on commit failure
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    get_divert_consumed,
)
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

# Synthetic three-strike skill (total strikes = 1 + 2 = 3)
_T_THREE_STRIKE = make_skill(
    "t_three_strike",
    element="lightning",
    cost={"mp": 20},
    effects=("damage:lightning:magic",),
    target_spec=TargetSpec.SINGLE,
    effect_policies=(
        EffectPolicy(
            damage=DamagePolicy(extra_strikes=2),
        ),
    ),
)

_EXTRA_SKILLS = {
    _T_THREE_STRIKE.key: _T_THREE_STRIKE,
}

_SCOPE = synthetic_registries("skills", extra={"skills": _EXTRA_SKILLS})


@_SCOPE
class MultiStrikeCapWideningSettlementTests(EvenniaTestCase):
    """Behavior tests for widened multi-strike (N=3) settlement mechanics."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="three_actor")
        self.target = create_object(PlayerCharacter, key="three_target")
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
            [_T_THREE_STRIKE.key],
        )

    def _make_bf(self, nonlethal: bool = False, nonlethal_keys: tuple[str, ...] = ()):
        bf = Battlefield(
            {"party": frozenset({"three_actor"}), "foes": frozenset({"three_target"})},
            {"three_actor": self.actor, "three_target": self.target},
        )
        event_ctx = {"now": 100}
        if nonlethal:
            event_ctx["nonlethal"] = True
        if nonlethal_keys:
            event_ctx["nonlethal_keys"] = nonlethal_keys
        return bf, BattlefieldActionContext(bf, event_context=event_ctx)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_roll_matrix_hit_hit_hit_records_three_rolls_and_deals_equal_damage(self):
        """WHEN all three rolls hit, three rolls are recorded in order, equal damage is dealt, and cost/practice paid once."""
        initial_hp = _stored_hp(self.target)
        initial_mp = self.actor.traits.mp.current
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]), patch(
            "world.rules.action.costs.grant_skill_practice_xp"
        ) as mock_practice:
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        # Exactly 3 rolls recorded, all hits
        self.assertEqual(len(rolls), 3)
        self.assertTrue(rolls[0].data["hit"])
        self.assertTrue(rolls[1].data["hit"])
        self.assertTrue(rolls[2].data["hit"])

        # Exactly 3 damage entries with identical damage
        self.assertEqual(len(damages), 3)
        self.assertGreater(damages[0].data["amount"], 0)
        self.assertEqual(damages[0].data["amount"], damages[1].data["amount"])
        self.assertEqual(damages[1].data["amount"], damages[2].data["amount"])
        total_damage = sum(d.data["amount"] for d in damages)
        self.assertEqual(initial_hp - _stored_hp(self.target), total_damage)

        # Single MP cost paid
        self.assertEqual(initial_mp - self.actor.traits.mp.current, 20)
        # Practice awarded exactly once
        mock_practice.assert_called_once()

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_roll_matrix_miss_hit_hit(self):
        """WHEN strike 1 misses and strikes 2 and 3 hit, the first miss does not suppress later strikes."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[1, 80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 3)
        self.assertFalse(rolls[0].data["hit"])
        self.assertTrue(rolls[1].data["hit"])
        self.assertTrue(rolls[2].data["hit"])

        self.assertEqual(len(damages), 2)
        total_damage = sum(d.data["amount"] for d in damages)
        self.assertEqual(initial_hp - _stored_hp(self.target), total_damage)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_roll_matrix_hit_miss_hit(self):
        """WHEN strike 1 hits, strike 2 misses, and strike 3 hits, both hits deal damage."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 1, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 3)
        self.assertTrue(rolls[0].data["hit"])
        self.assertFalse(rolls[1].data["hit"])
        self.assertTrue(rolls[2].data["hit"])

        self.assertEqual(len(damages), 2)
        total_damage = sum(d.data["amount"] for d in damages)
        self.assertEqual(initial_hp - _stored_hp(self.target), total_damage)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_roll_matrix_all_miss(self):
        """WHEN all three strikes miss, zero damage is dealt and target HP is unchanged."""
        initial_hp = _stored_hp(self.target)
        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[1, 1, 1]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        self.assertEqual(len(rolls), 3)
        self.assertFalse(rolls[0].data["hit"])
        self.assertFalse(rolls[1].data["hit"])
        self.assertFalse(rolls[2].data["hit"])

        self.assertEqual(len(damages), 0)
        self.assertEqual(_stored_hp(self.target), initial_hp)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_ordered_hp_projection_across_three_strikes(self):
        """WHEN three strikes resolve, target HP projects ordered damage sequentially across all strikes."""
        self.target.traits.hp.base = 100
        restore_gauges_to_full(self.target)
        self.assertEqual(_stored_hp(self.target), 100)

        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        damages = [e for e in res.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(damages), 3)
        d1, d2, d3 = damages[0].data["amount"], damages[1].data["amount"], damages[2].data["amount"]
        self.assertEqual(100 - _stored_hp(self.target), d1 + d2 + d3)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_divert_cap_and_gauge_ledger_discipline(self):
        """WHEN three strikes hit a target with divert buff, cap and gauge ledgers are respected across all three strikes."""
        # Set magic_power to 30, defense to 10 -> post-defense damage = 20 per strike.
        self.actor.traits.magic_power.base = 30
        self.target.traits.defense.base = 10
        self.target.traits.hp.base = 100
        self.target.traits.mp.base = 100
        restore_gauges_to_full(self.target)

        buff_def = BuffDefinition(
            key="synth_divert_three",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        patched = dict(BUFF_DEFINITIONS)
        patched[buff_def.key] = buff_def

        with patch.dict("world.rules.buffs.definitions.BUFF_DEFINITIONS", patched), patch.dict(
            "world.rules.combat.damage.BUFF_DEFINITIONS", patched
        ):
            apply_buff(self.target, buff_def.key, source_skill="synth_cast")
            self.assertIn(buff_def.key, self.target.buffs.all)

            bf, ctx = self._make_bf()
            req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

            with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]):
                res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")
            # 20 post-defense * 0.5 = 10 diverted per strike.
            # Strike 1: 10 diverted, remaining cap = 20
            # Strike 2: 10 diverted, remaining cap = 10
            # Strike 3: 10 diverted, remaining cap = 0
            # Total diverted = 30 (cap of 30 exhausted)
            buff_inst = self.target.buffs.all[buff_def.key]
            self.assertEqual(get_divert_consumed(buff_inst), 30)

            # MP reduced by 30
            self.assertEqual(self.target.traits.mp.current, 70)

            # Residual HP damage per strike is 20 - 10 = 10; across 3 strikes = 30
            self.assertEqual(_stored_hp(self.target), 70)

            # Exactly 3 damage events with amount=10
            damages = [e for e in res.event_log.entries if e.kind == "damage"]
            self.assertEqual(len(damages), 3)
            for d in damages:
                self.assertEqual(d.data["amount"], 10)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_lethal_crossing_single_defeat_credit(self):
        """WHEN three strikes cross target HP lethally, exactly one target_defeated entry is emitted."""
        # 30 damage per strike. With 40 HP, strike 2 drops target to 0 HP, strike 3 hits at 0 HP.
        self.target.traits.hp.base = 40
        restore_gauges_to_full(self.target)
        self.assertEqual(_stored_hp(self.target), 40)

        bf, ctx = self._make_bf()
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertEqual(_stored_hp(self.target), 0)
        defeats = [e for e in res.event_log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeats), 1)
        self.assertEqual(defeats[0].target, str(self.target.key))

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_nonlethal_floors_at_1_hp_with_single_knockout_mark(self):
        """WHEN three strikes cross HP in nonlethal combat, HP floors at 1 with exactly one knockout mark."""
        # 30 damage per strike against 40 HP in nonlethal mode.
        self.target.traits.hp.base = 40
        restore_gauges_to_full(self.target)

        bf, ctx = self._make_bf(nonlethal=True, nonlethal_keys=(str(self.target.key),))
        req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

        with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertEqual(_stored_hp(self.target), 1)

        kos = [e for e in res.event_log.entries if e.kind == "target_knocked_out"]
        self.assertEqual(len(kos), 1)
        self.assertEqual(kos[0].target, str(self.target.key))
        self.assertIn(str(self.target.key), bf.knocked_out)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_three_strike_atomic_rollback_restores_state_on_commit_failure(self):
        """WHEN a commit step fails after three strikes with divert, atomic rollback restores HP, MP, and divert state."""
        self.actor.traits.magic_power.base = 30
        self.target.traits.defense.base = 10
        self.target.traits.hp.base = 100
        self.target.traits.mp.base = 100
        restore_gauges_to_full(self.target)
        initial_hp = _stored_hp(self.target)
        initial_mp = self.target.traits.mp.current
        initial_actor_mp = self.actor.traits.mp.current

        buff_def = BuffDefinition(
            key="synth_divert_rollback",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        patched = dict(BUFF_DEFINITIONS)
        patched[buff_def.key] = buff_def

        with patch.dict("world.rules.buffs.definitions.BUFF_DEFINITIONS", patched), patch.dict(
            "world.rules.combat.damage.BUFF_DEFINITIONS", patched
        ):
            apply_buff(self.target, buff_def.key, source_skill="synth_cast")
            buff_inst = self.target.buffs.all[buff_def.key]
            self.assertEqual(get_divert_consumed(buff_inst), 0)

            bf, ctx = self._make_bf()
            req = ActionRequest(self.actor, _T_THREE_STRIKE.key, [self.target], ctx)

            def bomb_apply():
                raise RuntimeError("commit explosion")

            with patch("world.rules.combat.damage.roll_d100", side_effect=[80, 80, 80]), patch.dict(
                "world.rules.action.contracts._EVENT_EFFECT_PLANNERS",
                {
                    "boom": lambda r, l: [
                        PendingEffect(self.target, "boom", frozenset({"traits"}), bomb_apply)
                    ]
                },
            ):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "rejected")
            # All HP and MP gauges restored
            self.assertEqual(_stored_hp(self.target), initial_hp)
            self.assertEqual(self.target.traits.mp.current, initial_mp)
            self.assertEqual(self.actor.traits.mp.current, initial_actor_mp)
            # Divert consumed budget restored on freshly queried instance
            fresh_buff = self.target.buffs.all[buff_def.key]
            self.assertEqual(get_divert_consumed(fresh_buff), 0)
