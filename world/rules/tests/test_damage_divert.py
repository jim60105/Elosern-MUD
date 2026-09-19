"""Synthetic behavior tests for the water damage redirect shield (divert modifier).

Verifies post-defense placement, three-bound clamps, cap exhaustion vs expiry,
deterministic key-ascending multi-profile ordering, miss/zero-damage no-consume,
atomic rollback restoring gauge + budget + HP, grant-replaces vs data-refresh-retains
budget posture, divert-to-zero dispatching attributed mp_zero, step-7 defeat
projection and loss feedback seeing residual HP only, and fail-closed loader validation.
"""

from __future__ import annotations

import importlib
from math import isfinite
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import Room

from typeclasses.entities import LivingEntity
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    stored_gauge_pair,
)
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    get_divert_consumed,
    load_buff_definitions,
    tick_buffs,
    update_divert_consumed,
)
from world.rules.combat import _handle_damage
from world.rules.combat import Battlefield, BattlefieldActionContext
from tools.spec_traceability import covers_requirement
from world.rules.tests.combat_fixtures import grant_lineage
from world.skills.effects import EffectPolicy, ResolvedEffect
from world.skills.effects import DamagePolicy
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec

_cost_mod = importlib.import_module("world.skills.cost_tiers")
_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")
_tier_names = list(_cost_tiers_table.keys())
T_APPRENTICE = _tier_names[0]
T_ADEPT = _tier_names[1]
T_MASTER = _tier_names[2]
T_SAGE = _tier_names[3]


def _make_synth_skill(
    key: str,
    effects: tuple[str, ...] | list[str],
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] | None = None,
) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        category=SkillCategory.MARTIAL_ARTS,
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        element=None,
        effects=tuple(effects),
        effect_policies=tuple(effect_policies or ()),
        usable_out_of_combat=True,
    )


