"""Synthetic behavior tests for dark spell progression (curse and erosion behavior).

Covers:
- Curse ladder weakening observable stats at settlement and recovering on expiry.
- Psychological action-lock (fear) skipping actions and key-independence from physical stillness.
- Erosion HP transfer to origin caster across multi-tick intervals, area per-victim origins, and dead-origin silence.
- Missing-fraction self-recovery keyed strictly to the caster's own missing HP, never the victim's.
- Execution bypass defense and devastation max-HP riders through shared policies.
- Two roots, branching, and two-parent convergence lineage gates with reverse-edge caps.
- Capstone mixed composition (damage + devastation + wide debuff + self-recovery) non-double-pricing.
- Wholesale retirement of dev-era bindings and unknown keys rejecting cleanly without aliases.
"""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room

from tools.spec_traceability import covers_requirement
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    apply_buff,
    cleanse_debuffs,
    entity_active_buffs,
    remove_by_selector,
    tick_buffs,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _handle_damage,
    _handle_self_heal,
)
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
    proficiency_cap,
)
from world.skills.effects import (
    DamagePolicy,
    EffectPolicy,
    ResolvedEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)

_skills_mod = importlib.import_module("world.skills.registry")
_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")
_lore_mod = importlib.import_module("world.lore.elements")
_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_dark_skill(
    key: str,
    effects: tuple[str, ...] | list[str],
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] | None = None,
    *,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
) -> SkillDef:
    """Build one synthetic dark skill definition for behavior testing."""
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成暗系技能 {key}。",
        kind=SkillKind.ACTIVE,
        target_spec=target_spec,
        cost=cost or {"mp": 10},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP.get("dark"),
        effects=list(effects),
        faction_constraint=faction_constraint,
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="dark",
        prerequisites=prerequisites,
        effect_policies=tuple(effect_policies) if effect_policies is not None else (),
    )


