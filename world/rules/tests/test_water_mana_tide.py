"""Synthetic behavior tests for water spell progression (mana-tide behavior).

Covers:
- Mixed-audience composite settlement (enemy drain/damage + ally restore) with atomic rollback.
- Two roots, branching, and two-parent convergence lineage gates with reverse-edge caps.
- Water family non-healing contract (MP-only manipulation, zero HP heal).
- Wholesale retirement of dev-era keys without aliases, rejecting as unknown skills.
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
from world.rules.action import ActionRequest, ActionResolver, CommitFailed, RejectReason
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.progression import can_use_skill, missing_prerequisite, proficiency_cap
from world.skills.effects import (
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferPolicy,
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


def _make_synth_water_skill(
    key: str,
    effects: tuple[str, ...] | list[str],
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] | None = None,
    *,
    target_spec: TargetSpec = TargetSpec.AREA,
    cost: dict[str, int] | None = None,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
) -> SkillDef:
    """Build one synthetic water skill definition for testing."""
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成水系技能 {key}。",
        kind=SkillKind.ACTIVE,
        target_spec=target_spec,
        cost=cost or {"mp": 10},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP.get("water"),
        effects=list(effects),
        faction_constraint=faction_constraint,
        category=SkillCategory.ELEMENTAL_MAGIC,
        group="water",
        prerequisites=prerequisites,
        effect_policies=tuple(effect_policies) if effect_policies is not None else (),
    )


class WaterManaTideBehaviorTests(EvenniaTest):
    """Synthetic behavior test suite for water mana-tide progression."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_mana_tide_room")
        self.actor = create_object(PlayerCharacter, key="synth_water_actor")
        self.enemy = create_object(PlayerCharacter, key="synth_water_enemy")
        self.ally = create_object(PlayerCharacter, key="synth_water_ally")

        for char in (self.actor, self.enemy, self.ally):
            char.location = self.room
            char.race = "human"
            char.apply_race_baseline()
            char.traits.hp.base = 200
            char.traits.hp.current = 200
            char.traits.mp.base = 200
            char.traits.mp.current = 200
            char.db.skills = {"active": [], "passive": []}

        self.bf = Battlefield(
            teams={
                "party": frozenset({str(self.actor.key), str(self.ally.key)}),
                "enemy": frozenset({str(self.enemy.key)}),
            },
            roster={
                str(self.actor.key): self.actor,
                str(self.ally.key): self.ally,
                str(self.enemy.key): self.enemy,
            },
        )

    def _cast(self, skill: SkillDef, targets: list[Any]) -> Any:
        ctx = BattlefieldActionContext(self.bf)
        req = ActionRequest(actor=self.actor, skill_key=skill.key, targets=targets, context=ctx)
        with patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False):
            self.actor.db.skills = {"active": [skill.key], "passive": []}
            with patch("world.rules.combat.damage.roll_d100", return_value=100):
                return ActionResolver.resolve(req)

    @covers_requirement("skill-registry::water-spell-progression-composes-executable-mana-tide-behavior")
    def test_mixed_audience_composite_settlement_and_atomic_rollback(self):
        """Composite take-and-give settles atomically across enemy and ally audiences, rolling back on failure."""
        composite_skill = _make_synth_water_skill(
            "synth_abyssal_composite",
            effects=(
                "damage:water:magic",
                "gauge_transfer:mp:drain:all",
                "gauge_transfer:mp:restore:fixed:25",
            ),
            effect_policies=(
                EffectPolicy(
                    audience=EffectAudience.ENEMIES,
                    coefficient=3.8,
                    damage=DamagePolicy(max_hp_fraction=0.10),
                ),
                EffectPolicy(audience=EffectAudience.ENEMIES),
                EffectPolicy(audience=EffectAudience.ALLIES),
            ),
            target_spec=TargetSpec.AREA,
            cost={"mp": 50},
        )

        self.enemy.traits.hp.current = 200
        self.enemy.traits.mp.current = 100
        self.ally.traits.mp.current = 30
        self.actor.traits.mp.current = 100

        # 1. Successful composite resolution
        res = self._cast(composite_skill, [self.enemy, self.ally])
        self.assertEqual(res.outcome, "success")

        # Enemy takes damage and has all MP drained
        self.assertLess(self.enemy.traits.hp.current, 200)
        self.assertEqual(self.enemy.traits.mp.current, 0)

        # Ally receives fixed 25 MP restore
        self.assertEqual(self.ally.traits.mp.current, 55)

        # Actor paid 50 MP
        self.assertEqual(self.actor.traits.mp.current, 50)

        # 2. Atomic rollback on commit crash
        self.enemy.traits.hp.current = 200
        self.enemy.traits.mp.current = 100
        self.ally.traits.mp.current = 30
        self.actor.traits.mp.current = 100

        with patch(
            "world.rules.action.resolver._commit",
            side_effect=CommitFailed(RejectReason.COMMIT_FAILED, "simulated commit failure"),
        ):
            res_fail = self._cast(composite_skill, [self.enemy, self.ally])
            self.assertEqual(res_fail.outcome, "rejected")

        # State remains pristine (rolled back)
        self.assertEqual(self.enemy.traits.hp.current, 200)
        self.assertEqual(self.enemy.traits.mp.current, 100)
        self.assertEqual(self.ally.traits.mp.current, 30)
        self.assertEqual(self.actor.traits.mp.current, 100)

    @covers_requirement("skill-registry::water-spell-progression-composes-executable-mana-tide-behavior")
    def test_synthetic_two_root_two_parent_capstone_gates_and_caps(self):
        """Two roots, branch, and two-parent convergence gate through lineage engine with derived caps."""
        root_tide = _make_synth_water_skill("synth_root_tide", ["gauge_transfer:mp:drain:fixed:5"])
        branch_a = _make_synth_water_skill(
            "synth_branch_a",
            ["gauge_transfer:mp:restore:fixed:40"],
            prerequisites=(SkillPrerequisite("synth_root_tide", 3),),
        )
        parent_sigil = _make_synth_water_skill(
            "synth_parent_sigil",
            ["gauge_transfer:mp:drain:all"],
            prerequisites=(SkillPrerequisite("synth_branch_a", 5),),
        )

        root_deep = _make_synth_water_skill("synth_root_deep", ["damage:water:magic"])
        branch_b = _make_synth_water_skill(
            "synth_branch_b",
            ["damage:water:magic"],
            prerequisites=(SkillPrerequisite("synth_root_deep", 3),),
        )
        parent_tide = _make_synth_water_skill(
            "synth_parent_tide",
            ["damage:water:magic"],
            prerequisites=(SkillPrerequisite("synth_branch_b", 8),),
        )

        capstone = _make_synth_water_skill(
            "synth_capstone",
            ["damage:water:magic"],
            prerequisites=(
                SkillPrerequisite("synth_parent_sigil", 10),
                SkillPrerequisite("synth_parent_tide", 10),
            ),
        )

        synth_registry = {
            root_tide.key: root_tide,
            branch_a.key: branch_a,
            parent_sigil.key: parent_sigil,
            root_deep.key: root_deep,
            branch_b.key: branch_b,
            parent_tide.key: parent_tide,
            capstone.key: capstone,
        }

        # Validate DAG structure fails closed on cycles / unknown edges
        reverse_map = validate_prerequisite_graph(synth_registry)
        self.assertIn("synth_parent_sigil", reverse_map)
        self.assertIn("synth_parent_tide", reverse_map)

        # Derived caps from reverse-edge map
        self.assertEqual(max(p for _, p in reverse_map["synth_root_tide"]), 3)
        self.assertEqual(max(p for _, p in reverse_map["synth_branch_a"]), 5)
        self.assertEqual(max(p for _, p in reverse_map["synth_parent_sigil"]), 10)
        self.assertEqual(max(p for _, p in reverse_map["synth_root_deep"]), 3)
        self.assertEqual(max(p for _, p in reverse_map["synth_branch_b"]), 8)
        self.assertEqual(max(p for _, p in reverse_map["synth_parent_tide"]), 10)

        # Test use gating
        char = self.actor
        char.db.skills = {"active": list(synth_registry.keys()), "passive": []}

        # Neither parent satisfied -> rejected
        char.db.skill_proficiency = {}
        self.assertFalse(can_use_skill(char, capstone))
        self.assertEqual(missing_prerequisite(char, capstone).skill_key, "synth_parent_sigil")

        # Parent 1 satisfied, parent 2 not -> rejected
        char.db.skill_proficiency = {"synth_parent_sigil": 10 * 100.0}
        self.assertFalse(can_use_skill(char, capstone))
        self.assertEqual(missing_prerequisite(char, capstone).skill_key, "synth_parent_tide")

        # Both parents satisfied -> accepted
        char.db.skill_proficiency = {
            "synth_parent_sigil": 10 * 100.0,
            "synth_parent_tide": 10 * 100.0,
        }
        self.assertTrue(can_use_skill(char, capstone))
        self.assertIsNone(missing_prerequisite(char, capstone))

    @covers_requirement("skill-registry::water-spell-progression-composes-executable-mana-tide-behavior")
    def test_water_family_is_non_healing_mp_only(self):
        """Water spell compositions manipulate MP/damage/buffs and never restore target HP."""
        water_compositions = [
            _make_synth_water_skill("synth_drain", ["gauge_transfer:mp:drain:fixed:5"]),
            _make_synth_water_skill("synth_restore_mp", ["gauge_transfer:mp:restore:fixed:40"]),
            _make_synth_water_skill("synth_dot_ebbing", ["buff_apply:ebbing"]),
            _make_synth_water_skill(
                "synth_divert_shield",
                ["self_buff_apply:water_film"],
                target_spec=TargetSpec.SELF,
                faction_constraint=FactionConstraint.SELF_ONLY,
            ),
        ]

        # Wounded ally
        self.ally.traits.hp.current = 50
        self.ally.traits.mp.current = 50

        for comp in water_compositions:
            with self.subTest(skill=comp.key):
                hp_before = self.ally.traits.hp.current
                target = [self.actor] if comp.target_spec is TargetSpec.SELF else [self.ally]
                res = self._cast(comp, target)
                self.assertEqual(res.outcome, "success")
                # Ally HP never increased
                self.assertLessEqual(self.ally.traits.hp.current, hp_before)

    @covers_requirement("skill-registry::water-spell-progression-composes-executable-mana-tide-behavior")
    def test_retired_dev_era_keys_reject_as_unknown_skills(self):
        """Five retired HP-heal keys reject cleanly as unknown skills with no aliases or shims."""
        retired_keys = (
            "minor_heal",
            "healing_spring",
            "wellspring_of_life",
            "tidal_revival",
            "sea_of_life",
        )

        # None exist in the live SKILL_REGISTRY
        for key in retired_keys:
            with self.subTest(key=key):
                self.assertNotIn(key, _SKILL_MAP)

        # Attempting to cast any retired key yields UNKNOWN_SKILL rejection
        ctx = BattlefieldActionContext(self.bf)
        for key in retired_keys:
            with self.subTest(cast_key=key):
                req = ActionRequest(actor=self.actor, skill_key=key, targets=[self.ally], context=ctx)
                res = ActionResolver.resolve(req)
                self.assertEqual(res.outcome, "rejected")
                self.assertEqual(res.reason, RejectReason.UNKNOWN_SKILL)