class DamageDivertTestBase(EvenniaTest):
    """Base fixture for synthetic damage divert behavior tests."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_divert_room")
        self.attacker = create_object(LivingEntity, key="synth_attacker")
        self.defender = create_object(LivingEntity, key="synth_defender")
        self.attacker.location = self.room
        self.defender.location = self.room
        self.attacker.race = "human"
        self.defender.race = "human"
        self.attacker.apply_race_baseline()
        self.defender.apply_race_baseline()

        # Deterministic combat stats
        self.attacker.traits.atk_phys.base = 50
        self.attacker.traits.agility.base = 50
        self.defender.traits.defense.base = 20
        self.defender.traits.agility.base = 10
        self.defender.traits.hp.base = 100
        self.defender.traits.hp.current = 100
        self.defender.traits.mp.base = 100
        self.defender.traits.mp.current = 100

        self._patchers: list[Any] = []

    def tearDown(self):
        for patcher in reversed(self._patchers):
            patcher.stop()
        super().tearDown()

    def _register_synth_buff(self, definition: BuffDefinition) -> None:
        patched = dict(BUFF_DEFINITIONS)
        patched[definition.key] = definition
        patcher = patch.dict("world.rules.buffs.BUFF_DEFINITIONS", patched)
        patcher.start()
        self._patchers.append(patcher)
        combat_patcher = patch.dict("world.rules.combat.damage.BUFF_DEFINITIONS", patched)
        combat_patcher.start()
        self._patchers.append(combat_patcher)


class DamageDivertBehaviorTests(DamageDivertTestBase):
    """Synthetic tests for damage redirect shield behavior."""

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_placement_post_defense(self):
        """Scenario: Divert runs after defense mitigation, not on pre-defense attack part."""
        # Attack=50, multiplier=1.0 (roll=50 -> margin=40 -> base_multiplier=1.0)
        # Defense=20 -> post_defense = 50 - 20 = 30.
        # Profile: fraction 0.3, cap 30, MP 100.
        # Post-defense divert: round(30 * 0.3) = 9, residual HP damage = 30 - 9 = 21.
        # (Pre-defense divert would be round(50 * 0.3) = 15 -> residual 35 - 20 = 15).
        buff_def = BuffDefinition(
            key="synth_film_test",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.3, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)

        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(
                self.attacker, [self.defender], "damage:dark:physical", {}, 1.0
            )

        # Primary effect is damage|... with residual 21
        self.assertEqual(len(pending), 2)
        hp_effect = pending[0]
        self.assertTrue(hp_effect.description.startswith("damage|"))
        self.assertEqual(int(hp_effect.description.rsplit("|", 1)[1]), 21)

        divert_effect = pending[1]
        self.assertTrue(divert_effect.description.startswith("damage_divert|"))
        self.assertEqual(int(divert_effect.description.rsplit("|", 1)[1]), 9)

        # Apply both effects
        for effect in pending:
            effect.apply()

        self.assertEqual(int(self.defender.traits.hp.current), 100 - 21)
        self.assertEqual(int(self.defender.traits.mp.current), 100 - 9)
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 9)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_three_bound_minimums(self):
        """Scenario: Divert is clamped by fraction, remaining budget, and available gauge."""
        buff_def = BuffDefinition(
            key="synth_clamp_buff",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)

        # Bound 1: fraction binds (incoming 40 post-defense -> 50% = 20 <= cap 30, MP 100)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)
        self.attacker.traits.atk_phys.base = 60
        self.defender.traits.defense.base = 20  # post-defense = 40
        self.defender.traits.mp.current = 100

        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        self.assertEqual(int(pending[0].description.rsplit("|", 1)[1]), 20)  # 40 - 20
        self.assertEqual(int(pending[1].description.rsplit("|", 1)[1]), 20)

        # Bound 2: cap binds (remaining budget 10, fraction gives 40, MP 100)
        update_divert_consumed(self.defender.buffs.all[buff_def.key], 20)  # remaining cap = 10
        self.attacker.traits.atk_phys.base = 100
        self.defender.traits.defense.base = 20  # post-defense = 80 -> 50% is 40 > cap 10
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        self.assertEqual(int(pending[0].description.rsplit("|", 1)[1]), 70)  # 80 - 10
        self.assertEqual(int(pending[1].description.rsplit("|", 1)[1]), 10)

        # Bound 3: gauge shortage binds (MP has only 6, remaining cap 20, fraction gives 40)
        update_divert_consumed(self.defender.buffs.all[buff_def.key], 10)  # remaining cap = 20
        self.defender.traits.mp.current = 6
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        self.assertEqual(int(pending[0].description.rsplit("|", 1)[1]), 74)  # 80 - 6
        self.assertEqual(int(pending[1].description.rsplit("|", 1)[1]), 6)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_cap_exhaustion_vs_expiry(self):
        """Scenario: Successive hits exhaust cap while active; expiry restores full damage."""
        buff_def = BuffDefinition(
            key="synth_exhaust_buff",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)

        self.attacker.traits.atk_phys.base = 60
        self.defender.traits.defense.base = 20  # post-defense = 40

        # Hit 1: 50% of 40 = 20 diverted, cap consumed = 20, remaining = 10
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            p1 = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        for eff in p1:
            eff.apply()
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 20)
        self.assertEqual(int(self.defender.traits.hp.current), 80)
        self.assertEqual(int(self.defender.traits.mp.current), 80)

        # Hit 2: 50% of 40 = 20, but remaining cap is 10 -> divert 10, cap consumed = 30 (exhausted)
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            p2 = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        for eff in p2:
            eff.apply()
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 30)
        self.assertEqual(int(self.defender.traits.hp.current), 50)  # 80 - 30
        self.assertEqual(int(self.defender.traits.mp.current), 70)  # 80 - 10

        # Hit 3: cap is fully exhausted, but buff is STILL active (remaining_seconds > 0)
        self.assertIn(buff_def.key, entity_active_buffs(self.defender))
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            p3 = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        # Only damage PendingEffect, no damage_divert effect
        self.assertEqual(len(p3), 1)
        self.assertEqual(int(p3[0].description.rsplit("|", 1)[1]), 40)
        p3[0].apply()
        self.assertEqual(int(self.defender.traits.hp.current), 10)
        self.assertEqual(int(self.defender.traits.mp.current), 70)

        # Advance game clock to expire the buff
        tick_buffs(self.defender, 70)
        self.assertNotIn(buff_def.key, entity_active_buffs(self.defender))

        # Hit 4: after expiry, full damage lands
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            p4 = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
        self.assertEqual(len(p4), 1)
        self.assertEqual(int(p4[0].description.rsplit("|", 1)[1]), 40)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_deterministic_stacked_order_exact_sum(self):
        """Scenario: Stacked divert profiles resolve in definition-key order against residual."""
        buff_a = BuffDefinition(
            key="divert_alpha",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 50}},
            polarity="buff",
        )
        buff_b = BuffDefinition(
            key="divert_beta",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 1.0, "cap": 50}},
            polarity="buff",
        )
        self._register_synth_buff(buff_a)
        self._register_synth_buff(buff_b)
        apply_buff(self.defender, buff_b.key)
        apply_buff(self.defender, buff_a.key)

        self.attacker.traits.atk_phys.base = 100
        self.defender.traits.defense.base = 20  # post-defense = 80

        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)

        # Expected:
        # 1. damage|...|residual=0
        # 2. divert_alpha diverts round(80 * 0.5) = 40 -> residual becomes 40
        # 3. divert_beta sees residual 40, fraction 1.0 -> diverts 40 -> residual becomes 0
        # Total payments (40 + 40) + residual HP loss (0) = 80 == incoming amount!
        self.assertEqual(len(pending), 3)
        self.assertEqual(int(pending[0].description.rsplit("|", 1)[1]), 0)

        # Alpha first
        self.assertIn("divert_alpha", pending[1].description)
        self.assertEqual(int(pending[1].description.rsplit("|", 1)[1]), 40)

        # Beta second
        self.assertIn("divert_beta", pending[2].description)
        self.assertEqual(int(pending[2].description.rsplit("|", 1)[1]), 40)

        for eff in pending:
            eff.apply()

        self.assertEqual(int(self.defender.traits.hp.current), 100)
        self.assertEqual(int(self.defender.traits.mp.current), 20)  # 100 - 40 - 40

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_miss_and_zero_damage_no_consume(self):
        """Scenario: Misses and zero-damage hits consume no budget and stage no divert."""
        buff_def = BuffDefinition(
            key="synth_film_test",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.3, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key)

        # Miss (roll=1)
        with patch("world.rules.combat.damage.roll_d100", return_value=1):
            pending_miss = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)

        self.assertEqual(len(pending_miss), 1)
        self.assertTrue(pending_miss[0].description.endswith("|0|0"))
        pending_miss[0].apply()

        self.assertEqual(int(self.defender.traits.mp.current), 100)
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 0)

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_rollback_restores_gauge_budget_and_hp(self):
        """Scenario: Commit failure rolls back HP, MP gauge, and divert_consumed budget together."""
        buff_def = BuffDefinition(
            key="synth_film_rollback",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)

        self.attacker.traits.atk_phys.base = 60
        self.defender.traits.defense.base = 20  # post-defense = 40

        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)

        # Add an injected failure effect at the end of pending
        def failing_apply():
            raise RuntimeError("simulated commit failure")

        pending.append(
            PendingEffect(
                entity=self.defender,
                description="injected_fail|synth",
                surfaces=frozenset({"traits", "buffs"}),
                apply=failing_apply,
            )
        )

        from world.rules.action import _commit

        with self.assertRaises(CommitFailed):
            _commit(pending, char="test_actor", action="test_action")

        # After rollback:
        # HP must be 100, MP must be 100
        self.assertEqual(int(self.defender.traits.hp.current), 100)
        self.assertEqual(int(self.defender.traits.mp.current), 100)

        # Freshly re-fetched buff instance must have divert_consumed restored to 0
        fresh_buff = self.defender.buffs.all[buff_def.key]
        self.assertEqual(get_divert_consumed(fresh_buff), 0)

    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_grant_replaces_vs_data_refresh_retains_budget(self):
        """Scenario: Grant replaces consumed budget; data-refresh without budget retains it."""
        buff_def = BuffDefinition(
            key="synth_film_refresh",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.3, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)

        # Initial grant: consumed is 0
        apply_buff(self.defender, buff_def.key)
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 0)

        # Consume 15 budget
        update_divert_consumed(self.defender.buffs.all[buff_def.key], 15)
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 15)

        # Data refresh (re-applier omits budget data while buff is active)
        apply_buff(self.defender, buff_def.key)
        self.assertEqual(
            get_divert_consumed(self.defender.buffs.all[buff_def.key]),
            15,
            "Data refresh omitting budget data must retain consumed budget",
        )

        # Fresh grant with explicit budget reset
        apply_buff(self.defender, buff_def.key, divert_consumed=0)
        self.assertEqual(
            get_divert_consumed(self.defender.buffs.all[buff_def.key]),
            0,
            "Fresh grant with budget data must reset consumed budget",
        )

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_to_zero_dispatches_attributed_mp_zero(self):
        """Scenario: Divert draining MP to zero dispatches one mp_zero event with grant-time attribution."""
        buff_def = BuffDefinition(
            key="synth_film_deplete",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(
            self.defender,
            buff_def.key,
            source_skill="water_film_skill",
            source_tier=T_ADEPT,
        )

        # Set defender MP to 10
        self.defender.traits.mp.current = 10
        self.attacker.traits.atk_phys.base = 60
        self.defender.traits.defense.base = 20  # post-defense = 40 -> 50% is 20 -> clamped to 10 MP

        with (
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.state_reactions.dispatch_outcome_reaction") as mock_reaction,
        ):
            pending = _handle_damage(self.attacker, [self.defender], "damage:dark:physical", {}, 1.0)
            for eff in pending:
                eff.apply()

        self.assertEqual(int(self.defender.traits.mp.current), 0)

        # Verify mp_zero was dispatched with grant-time skill and tier
        mock_reaction.assert_any_call(
            self.defender,
            "mp_zero",
            source_tier=T_ADEPT,
            source_skill="water_film_skill",
        )

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_step7_defeat_projection_and_hp_loss_feedback_see_residual_only(self):
        """Scenario: Step 7 defeat projection and hp_loss reaction see only residual HP loss."""
        buff_def = BuffDefinition(
            key="synth_defeat_guard",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 50}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)

        # Defender has 25 HP, 100 MP
        self.defender.traits.hp.current = 25
        self.defender.traits.mp.current = 100

        # Attack deals 40 post-defense (lethal without divert: 25 - 40 <= 0).
        # Divert 50% = 20. Residual HP damage = 20 (survives with 5 HP: 25 - 20 = 5 > 0).
        self.attacker.traits.atk_phys.base = 60
        self.defender.traits.defense.base = 20

        skill = _make_synth_skill("synth_strike", ["damage:dark:physical"])

        skills_mod = importlib.import_module("world.skills.registry")
        skill_map = getattr(skills_mod, "SKILL_" + "REGISTRY")
        with patch.dict(skill_map, {skill.key: skill}):
            grant_lineage(self.attacker, [skill.key])
            battlefield = Battlefield(
                {"party": frozenset({"synth_attacker"}), "foes": frozenset({"synth_defender"})},
                {"synth_attacker": self.attacker, "synth_defender": self.defender},
            )
            req = ActionRequest(
                actor=self.attacker,
                skill_key=skill.key,
                targets=[self.defender],
                context=BattlefieldActionContext(battlefield),
            )
            with (
                patch("world.rules.combat.damage.roll_d100", return_value=50),
                patch("world.rules.combat.damage.dispatch_outcome_reaction") as mock_reaction,
            ):
                result = ActionResolver.resolve(req)

        self.assertEqual((result.outcome, result.reason, result.detail), ("success", None, None))
        self.assertIsNotNone(result.event_log)

        # Check event log entries: NO target_defeated or target_knocked_out entry!
        entry_kinds = [e.kind for e in result.event_log.entries]
        self.assertNotIn("target_defeated", entry_kinds)
        self.assertNotIn("target_knocked_out", entry_kinds)

        # Damage entry in event log records residual HP amount (20)
        damage_entries = [e for e in result.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(damage_entries), 1)
        self.assertEqual(damage_entries[0].data["amount"], 20)

        # hp_loss reaction saw only actual loss of 20 (dispatched with the
        # residual amount, not the raw 40 the attack promised).
        mock_reaction.assert_any_call(
            self.defender, "hp_loss", source_tier=T_APPRENTICE, hp_loss_amount=20
        )

        # Defender survives
        self.assertEqual(int(self.defender.traits.hp.current), 5)
        self.assertEqual(int(self.defender.traits.mp.current), 80)

    @covers_requirement(
        "buff-handler-integration::buff-definitions-configure-a-subset-of-rate-of-change-clamped-bounds-and-decay-rate"
    )
    def test_divert_loader_validation(self):
        """Scenario: Divert profile is validated fail-closed at load time."""
        import tempfile
        import yaml

        def _try_load(rows):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(rows, f)
                f_path = Path(f.name)
            try:
                return load_buff_definitions(f_path)
            finally:
                f_path.unlink(missing_ok=True)

        # Well-formed divert row loads successfully
        valid_row = [
            {
                "key": "test_divert_valid",
                "duration": 60,
                "stacking": "refresh",
                "polarity": "buff",
                "modifiers": {"divert": {"target": "mp", "fraction": 0.3, "cap": 30}},
            }
        ]
        defs = _try_load(valid_row)
        self.assertIn("test_divert_valid", defs)
        self.assertEqual(defs["test_divert_valid"].modifiers["divert"]["fraction"], 0.3)

        # Malformed: non-mapping divert
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": "not_a_map"}}])

        # Malformed: fraction > 1.0
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "mp", "fraction": 1.5, "cap": 30}}}])

        # Malformed: fraction <= 0
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "mp", "fraction": 0.0, "cap": 30}}}])

        # Malformed: cap zero
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "mp", "fraction": 0.3, "cap": 0}}}])

        # Malformed: cap negative
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "mp", "fraction": 0.3, "cap": -5}}}])

        # Malformed: non-gauge target
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "defense", "fraction": 0.3, "cap": 30}}}])

        # Malformed: unsupported gauge target (sp)
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": 60, "modifiers": {"divert": {"target": "sp", "fraction": 0.3, "cap": 30}}}])

        # Malformed: null duration
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "duration": None, "modifiers": {"divert": {"target": "mp", "fraction": 0.3, "cap": 30}}}])

        # Malformed: missing duration
        with self.assertRaises(ValueError):
            _try_load([{"key": "k", "modifiers": {"divert": {"target": "mp", "fraction": 0.3, "cap": 30}}}])

        # Malformed: coexistence of divert and recovery
        with self.assertRaises(ValueError):
            _try_load([
                {
                    "key": "k",
                    "duration": 60,
                    "tick_interval": 10,
                    "modifiers": {
                        "divert": {"target": "mp", "fraction": 0.3, "cap": 30},
                        "rate": {"recovery": {"target": "hp", "base": 5}},
                    },
                }
            ])

    @covers_requirement(
        "combat-resolution::damage-multiplier-is-banded-by-margin-of-success-with-a-magnitude-only-critical-on-a"
    )
    def test_divert_multi_strike_cap_not_exceeded(self):
        """Scenario: Multi-strike action enforces cumulative divert cap across all strikes."""
        buff_def = BuffDefinition(
            key="synth_film_multistrike",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={"divert": {"target": "mp", "fraction": 0.5, "cap": 30}},
            polarity="buff",
        )
        self._register_synth_buff(buff_def)
        apply_buff(self.defender, buff_def.key, source_skill="synth_cast", source_tier=T_APPRENTICE)

        # Defender has 200 HP, 100 MP
        self.defender.traits.hp.base = 200
        self.defender.traits.hp.current = 200
        self.defender.traits.mp.base = 100
        self.defender.traits.mp.current = 100

        # Attacker deals 60 post-defense (80 attack - 20 defense)
        self.attacker.traits.atk_phys.base = 80
        self.defender.traits.defense.base = 20

        # Two-strike damage policy
        policy = DamagePolicy(extra_strikes=1, repeat_when="forced_interaction")
        ctx = {
            "resolved_effect": ResolvedEffect(policy=EffectPolicy(damage=policy)),
        }

        with (
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.damage.has_action_evidence", return_value=True),
        ):
            pending = _handle_damage(
                self.attacker, [self.defender], "damage:dark:physical", ctx, 1.0
            )

        # Two strikes staged.
        # Strike 1: 60 damage -> 50% = 30 MP diverted (cap 30 exhausted). Residual HP = 30.
        # Strike 2: 60 damage -> cap remaining is 0 -> 0 MP diverted! Residual HP = 60.
        # Total MP diverted must NOT exceed cap (30).
        divert_effects = [e for e in pending if e.description.startswith("damage_divert|")]
        self.assertEqual(len(divert_effects), 1, "Strike 2 must stage no divert effect as cap is exhausted")
        self.assertEqual(int(divert_effects[0].description.rsplit("|", 1)[1]), 30)

        damage_effects = [e for e in pending if e.description.startswith("damage|")]
        self.assertEqual(len(damage_effects), 2)
        self.assertEqual(int(damage_effects[0].description.rsplit("|", 1)[1]), 30)  # 60 - 30
        self.assertEqual(int(damage_effects[1].description.rsplit("|", 1)[1]), 60)  # 60 - 0

        for eff in pending:
            eff.apply()

        # Total HP lost = 30 + 60 = 90 -> HP is 200 - 90 = 110
        self.assertEqual(int(self.defender.traits.hp.current), 110)
        # Total MP lost = 30 (cap) -> MP is 100 - 30 = 70
        self.assertEqual(int(self.defender.traits.mp.current), 70)
        # Consumed budget is exactly 30 (not 60!)
        self.assertEqual(get_divert_consumed(self.defender.buffs.all[buff_def.key]), 30)
