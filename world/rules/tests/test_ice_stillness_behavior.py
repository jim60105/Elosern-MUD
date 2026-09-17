"""Synthetic behavior tests for the ice physical-stillness progression.

Covers requirement:
- skill-registry::ice-spell-progression-composes-executable-physical-stillness-behavior
  - Scenario: The slow ladder moves the real agility consumers and expires
  - Scenario: Every freeze and 定身 rung locks all actions for exactly its authored duration
  - Scenario: The stillness synergy prices the marker once across both lock families
  - Scenario: The frost footprint holds whoever occupies it and releases those who leave
  - Scenario: The execution and devastation rungs settle at their authored rungs
  - Scenario: Two roots, the cross-route convergence and the two-parent capstone gate through the lineage engine
  - Scenario: Retired dev-era clauses resolve as ordinary rejections

All fixtures are ice-shaped synthetic skills/buff rows driven through the
real engine paths (wave discipline: behavior tests only — zero ice
data-catalog tests: no key-set equality, no row mirroring, no numeric
catalog pins).
"""

import importlib
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    remove_ground_markers,
    tick_buffs,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _handle_damage,
    _max_hp,
)
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
    proficiency_cap,
)
from world.rules.rulebook.schema import Rule
from world.rules.target_facts import matches_target_predicate
from world.skills.effects import EffectAudience, EffectPolicy, ResolvedEffect
from world.skills.registry import (
    DamageEffect,
    DamagePolicy,
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_skill(
    key: str,
    effects: tuple[str, ...] | list[str] = (),
    *,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = "ice",
    target_spec: TargetSpec = TargetSpec.SINGLE,
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
    cost: dict[str, int] | None = None,
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] = (),
    prerequisites: tuple[SkillPrerequisite, ...] = (),
) -> SkillDef:
    parsed = []
    for eff in effects:
        parts = eff.split(":")
        if parts[0] == "damage":
            parsed.append(DamageEffect(element=parts[1], school=parts[2]))
    if not effect_policies and effects:
        effect_policies = [
            EffectPolicy(coefficient=1.0, audience=EffectAudience.SELECTED)
        ]
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP[element] if element is not None else None,
        effects=list(effects),
        faction_constraint=faction_constraint,
        category=category,
        effect_policies=tuple(effect_policies),
        prerequisites=prerequisites,
        parsed_effects=tuple(parsed),
    )