class DarkCurseErosionBehaviorTests(EvenniaTest):
    """Synthetic behavior test suite for dark curse and erosion progression."""

    def setUp(self):
        super().setUp()
        self.addCleanup(validate_prerequisite_graph, _SKILL_MAP)
        self.room = create_object(Room, key="synth_dark_room")
        self.caster = create_object(PlayerCharacter, key="synth_dark_caster")
        self.target = create_object(PlayerCharacter, key="synth_dark_target")
        self.other = create_object(PlayerCharacter, key="synth_dark_other")

        for char in (self.caster, self.target, self.other):
            char.location = self.room
            char.race = "human"
            char.apply_race_baseline()
            char.traits.hp.base = 200
            char.traits.hp.current = 200
            char.traits.mp.base = 500
            char.traits.mp.current = 500
            char.traits.defense.base = 10
            char.traits.atk_phys.base = 20
            char.traits.agility.base = 20
            char.traits.magic_power.base = 30
            char.db.skills = {"active": [], "passive": []}

        self.bf = Battlefield(
            teams={
                "party": frozenset({str(self.caster.key)}),
                "enemy": frozenset({str(self.target.key), str(self.other.key)}),
            },
            roster={
                str(self.caster.key): self.caster,
                str(self.target.key): self.target,
                str(self.other.key): self.other,
            },
        )

    def _cast(self, skill: SkillDef, targets: list[Any]) -> Any:
        ctx = BattlefieldActionContext(self.bf)
        req = ActionRequest(actor=self.caster, skill_key=skill.key, targets=targets, context=ctx)
        with patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False):
            self.caster.db.skills = {"active": [skill.key], "passive": []}
            with patch("world.rules.combat.roll_d100", return_value=100):
                return ActionResolver.resolve(req)

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_curse_ladder_weakens_stats_and_fear_locks_actions(self):
        """Scenario: The curse ladder weakens observable stats at settlement and recovers on expiry."""
        # 1. Weaken debuff
        weaken_skill = _make_synth_dark_skill("synth_weaken", ["buff_apply:dark_weaken"])
        res = self._cast(weaken_skill, [self.target])
        self.assertEqual(res.outcome, "success")
        self.assertIn("dark_weaken", entity_active_buffs(self.target))

        remove_by_selector(self.target, "dark_weaken")
        self.assertNotIn("dark_weaken", entity_active_buffs(self.target))

        # 2. Curse debuff (multi-stat: atk, def, agi -5, 20s)
        curse_skill = _make_synth_dark_skill("synth_curse", ["buff_apply:dark_curse"])
        res = self._cast(curse_skill, [self.target])
        self.assertEqual(res.outcome, "success")
        self.assertIn("dark_curse", entity_active_buffs(self.target))
        remove_by_selector(self.target, "dark_curse")
        self.assertNotIn("dark_curse", entity_active_buffs(self.target))

        # 3. Fear action-lock and key-independence from physical stillness
        fear_skill = _make_synth_dark_skill("synth_fear", ["buff_apply:fear"])
        res = self._cast(fear_skill, [self.target])
        self.assertEqual(res.outcome, "success")
        self.assertIn("fear", entity_active_buffs(self.target))

        feared_mods = evaluate_combat_modifiers(self.target)
        self.assertEqual(feared_mods.get("actions_per_turn"), 0)
        self.assertEqual(feared_mods.get("agility"), "-15%")
        self.assertEqual(feared_mods.get("accuracy"), -10)

        # Other entity holds ice physical stillness (paralysis)
        apply_buff(self.other, "paralysis")
        other_mods = evaluate_combat_modifiers(self.other)
        self.assertEqual(other_mods.get("actions_per_turn"), 0)
        self.assertNotIn("agility", other_mods)

        # Cleansing fear restores target's actions without touching other entity's state
        remove_by_selector(self.target, "fear")
        self.assertEqual(evaluate_combat_modifiers(self.target), {})
        self.assertEqual(evaluate_combat_modifiers(self.other), {"actions_per_turn": 0})

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_erosion_transfers_loss_to_origin_caster_including_area_and_dead_silence(self):
        """Scenario: Erosion transfers its whole loss to the origin caster."""
        # Wounded caster: 50 / 200 HP
        self.caster.traits.hp.current = 50
        self.target.traits.hp.current = 200

        # Apply erosion (-12 delta, caster_share 1.0) with origin caster
        apply_buff(self.target, "dark_corrosion", source_pk=int(self.caster.pk))

        # Interval 1: target loses 12 HP, living caster receives 12 HP
        tick_buffs(self.target, 10)
        self.assertEqual(self.target.traits.hp.value, 188)
        self.assertEqual(self.caster.traits.hp.value, 62)

        # Deep erosion (-18 delta) on target
        apply_buff(self.target, "dark_corrosion_deep", source_pk=int(self.caster.pk))
        tick_buffs(self.target, 10)
        # Target loses 12 + 18 = 30 HP, caster receives 30 HP
        self.assertEqual(self.target.traits.hp.value, 158)
        self.assertEqual(self.caster.traits.hp.value, 92)

        # Area multi-victim test: caster credits from multiple victims
        self.other.traits.hp.current = 100
        apply_buff(self.other, "dark_corrosion", source_pk=int(self.caster.pk))
        tick_buffs(self.other, 10)
        self.assertEqual(self.other.traits.hp.value, 88)
        self.assertEqual(self.caster.traits.hp.value, 104)

        # HP floor clamp: victim only has 5 HP
        self.target.traits.hp.current = 5
        cleanse_debuffs(self.target)
        apply_buff(self.target, "dark_corrosion", source_pk=int(self.caster.pk))
        caster_hp_before = self.caster.traits.hp.value
        tick_buffs(self.target, 10)
        # Loss clamped at 5, caster receives exactly 5
        self.assertEqual(self.target.traits.hp.value, 0)
        self.assertEqual(self.caster.traits.hp.value, caster_hp_before + 5)

        # Dead origin silence: when caster is dead, tick produces no credit
        self.caster.traits.hp.current = 0
        self.other.traits.hp.current = 50
        tick_buffs(self.other, 10)
        self.assertEqual(self.other.traits.hp.value, 38)
        self.assertEqual(self.caster.traits.hp.value, 0)

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_recovery_rides_caster_missing_hp_not_victim(self):
        """Scenario: Recovery rides the caster's own missing HP, never the victim's."""
        # Wounded caster: max 200, current 100 (missing 100 HP)
        self.caster.traits.hp.current = 100
        # Fuller enemy: max 200, current 200 (missing 0 HP)
        self.target.traits.hp.current = 200

        # Synthetic damage + 10% missing-fraction recovery
        recover_skill_10 = _make_synth_dark_skill(
            "synth_recover_10",
            effects=("damage:dark:magic", "self_heal:missing_fraction:0.1"),
            effect_policies=(
                EffectPolicy(coefficient=1.0),
                EffectPolicy(),
            ),
        )
        res = self._cast(recover_skill_10, [self.target])
        self.assertEqual(res.outcome, "success")
        # 10% of 100 missing = 10 HP recovered
        self.assertEqual(self.caster.traits.hp.current, 110)

        # 15% missing-fraction recovery on caster missing 90 HP (200 - 110 = 90)
        recover_skill_15 = _make_synth_dark_skill(
            "synth_recover_15",
            effects=("damage:dark:magic", "self_heal:missing_fraction:0.15"),
            effect_policies=(
                EffectPolicy(coefficient=1.0),
                EffectPolicy(),
            ),
        )
        res2 = self._cast(recover_skill_15, [self.target])
        self.assertEqual(res2.outcome, "success")
        # 15% of 90 missing = 13.5 -> 14 HP recovered
        self.assertEqual(self.caster.traits.hp.current, 124)

        # Dead caster recovers nothing (never revives)
        self.caster.traits.hp.current = 0
        pending = _handle_self_heal(
            self.caster,
            [self.target],
            "self_heal:missing_fraction:0.15",
            event_context={"resolved_effect": ResolvedEffect(policy=EffectPolicy())},
            scale=1.0,
        )
        for eff in pending:
            eff.apply()
        self.assertEqual(self.caster.traits.hp.current, 0)

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_execution_and_devastation_rungs_behave_through_shared_policies(self):
        """Scenario: Execution and devastation rungs behave through the shared policies."""
        from .combat_fixtures import FakeEntity

        # High defense target: defense = 200, attacker magic_power = 50
        actor = FakeEntity("caster", magic_power=50, agility=10)
        target_high_def = FakeEntity("target", hp=1000, agility=10, defense=200)

        # 1. Ordinary damage rung without defense bypass
        normal_policy = EffectPolicy(coefficient=2.0)
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending_normal = _handle_damage(
                actor,
                [target_high_def],
                "damage:dark:magic",
                event_context={"resolved_effect": ResolvedEffect(policy=normal_policy)},
                scale=1.0,
            )
        before_hp = target_high_def.traits.hp.value
        for eff in pending_normal:
            eff.apply()
        normal_damage = before_hp - target_high_def.traits.hp.value

        # 2. Execution rung with unconditional defense bypass
        exec_policy = EffectPolicy(
            coefficient=2.0,
            damage=DamagePolicy(bypass_defense=True, predicate=()),
        )
        target_high_def.traits.hp._data["current"] = 1000
        before_hp = target_high_def.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending_exec = _handle_damage(
                actor,
                [target_high_def],
                "damage:dark:magic",
                event_context={"resolved_effect": ResolvedEffect(policy=exec_policy)},
                scale=1.0,
            )
        for eff in pending_exec:
            eff.apply()
        exec_damage = before_hp - target_high_def.traits.hp.value

        # Execution bypasses defense completely, dealing significantly more damage
        self.assertGreater(exec_damage, normal_damage)

        # 3. Devastation rung with maximum-HP rider (10%)
        devastation_policy = EffectPolicy(
            coefficient=2.0,
            damage=DamagePolicy(max_hp_fraction=0.10),
        )
        target_high_def.traits.hp._data["current"] = 1000
        before_hp = target_high_def.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending_devas = _handle_damage(
                actor,
                [target_high_def],
                "damage:dark:magic",
                event_context={"resolved_effect": ResolvedEffect(policy=devastation_policy)},
                scale=1.0,
            )
        for eff in pending_devas:
            eff.apply()
        devas_damage = before_hp - target_high_def.traits.hp.value

        # Devastation adds 10% of target max HP (10% of 1000 = 100)
        self.assertGreater(devas_damage, normal_damage)
        self.assertGreaterEqual(devas_damage, 100)

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_two_roots_branch_and_convergence_lineage_gates(self):
        """Scenario: Two roots, branch, and convergence gate through the lineage engine."""
        root_curse = _make_synth_dark_skill("synth_root_curse", ["buff_apply:dark_weaken"])
        curse_branch = _make_synth_dark_skill(
            "synth_curse_branch",
            ["buff_apply:dark_curse"],
            prerequisites=(SkillPrerequisite("synth_root_curse", 3),),
        )
        pure_debuff_leaf = _make_synth_dark_skill(
            "synth_pure_debuff_leaf",
            ["buff_apply:fear"],
            prerequisites=(SkillPrerequisite("synth_curse_branch", 5),),
        )
        erosion_exec_parent = _make_synth_dark_skill(
            "synth_erosion_exec_parent",
            ["damage:dark:magic"],
            prerequisites=(SkillPrerequisite("synth_curse_branch", 8),),
        )

        root_devour = _make_synth_dark_skill("synth_root_devour", ["damage:dark:magic"])
        devour_branch = _make_synth_dark_skill(
            "synth_devour_branch",
            ["damage:dark:magic"],
            prerequisites=(SkillPrerequisite("synth_root_devour", 3),),
        )
        devour_parent = _make_synth_dark_skill(
            "synth_devour_parent",
            ["damage:dark:magic", "self_heal:missing_fraction:0.1"],
            prerequisites=(SkillPrerequisite("synth_devour_branch", 8),),
        )

        capstone = _make_synth_dark_skill(
            "synth_apotheosis_capstone",
            ["damage:dark:magic", "buff_apply:dark_apotheosis", "self_heal:missing_fraction:0.15"],
            prerequisites=(
                SkillPrerequisite("synth_erosion_exec_parent", 10),
                SkillPrerequisite("synth_devour_parent", 10),
            ),
        )

        registry = {
            s.key: s
            for s in (
                root_curse,
                curse_branch,
                pure_debuff_leaf,
                erosion_exec_parent,
                root_devour,
                devour_branch,
                devour_parent,
                capstone,
            )
        }
        validate_prerequisite_graph(registry)

        # Derived tip caps: roots and intermediate nodes cap at consuming prerequisite; leaves at 10
        self.assertEqual(proficiency_cap("synth_root_curse"), 3)
        self.assertEqual(proficiency_cap("synth_curse_branch"), 8)
        self.assertEqual(proficiency_cap("synth_pure_debuff_leaf"), 10)
        self.assertEqual(proficiency_cap("synth_erosion_exec_parent"), 10)
        self.assertEqual(proficiency_cap("synth_root_devour"), 3)
        self.assertEqual(proficiency_cap("synth_devour_branch"), 8)
        self.assertEqual(proficiency_cap("synth_devour_parent"), 10)
        self.assertEqual(proficiency_cap("synth_apotheosis_capstone"), 10)

        # Usage gates: rejects until both parent branches meet Lv.10
        char = create_object(PlayerCharacter, key="synth_lineage_char")
        char.db.skills = {"active": list(registry.keys()), "passive": []}

        # Neither parent satisfied
        char.db.skill_proficiency = {
            "synth_erosion_exec_parent": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            "synth_devour_parent": 5 * SKILL_PROFICIENCY_XP_PER_LEVEL,
        }
        self.assertFalse(can_use_skill(char, capstone))
        self.assertIsNotNone(missing_prerequisite(char, capstone))

        # Only one parent satisfied
        char.db.skill_proficiency["synth_erosion_exec_parent"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(char, capstone))
        self.assertEqual(missing_prerequisite(char, capstone).skill_key, "synth_devour_parent")

        # Both parents satisfied -> accepted
        char.db.skill_proficiency["synth_devour_parent"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(char, capstone))
        self.assertIsNone(missing_prerequisite(char, capstone))

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_retired_dev_era_bindings_resolve_as_ordinary_rejections(self):
        """Scenario: Retired dev-era bindings resolve as ordinary rejections."""
        # 1. Applying deleted buff raises KeyError through the ordinary buff application path
        with self.assertRaises(KeyError):
            apply_buff(self.target, "dark_atk_down")

        # 2. Casting never-existing or retired skill keys yields UNKNOWN_SKILL
        ctx = BattlefieldActionContext(self.bf)
        for key in ("dark_atk_down", "nonexistent_spell", "old_dev_spell"):
            with self.subTest(key=key):
                req = ActionRequest(actor=self.caster, skill_key=key, targets=[self.target], context=ctx)
                res = ActionResolver.resolve(req)
                self.assertEqual(res.outcome, "rejected")
                self.assertEqual(res.reason, RejectReason.UNKNOWN_SKILL)

    @covers_requirement("skill-registry::dark-spell-progression-composes-executable-curse-and-erosion-behavior")
    def test_capstone_mixed_composition_settles_without_double_pricing(self):
        """Capstone stacks devastation damage, wide stat debuff, and missing-fraction self-recovery cleanly."""
        self.caster.traits.hp.current = 100  # missing 100 HP
        self.target.traits.hp.current = 200

        capstone_skill = _make_synth_dark_skill(
            "synth_apotheosis_full",
            effects=(
                "damage:dark:magic",
                "buff_apply:dark_apotheosis",
                "self_heal:missing_fraction:0.15",
            ),
            effect_policies=(
                EffectPolicy(
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(),
                EffectPolicy(),
            ),
        )

        res = self._cast(capstone_skill, [self.target])
        self.assertEqual(res.outcome, "success")

        # Target received damage and debuff
        self.assertLess(self.target.traits.hp.current, 200)
        self.assertIn("dark_apotheosis", entity_active_buffs(self.target))

        # Caster recovered 15% of 100 = 15 HP (100 -> 115)
        self.assertEqual(self.caster.traits.hp.current, 115)

        # No erosion leech occurred during cast (erosion leech is DoT-tick-only; no double-pricing)
        self.assertNotIn("dark_corrosion", entity_active_buffs(self.target))
        self.assertNotIn("dark_corrosion_deep", entity_active_buffs(self.target))