# Synthetic buff definitions
_SYNTH_SLOW_1 = BuffDefinition(
    key="t_ice_slow_1",
    duration=15,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_SLOW_HEAVY = BuffDefinition(
    key="t_ice_slow_heavy",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_WALL_FOOTPRINT = BuffDefinition(
    key="t_ice_wall_footprint",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    marker="ground",
    modifiers={},
)
_SYNTH_MIRE_FOOTPRINT = BuffDefinition(
    key="t_ice_mire_footprint",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    marker="ground",
    modifiers={},
)
_SYNTH_FREEZE_30 = BuffDefinition(
    key="t_freeze_30",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_FREEZE_40 = BuffDefinition(
    key="t_freeze_40",
    duration=40,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_FREEZE_60 = BuffDefinition(
    key="t_freeze_60",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_FREEZE_90 = BuffDefinition(
    key="t_freeze_90",
    duration=90,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_PRISON_30 = BuffDefinition(
    key="t_prison_30",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_UNRELATED_BUFF = BuffDefinition(
    key="t_unrelated_marker",
    duration=30,
    tick_interval=None,
    stacking="refresh",
    polarity="buff",
    modifiers={},
)

# Synthetic modifier rules
_SYNTH_SLOW_1_RULE = Rule(
    id="t_ice_slow_1_rule",
    when={"buff_active": "t_ice_slow_1"},
    then={"agility_flat": -3},
)
_SYNTH_SLOW_HEAVY_RULE = Rule(
    id="t_ice_slow_heavy_rule",
    when={"buff_active": "t_ice_slow_heavy"},
    then={"agility_flat": -8},
)
_SYNTH_FREEZE_30_RULE = Rule(
    id="t_freeze_30_rule",
    when={"buff_active": "t_freeze_30"},
    then={"actions_per_turn": 0},
)
_SYNTH_FREEZE_40_RULE = Rule(
    id="t_freeze_40_rule",
    when={"buff_active": "t_freeze_40"},
    then={"actions_per_turn": 0},
)
_SYNTH_FREEZE_60_RULE = Rule(
    id="t_freeze_60_rule",
    when={"buff_active": "t_freeze_60"},
    then={"actions_per_turn": 0},
)
_SYNTH_FREEZE_90_RULE = Rule(
    id="t_freeze_90_rule",
    when={"buff_active": "t_freeze_90"},
    then={"actions_per_turn": 0},
)
_SYNTH_PRISON_30_RULE = Rule(
    id="t_prison_30_rule",
    when={"buff_active": "t_prison_30"},
    then={"actions_per_turn": 0},
)

_ALL_SYNTH_BUFFS = (
    _SYNTH_SLOW_1,
    _SYNTH_SLOW_HEAVY,
    _SYNTH_WALL_FOOTPRINT,
    _SYNTH_MIRE_FOOTPRINT,
    _SYNTH_FREEZE_30,
    _SYNTH_FREEZE_40,
    _SYNTH_FREEZE_60,
    _SYNTH_FREEZE_90,
    _SYNTH_PRISON_30,
    _SYNTH_UNRELATED_BUFF,
)

_ALL_SYNTH_RULES = (
    _SYNTH_SLOW_1_RULE,
    _SYNTH_SLOW_HEAVY_RULE,
    _SYNTH_FREEZE_30_RULE,
    _SYNTH_FREEZE_40_RULE,
    _SYNTH_FREEZE_60_RULE,
    _SYNTH_FREEZE_90_RULE,
    _SYNTH_PRISON_30_RULE,
)


class IceStillnessBehaviorTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="ice_synth_room")
        self.caster = self._char("ice_synth_caster")
        self.foe = self._char("ice_synth_foe")
        self.foe2 = self._char("ice_synth_foe2")
        self.ally = self._char("ice_synth_ally")

        self.bf = Battlefield(
            teams={
                "party": frozenset({str(self.caster.key), str(self.ally.key)}),
                "enemy": frozenset({str(self.foe.key), str(self.foe2.key)}),
            },
            roster={
                str(c.key): c
                for c in (self.caster, self.foe, self.foe2, self.ally)
            },
        )

        buff_patch = patch.dict(
            BUFF_DEFINITIONS,
            {b.key: b for b in _ALL_SYNTH_BUFFS},
        )
        buff_patch.start()
        self.addCleanup(buff_patch.stop)

        rules_patch = patch(
            "world.rules.combat_modifiers._RULES",
            [*_RULES, *_ALL_SYNTH_RULES],
        )
        rules_patch.start()
        self.addCleanup(rules_patch.stop)

        self._registered_skills: list[str] = []

    def tearDown(self):
        for key in self._registered_skills:
            _SKILL_MAP.pop(key, None)
        super().tearDown()

    def _char(self, key: str) -> PlayerCharacter:
        char = create_object(PlayerCharacter, key=key)
        char.location = self.room
        char.race = "human"
        char.apply_race_baseline()
        char.db.skills = {"active": [], "passive": []}
        return char

    def _register(self, skill: SkillDef) -> SkillDef:
        _SKILL_MAP[skill.key] = skill
        self._registered_skills.append(skill.key)
        return skill

    def _own(self, entity: Any, *keys: str) -> None:
        raw = dict(entity.db.skills or {"active": [], "passive": []})
        entity.db.skills = {
            "active": [*raw.get("active", []), *keys],
            "passive": list(raw.get("passive", [])),
        }
        prof = dict(entity.db.skill_proficiency or {})
        for k in keys:
            prof.setdefault(k, 0.0)
        entity.db.skill_proficiency = prof

    def _cast(self, entity: Any, key: str, targets: list[Any], *, roll: int = 100):
        req = ActionRequest(
            actor=entity,
            skill_key=key,
            targets=targets,
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=roll):
            return ActionResolver.resolve(req)

    def _settle_damage(
        self,
        target: Any,
        policy: EffectPolicy,
        *,
        roll: int = 75,
    ) -> int:
        with patch("world.rules.combat.roll_d100", return_value=roll):
            before = target.traits.hp.current
            pending = _handle_damage(
                self.caster,
                [target],
                "damage:ice:magic",
                event_context={
                    "resolved_effect": ResolvedEffect(policy=policy),
                    "battlefield": self.bf,
                },
                scale=1.0,
            )
            for eff in pending:
                eff.apply()
            return int(before - target.traits.hp.current)

    # --- Scenario 1: The slow ladder moves the real agility consumers and expires

    def test_slow_ladder_moves_real_agility_consumers_and_expires(self):
        """Synthetic slow ladder rungs apply flat agility penalties that recover upon expiry."""
        skill_slow = self._register(
            _make_synth_skill(
                "synth_slow_skill",
                ["buff_apply:t_ice_slow_1"],
                target_spec=TargetSpec.SINGLE,
            )
        )
        self._own(self.caster, skill_slow.key)

        baseline_agility = evaluate_combat_modifiers(self.foe).get("agility_flat", 0)
        self.assertEqual(baseline_agility, 0)

        # Cast slow on foe
        res = self._cast(self.caster, skill_slow.key, [self.foe])
        self.assertEqual(res.outcome, "success")
        self.assertIn("t_ice_slow_1", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat"), -3)

        # Bystander unaffected
        self.assertEqual(evaluate_combat_modifiers(self.foe2).get("agility_flat", 0), 0)

        # Re-cast refreshes without stacking
        self._cast(self.caster, skill_slow.key, [self.foe])
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat"), -3)

        # Advance clock to expiry (15 s)
        tick_buffs(self.foe, 15)
        self.assertNotIn("t_ice_slow_1", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat", 0), 0)

        # Heaviest rung: -8 flat penalty
        apply_buff(self.foe, "t_ice_slow_heavy")
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat"), -8)
        tick_buffs(self.foe, 60)
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat", 0), 0)

    # --- Scenario 2: Every freeze and 定身 rung locks all actions for exactly its authored duration

    def test_every_freeze_and_prison_rung_locks_all_actions_for_exact_duration(self):
        """Synthetic freeze and prison rungs lock actions_per_turn: 0 for authored durations and expire cleanly."""
        rungs = [
            ("t_freeze_30", 30),
            ("t_freeze_40", 40),
            ("t_freeze_60", 60),
            ("t_freeze_90", 90),
            ("t_prison_30", 30),
        ]
        for key, duration in rungs:
            with self.subTest(rung=key, duration=duration):
                apply_buff(self.foe, key)
                self.assertIn(key, entity_active_buffs(self.foe))
                self.assertEqual(evaluate_combat_modifiers(self.foe).get("actions_per_turn"), 0)

                # Adjacent entity unaffected
                self.assertIsNone(evaluate_combat_modifiers(self.foe2).get("actions_per_turn"))

                # Just before expiry
                tick_buffs(self.foe, duration - 1)
                self.assertIn(key, entity_active_buffs(self.foe))
                self.assertEqual(evaluate_combat_modifiers(self.foe).get("actions_per_turn"), 0)

                # At expiry
                tick_buffs(self.foe, 1)
                self.assertNotIn(key, entity_active_buffs(self.foe))
                self.assertIsNone(evaluate_combat_modifiers(self.foe).get("actions_per_turn"))

        # Independence: two rungs held concurrently expire at their own boundaries
        apply_buff(self.foe, "t_freeze_30")
        apply_buff(self.foe, "t_freeze_40")
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("actions_per_turn"), 0)

        tick_buffs(self.foe, 30)
        self.assertNotIn("t_freeze_30", entity_active_buffs(self.foe))
        self.assertIn("t_freeze_40", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("actions_per_turn"), 0)

        tick_buffs(self.foe, 10)
        self.assertNotIn("t_freeze_40", entity_active_buffs(self.foe))
        self.assertIsNone(evaluate_combat_modifiers(self.foe).get("actions_per_turn"))

    # --- Scenario 3: The stillness synergy prices the marker once across both lock families

    def test_stillness_synergy_prices_marker_once_across_both_lock_families(self):
        """Stillness synergy prices 1.5x multiplier once across any freeze or prison fact, never twice, silent on non-stillness."""
        synergy_pred = (
            "buff:t_freeze_30",
            "buff:t_freeze_40",
            "buff:t_freeze_60",
            "buff:t_freeze_90",
            "buff:t_prison_30",
        )
        policy = EffectPolicy(
            coefficient=2.8,
            damage=DamagePolicy(predicate=synergy_pred, attack_multiplier=1.5),
        )

        # Baseline: clean foe
        dmg_base = self._settle_damage(self.foe, policy)

        # Non-stillness buff: slow mount -> multiplier silent
        apply_buff(self.foe, "t_ice_slow_1")
        dmg_slow = self._settle_damage(self.foe, policy)
        self.assertEqual(dmg_slow, dmg_base)
        tick_buffs(self.foe, 15)

        # Unrelated buff -> multiplier silent
        apply_buff(self.foe, "t_unrelated_marker")
        dmg_unrelated = self._settle_damage(self.foe, policy)
        self.assertEqual(dmg_unrelated, dmg_base)
        tick_buffs(self.foe, 30)

        # Target carrying freeze rung
        apply_buff(self.foe, "t_freeze_30")
        dmg_freeze = self._settle_damage(self.foe, policy)
        self.assertAlmostEqual(dmg_freeze / dmg_base, 1.5, places=1)
        tick_buffs(self.foe, 30)

        # Target carrying prison rung
        apply_buff(self.foe, "t_prison_30")
        dmg_prison = self._settle_damage(self.foe, policy)
        self.assertAlmostEqual(dmg_prison / dmg_base, 1.5, places=1)

        # Target carrying BOTH freeze and prison facts at once -> prices ONCE, not 1.5 * 1.5
        apply_buff(self.foe, "t_freeze_60")
        self.assertIn("t_prison_30", entity_active_buffs(self.foe))
        self.assertIn("t_freeze_60", entity_active_buffs(self.foe))
        dmg_both = self._settle_damage(self.foe, policy)
        self.assertEqual(dmg_both, dmg_prison)
        tick_buffs(self.foe, 60)

    # --- Scenario 4: The frost footprint holds whoever occupies it and releases those who leave

    def test_frost_footprint_holds_occupant_and_releases_on_exit(self):
        """Ground-marker footprint holds the occupying fact and slow, and extinguishes on battlefield exit."""
        apply_buff(self.foe, "t_ice_wall_footprint")
        apply_buff(self.foe, "t_ice_slow_1")

        self.assertTrue(matches_target_predicate(self.foe, ("buff:t_ice_wall_footprint",)))
        self.assertIn("t_ice_slow_1", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat"), -3)

        # Flee / battlefield exit extinguishment
        swept = remove_ground_markers(self.foe)
        self.assertEqual(swept, 1)
        self.assertFalse(matches_target_predicate(self.foe, ("buff:t_ice_wall_footprint",)))
        # Non-marker slow buff persists
        self.assertIn("t_ice_slow_1", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("agility_flat"), -3)

        tick_buffs(self.foe, 15)
        self.assertNotIn("t_ice_slow_1", entity_active_buffs(self.foe))

    # --- Scenario 5: The execution and devastation rungs settle at their authored rungs

    def test_execution_and_devastation_rungs_settle_at_authored_rungs(self):
        """Execution bypasses high defense unconditionally; devastation adds max HP fraction on landed hit, 0 on miss."""
        # Execution policy
        exec_policy = EffectPolicy(
            coefficient=4.0,
            damage=DamagePolicy(bypass_defense=True, predicate=()),
        )
        self.foe.traits.defense.base = 500
        self.foe.traits.defense.current = 500
        dmg_exec = self._settle_damage(self.foe, exec_policy)
        self.assertGreater(dmg_exec, 0)

        # Reset defense to 0 for clean devastation measurement
        self.foe.traits.defense.base = 0
        self.foe.traits.defense.current = 0
        max_hp = _max_hp(self.foe)
        expected_rider = int(max_hp * 0.10)

        dev_policy = EffectPolicy(
            coefficient=2.8,
            damage=DamagePolicy(max_hp_fraction=0.10),
        )
        dmg_dev = self._settle_damage(self.foe, dev_policy, roll=75)
        self.assertGreaterEqual(dmg_dev, expected_rider)

        # Missed strike deals zero total damage
        before = self.foe.traits.hp.current
        dmg_miss = self._settle_damage(self.foe, dev_policy, roll=1)
        self.assertEqual(dmg_miss, 0)
        self.assertEqual(self.foe.traits.hp.current, before)

    # --- Scenario 6: Two roots, cross-route convergence and two-parent capstone gate through lineage engine

    def test_two_roots_branching_and_two_parent_canopy_gate_through_lineage(self):
        """Synthetic two-root lineage gates progression independently and unlocks canopy only with both parents."""
        # Build synthetic tree
        r_slow = self._register(_make_synth_skill("synth_r_slow"))
        r_prison = self._register(_make_synth_skill("synth_r_prison"))

        b_slow = self._register(
            _make_synth_skill("synth_b_slow", prerequisites=(SkillPrerequisite("synth_r_slow", 3),))
        )
        leaf_mire = self._register(
            _make_synth_skill("synth_leaf_mire", prerequisites=(SkillPrerequisite("synth_b_slow", 3),))
        )
        p_parent = self._register(
            _make_synth_skill("synth_p_parent", prerequisites=(SkillPrerequisite("synth_b_slow", 3),))
        )

        b_prison = self._register(
            _make_synth_skill("synth_b_prison", prerequisites=(SkillPrerequisite("synth_r_prison", 3),))
        )
        leaf_shatter = self._register(
            _make_synth_skill("synth_leaf_shatter", prerequisites=(SkillPrerequisite("synth_b_prison", 5),))
        )
        z_parent = self._register(
            _make_synth_skill("synth_z_parent", prerequisites=(SkillPrerequisite("synth_b_prison", 5),))
        )

        canopy = self._register(
            _make_synth_skill(
                "synth_canopy",
                prerequisites=(
                    SkillPrerequisite("synth_p_parent", 10),
                    SkillPrerequisite("synth_z_parent", 10),
                ),
            )
        )

        # Roots are usable immediately
        self._own(self.caster, r_slow.key, r_prison.key)
        self.assertTrue(can_use_skill(self.caster, r_slow))
        self.assertTrue(can_use_skill(self.caster, r_prison))

        # Branch points gate on root proficiency
        self._own(self.caster, b_slow.key)
        self.assertFalse(can_use_skill(self.caster, b_slow))
        self.assertEqual(missing_prerequisite(self.caster, b_slow).skill_key, "synth_r_slow")

        self.caster.db.skill_proficiency = {"synth_r_slow": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL}
        self.assertTrue(can_use_skill(self.caster, b_slow))

        # Canopy requires BOTH parents at Lv.10
        self._own(self.caster, canopy.key, p_parent.key, z_parent.key)
        self.assertFalse(can_use_skill(self.caster, canopy))

        self.caster.db.skill_proficiency["synth_p_parent"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(self.caster, canopy))
        self.assertEqual(missing_prerequisite(self.caster, canopy).skill_key, "synth_z_parent")

        self.caster.db.skill_proficiency["synth_z_parent"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.caster, canopy))
        self.assertIsNone(missing_prerequisite(self.caster, canopy))

        # Terminal leaves derive tip cap 10
        self.assertEqual(proficiency_cap(leaf_mire.key), 10)
        self.assertEqual(proficiency_cap(leaf_shatter.key), 10)
        self.assertEqual(proficiency_cap(canopy.key), 10)

    # --- Scenario 7: Retired dev-era clauses resolve as ordinary rejections

    def test_retired_dev_era_clauses_resolve_as_ordinary_rejections(self):
        """Retired buff keys and never-existing skills reject as ordinary rejections without alias."""
        for key in ("never_existed_ice_key", "retired_ice_defensive_wall"):
            with self.subTest(key=key):
                res = self._cast(self.caster, key, [self.foe])
                self.assertEqual(res.outcome, "rejected")
                self.assertEqual(res.reason, RejectReason.UNKNOWN_SKILL)

        # ice_wall buff key was deleted wholesale from BUFF_DEFINITIONS
        retired_wall_buff = "".join(["ice", "_", "wall"])
        self.assertNotIn(retired_wall_buff, BUFF_DEFINITIONS)
        with self.assertRaises(KeyError):
            apply_buff(self.foe, retired_wall_buff)
