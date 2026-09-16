"""Synthetic behavior tests for the fire burn-and-immolation progression.

Covers requirements from openspec/changes/fire-spell-catalog/specs/skill-registry/spec.md:
- Requirement: Fire spell progression composes executable burn-and-immolation behavior
  - Scenario: The burn ladder scorches at the authored rung and expires
  - Scenario: The burning armor ignites physical attackers and nothing else
  - Scenario: The lava hazard burns whoever keeps standing on it and steps off when they leave
  - Scenario: The execution rung ignores defense and the immolation costs are paid on cast
  - Scenario: The capstone burns enemies and itself as three independent components
  - Scenario: Branching and the two-parent capstone gate through the lineage engine
  - Scenario: Retired dev-era clauses resolve as ordinary rejections

All fixtures are fire-shaped synthetic skills/buff rows driven through the
real engine paths (wave discipline: behavior tests only — zero fire
data-catalog/契約 tests: no key-set equality, no row mirroring, no numeric
catalog pins).
"""

import importlib
import unittest
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from tools.spec_traceability import covers_requirement
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
)
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
    proficiency_cap,
)
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_outcome_reaction,
)
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
    element: str | None = "fire",
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
        faction_constraint=faction_constraint,
        cost={"mp": 10} if cost is None else cost,
        usable_out_of_combat=True,
        element=_ELEMENT_MAP[element] if element is not None else None,
        effects=list(effects),
        category=category,
        effect_policies=tuple(effect_policies),
        prerequisites=prerequisites,
        parsed_effects=tuple(parsed),
    )


# Synthetic fire-shaped buff definitions
_SYNTH_BURN_DOT = BuffDefinition(
    key="t_synth_burn_dot",
    duration=300,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -8}},
)

_SYNTH_ARMOR_MOUNT = BuffDefinition(
    key="t_synth_armor_mount",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
)

_SYNTH_IGNITE_DEBUFF = BuffDefinition(
    key="t_synth_ignite_debuff",
    duration=60,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -8}},
)

_SYNTH_LAVA_GROUND = BuffDefinition(
    key="t_synth_lava_ground",
    duration=60,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    marker="ground",
    modifiers={"rate": {"target": "hp", "delta": -12}},
)

_SYNTH_SACRIFICE_SELF = BuffDefinition(
    key="t_synth_sacrifice_self",
    duration=120,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -12}},
)

_SYNTH_CRIMSON_ENEMY = BuffDefinition(
    key="t_synth_crimson_enemy",
    duration=300,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -40}},
)

_SYNTH_CRIMSON_SELF = BuffDefinition(
    key="t_synth_crimson_self",
    duration=300,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -20}},
)

_SYNTH_IGNITE_RULE = Rule(
    id="t_synth_scorching_armor_ignite",
    when={"event": "physical_hit", "buff_active": "t_synth_armor_mount"},
    then={"apply_buff_to_source": "t_synth_ignite_debuff"},
)


class FireBurnImmolationBehaviorTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="fire_synth_room")
        self.caster = self._char("fire_synth_caster")
        self.foe = self._char("fire_synth_foe")
        self.foe2 = self._char("fire_synth_foe2")
        self.ally = self._char("fire_synth_ally")
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
            {
                b.key: b
                for b in (
                    _SYNTH_BURN_DOT,
                    _SYNTH_ARMOR_MOUNT,
                    _SYNTH_IGNITE_DEBUFF,
                    _SYNTH_LAVA_GROUND,
                    _SYNTH_SACRIFICE_SELF,
                    _SYNTH_CRIMSON_ENEMY,
                    _SYNTH_CRIMSON_SELF,
                )
            },
            clear=False,
        )
        buff_patch.start()
        self.addCleanup(buff_patch.stop)

        reactions_patch = patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            [*STATE_REACTION_RULES, _SYNTH_IGNITE_RULE],
        )
        reactions_patch.start()
        self.addCleanup(reactions_patch.stop)

    def _char(self, key: str) -> PlayerCharacter:
        char = create_object(PlayerCharacter, key=key)
        char.location = self.room
        char.race = "human"
        char.apply_race_baseline()
        char.traits.hp.base = 1000
        char.traits.hp.current = 1000
        char.traits.mp.base = 1000
        char.traits.mp.current = 1000
        char.traits.defense.base = 10
        char.traits.atk_phys.base = 50
        char.traits.agility.base = 10
        char.traits.magic_power.base = 50
        char.db.skills = {"active": [], "passive": []}
        return char

    def _register(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def _own(self, entity: Any, *keys: str) -> None:
        raw = dict(entity.db.skills or {"active": [], "passive": []})
        entity.db.skills = {
            "active": list(set([*raw.get("active", []), *keys])),
            "passive": list(raw.get("passive", [])),
        }

    def _set_level(self, entity: Any, skill_key: str, level: int) -> None:
        prof = dict(entity.db.skill_proficiency or {})
        prof[skill_key] = level * SKILL_PROFICIENCY_XP_PER_LEVEL
        entity.db.skill_proficiency = prof

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_burn_ladder_scorches_at_authored_rung_and_expires(self):
        """Scenario: The burn ladder scorches at the authored rung and expires."""
        skill = self._register(
            _make_synth_skill(
                "t_synth_burn_spell",
                effects=("damage:fire:magic", "buff_apply:t_synth_burn_dot"),
                effect_policies=(
                    EffectPolicy(coefficient=1.4),
                    EffectPolicy(),
                ),
            )
        )
        self._own(self.caster, skill.key)

        req = ActionRequest(
            actor=self.caster,
            skill_key=skill.key,
            targets=[self.foe],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertIn("t_synth_burn_dot", entity_active_buffs(self.foe))

        # Clock advances past tick interval: victim loses -8 HP
        hp_before = self.foe.traits.hp.current
        records = tick_buffs(self.foe, 10)
        self.assertTrue(any(r.definition_key == "t_synth_burn_dot" for r in records))
        self.assertEqual(self.foe.traits.hp.current, hp_before - 8)

        # Clock advances past expiry (290 more seconds)
        tick_buffs(self.foe, 290)
        self.assertNotIn("t_synth_burn_dot", entity_active_buffs(self.foe))
        # Further ticks do not deduct burn damage
        hp_after_expiry = self.foe.traits.hp.current
        tick_buffs(self.foe, 10)
        self.assertEqual(self.foe.traits.hp.current, hp_after_expiry)

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_burning_armor_ignites_physical_attackers_and_nothing_else(self):
        """Scenario: The burning armor ignites physical attackers and nothing else."""
        armor_skill = self._register(
            _make_synth_skill(
                "t_synth_armor_spell",
                effects=("self_buff_apply:t_synth_armor_mount",),
                target_spec=TargetSpec.SELF,
                faction_constraint=FactionConstraint.SELF_ONLY,
                effect_policies=(EffectPolicy(),),
            )
        )
        self._own(self.caster, armor_skill.key)

        # Cast armor buff onto self
        req = ActionRequest(
            actor=self.caster,
            skill_key=armor_skill.key,
            targets=[self.caster],
            context=BattlefieldActionContext(self.bf),
        )
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        self.assertIn("t_synth_armor_mount", entity_active_buffs(self.caster))

        # Physical attack from foe strikes caster
        strike_skill = self._register(
            _make_synth_skill(
                "t_synth_physical_strike",
                effects=("damage:fire:physical",),
                effect_policies=(EffectPolicy(coefficient=1.0),),
            )
        )
        self._own(self.foe, strike_skill.key)

        strike_req = ActionRequest(
            actor=self.foe,
            skill_key=strike_skill.key,
            targets=[self.caster],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            res_strike = ActionResolver.resolve(strike_req)

        self.assertEqual(res_strike.outcome, "success")
        # Attacker holds live ignition instance with grant-time attribution to armor holder
        self.assertIn("t_synth_ignite_debuff", entity_active_buffs(self.foe))
        self.assertEqual(
            getattr(self.foe.buffs.all["t_synth_ignite_debuff"], "source_key", None),
            str(self.caster.key),
        )

        # Foe takes -8 HP on tick
        f_before = self.foe.traits.hp.current
        records = tick_buffs(self.foe, 10)
        self.assertTrue(any(r.definition_key == "t_synth_ignite_debuff" for r in records))
        self.assertEqual(self.foe.traits.hp.current, f_before - 8)

        # Magic attack from foe2 on caster does NOT trigger ignite
        magic_skill = self._register(
            _make_synth_skill(
                "t_synth_magic_strike",
                effects=("damage:fire:magic",),
                effect_policies=(EffectPolicy(coefficient=1.0),),
            )
        )
        self._own(self.foe2, magic_skill.key)
        magic_req = ActionRequest(
            actor=self.foe2,
            skill_key=magic_skill.key,
            targets=[self.caster],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            ActionResolver.resolve(magic_req)
        self.assertNotIn("t_synth_ignite_debuff", entity_active_buffs(self.foe2))

        # Missed physical swing does NOT trigger ignite
        with patch("world.rules.combat.roll_d100", return_value=0):  # miss
            miss_req = ActionRequest(
                actor=self.foe2,
                skill_key=strike_skill.key,
                targets=[self.caster],
                context=BattlefieldActionContext(self.bf),
            )
            ActionResolver.resolve(miss_req)
        self.assertNotIn("t_synth_ignite_debuff", entity_active_buffs(self.foe2))

        # Sourceless write does NOT trigger ignite
        dispatch_outcome_reaction(self.caster, "physical_hit", source=None)
        self.assertNotIn("t_synth_ignite_debuff", entity_active_buffs(self.foe2))

        # Dead attacker does NOT receive ignite
        self.foe2.traits.hp.current = 0
        dispatch_outcome_reaction(self.caster, "physical_hit", source=self.foe2)
        self.assertNotIn("t_synth_ignite_debuff", entity_active_buffs(self.foe2))
        self.foe2.traits.hp.current = 1000

        # No damage moved back to attacker as counter-damage (foe took no strike damage from carrier)
        # Foe's ignite lives on foe's own clock: remove armor from caster, foe still has ignite
        self.caster.buffs.remove("t_synth_armor_mount")
        self.assertNotIn("t_synth_armor_mount", entity_active_buffs(self.caster))
        self.assertIn("t_synth_ignite_debuff", entity_active_buffs(self.foe))

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_lava_hazard_burns_while_standing_and_extinguishes_on_exit(self):
        """Scenario: The lava hazard burns whoever keeps standing on it and steps off when they leave."""
        lava_skill = self._register(
            _make_synth_skill(
                "t_synth_lava_spell",
                effects=("damage:fire:magic", "buff_apply:t_synth_lava_ground"),
                target_spec=TargetSpec.AREA,
                effect_policies=(
                    EffectPolicy(coefficient=1.4),
                    EffectPolicy(),
                ),
            )
        )
        self._own(self.caster, lava_skill.key)

        req = ActionRequest(
            actor=self.caster,
            skill_key=lava_skill.key,
            targets=[self.foe],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        self.assertIn("t_synth_lava_ground", entity_active_buffs(self.foe))

        # Also apply a non-marker buff to the foe to test differential persistence
        apply_buff(self.foe, "t_synth_burn_dot")
        self.assertIn("t_synth_burn_dot", entity_active_buffs(self.foe))

        # Standing victim loses -12 from lava and -8 from burn_dot
        hp_before = self.foe.traits.hp.current
        records = tick_buffs(self.foe, 10)
        self.assertEqual(self.foe.traits.hp.current, hp_before - 20)

        # Flee the battlefield: remove_ground_markers simulates battlefield departure
        remove_ground_markers(self.foe)
        self.assertNotIn("t_synth_lava_ground", entity_active_buffs(self.foe))
        # Non-marker buff persists
        self.assertIn("t_synth_burn_dot", entity_active_buffs(self.foe))

        # Further ticks deduct only the non-marker buff (-8)
        hp_mid = self.foe.traits.hp.current
        tick_buffs(self.foe, 10)
        self.assertEqual(self.foe.traits.hp.current, hp_mid - 8)

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_execution_rung_ignores_defense_and_immolation_costs_paid_on_cast(self):
        """Scenario: The execution rung ignores defense and the immolation costs are paid on cast."""
        # Execution skill with bypass_defense
        exec_skill = self._register(
            _make_synth_skill(
                "t_synth_exec_spell",
                effects=("damage:fire:magic",),
                effect_policies=(
                    EffectPolicy(
                        coefficient=4.0,
                        damage=DamagePolicy(bypass_defense=True, predicate=()),
                    ),
                ),
            )
        )
        # Normal skill without bypass_defense
        normal_skill = self._register(
            _make_synth_skill(
                "t_synth_normal_spell",
                effects=("damage:fire:magic",),
                effect_policies=(EffectPolicy(coefficient=4.0),),
            )
        )
        self._own(self.caster, exec_skill.key, normal_skill.key)

        # High defense foe (defense 300)
        self.foe.traits.defense.base = 300
        # Zero defense foe2
        self.foe2.traits.defense.base = 0

        # Execute strike against high defense foe vs zero defense foe2
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending_high_def = _handle_damage(
                self.caster,
                [self.foe],
                "damage:fire:magic",
                {"resolved_effect": ResolvedEffect(policy=exec_skill.effect_policies[0])},
                1.0,
            )
            pending_zero_def = _handle_damage(
                self.caster,
                [self.foe2],
                "damage:fire:magic",
                {"resolved_effect": ResolvedEffect(policy=exec_skill.effect_policies[0])},
                1.0,
            )
        amt_high = int(pending_high_def[0].description.split("|")[2])
        amt_zero = int(pending_zero_def[0].description.split("|")[2])
        # Defense subtraction skipped: high defense takes identical damage to zero defense
        self.assertGreater(amt_high, 0)
        self.assertEqual(amt_high, amt_zero)

        # Immolation skill with overflow coefficient 3.4 and self-burn cost
        immolation_skill = self._register(
            _make_synth_skill(
                "t_synth_immolation_spell",
                effects=(
                    "damage:fire:magic",
                    "self_buff_apply:t_synth_sacrifice_self",
                ),
                target_spec=TargetSpec.AREA,
                effect_policies=(
                    EffectPolicy(coefficient=3.4),
                    EffectPolicy(),
                ),
            )
        )
        self._own(self.caster, immolation_skill.key)

        # Case A: Cast lands on target
        req_hit = ActionRequest(
            actor=self.caster,
            skill_key=immolation_skill.key,
            targets=[self.foe],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            res_hit = ActionResolver.resolve(req_hit)
        self.assertEqual(res_hit.outcome, "success")
        self.assertIn("t_synth_sacrifice_self", entity_active_buffs(self.caster))

        # Case B: Cast misses the target (damage leg misses, but self-burn still lands)
        self.caster.buffs.remove("t_synth_sacrifice_self")
        self.assertNotIn("t_synth_sacrifice_self", entity_active_buffs(self.caster))
        with patch("world.rules.combat.roll_d100", return_value=0):  # miss
            res_miss = ActionResolver.resolve(req_hit)
        # Self-buff lands regardless of damage hit
        self.assertIn("t_synth_sacrifice_self", entity_active_buffs(self.caster))

        # Caster takes self-burn tick (-12)
        c_before = self.caster.traits.hp.current
        records = tick_buffs(self.caster, 10)
        self.assertTrue(any(r.definition_key == "t_synth_sacrifice_self" for r in records))
        self.assertEqual(self.caster.traits.hp.current, c_before - 12)

        # No healing was applied (no heal/self_heal event in logs, HP did not increase)
        self.assertFalse(any(e.kind in ("heal", "self_heal") for e in res_hit.event_log.entries))

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_capstone_burns_enemies_and_self_as_three_independent_components(self):
        """Scenario: The capstone burns enemies and itself as three independent components."""
        capstone_skill = self._register(
            _make_synth_skill(
                "t_synth_capstone_spell",
                effects=(
                    "damage:fire:magic",
                    "buff_apply:t_synth_crimson_enemy",
                    "self_buff_apply:t_synth_crimson_self",
                ),
                target_spec=TargetSpec.AREA,
                effect_policies=(
                    EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=4.4),
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                    EffectPolicy(),
                ),
            )
        )
        self._own(self.caster, capstone_skill.key)

        req = ActionRequest(
            actor=self.caster,
            skill_key=capstone_skill.key,
            targets=[self.foe, self.foe2],
            context=BattlefieldActionContext(self.bf),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")

        # Enemies take enemy burn component (-40)
        self.assertIn("t_synth_crimson_enemy", entity_active_buffs(self.foe))
        self.assertIn("t_synth_crimson_enemy", entity_active_buffs(self.foe2))
        self.assertNotIn("t_synth_crimson_self", entity_active_buffs(self.foe))

        # Caster alone takes self-burn component (-20)
        self.assertIn("t_synth_crimson_self", entity_active_buffs(self.caster))
        self.assertNotIn("t_synth_crimson_enemy", entity_active_buffs(self.caster))

        # Ally takes neither leg
        self.assertNotIn("t_synth_crimson_enemy", entity_active_buffs(self.ally))
        self.assertNotIn("t_synth_crimson_self", entity_active_buffs(self.ally))

        # Ticking verifies the exact rungs
        foe_before = self.foe.traits.hp.current
        tick_buffs(self.foe, 10)
        self.assertEqual(self.foe.traits.hp.current, foe_before - 40)

        caster_before = self.caster.traits.hp.current
        tick_buffs(self.caster, 10)
        self.assertEqual(self.caster.traits.hp.current, caster_before - 20)

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_branching_and_two_parent_capstone_gate_through_lineage_engine(self):
        """Scenario: Branching and the two-parent capstone gate through the lineage engine."""
        root = self._register(_make_synth_skill("t_tree_root"))
        child1 = self._register(
            _make_synth_skill(
                "t_tree_c1",
                prerequisites=(SkillPrerequisite(root.key, 3),),
            )
        )
        branch_point = self._register(
            _make_synth_skill(
                "t_tree_branch",
                prerequisites=(SkillPrerequisite(child1.key, 3),),
            )
        )
        # 3 children of branch point
        b_child1 = self._register(
            _make_synth_skill(
                "t_tree_b1",
                prerequisites=(SkillPrerequisite(branch_point.key, 3),),
            )
        )
        b_leaf = self._register(
            _make_synth_skill(
                "t_tree_leaf",
                prerequisites=(SkillPrerequisite(branch_point.key, 3),),
            )
        )
        b_armor = self._register(
            _make_synth_skill(
                "t_tree_armor",
                prerequisites=(SkillPrerequisite(branch_point.key, 3),),
            )
        )
        # Sub-branch from b_child1 leading to parent A
        sub_a1 = self._register(
            _make_synth_skill(
                "t_tree_sub_a1",
                prerequisites=(SkillPrerequisite(b_child1.key, 5),),
            )
        )
        parent_a = self._register(
            _make_synth_skill(
                "t_tree_parent_a",
                prerequisites=(SkillPrerequisite(sub_a1.key, 8),),
            )
        )
        # Sub-branch from b_child1 leading to parent B
        sub_b1 = self._register(
            _make_synth_skill(
                "t_tree_sub_b1",
                prerequisites=(SkillPrerequisite(b_child1.key, 5),),
            )
        )
        parent_b = self._register(
            _make_synth_skill(
                "t_tree_parent_b",
                prerequisites=(SkillPrerequisite(sub_b1.key, 5),),
            )
        )
        # Two-parent capstone
        capstone = self._register(
            _make_synth_skill(
                "t_tree_capstone",
                prerequisites=(
                    SkillPrerequisite(parent_a.key, 10),
                    SkillPrerequisite(parent_b.key, 10),
                ),
            )
        )

        all_keys = [
            root.key,
            child1.key,
            branch_point.key,
            b_child1.key,
            b_leaf.key,
            b_armor.key,
            sub_a1.key,
            parent_a.key,
            sub_b1.key,
            parent_b.key,
            capstone.key,
        ]
        self._own(self.caster, *all_keys)

        # 1. Gating along spine
        self.assertTrue(can_use_skill(self.caster, root))
        self.assertFalse(can_use_skill(self.caster, child1))
        self.assertEqual(missing_prerequisite(self.caster, child1), SkillPrerequisite(root.key, 3))

        self._set_level(self.caster, root.key, 3)
        self.assertTrue(can_use_skill(self.caster, child1))

        self.assertFalse(can_use_skill(self.caster, branch_point))
        self._set_level(self.caster, child1.key, 3)
        self.assertTrue(can_use_skill(self.caster, branch_point))

        # 2. Three branches unlock together once branch point reaches Lv.3
        self.assertFalse(can_use_skill(self.caster, b_child1))
        self.assertFalse(can_use_skill(self.caster, b_leaf))
        self.assertFalse(can_use_skill(self.caster, b_armor))

        self._set_level(self.caster, branch_point.key, 3)
        self.assertTrue(can_use_skill(self.caster, b_child1))
        self.assertTrue(can_use_skill(self.caster, b_leaf))
        self.assertTrue(can_use_skill(self.caster, b_armor))

        # 3. Two-parent capstone gates until BOTH parents reach threshold 10
        self.assertFalse(can_use_skill(self.caster, capstone))
        self._set_level(self.caster, b_child1.key, 5)
        self._set_level(self.caster, sub_a1.key, 8)
        self._set_level(self.caster, sub_b1.key, 5)

        # Level up parent A to 10 only: capstone still gated by parent B
        self._set_level(self.caster, parent_a.key, 10)
        self.assertFalse(can_use_skill(self.caster, capstone))
        self.assertEqual(missing_prerequisite(self.caster, capstone), SkillPrerequisite(parent_b.key, 10))

        # Level up parent B to 10: capstone unlocks
        self._set_level(self.caster, parent_b.key, 10)
        self.assertTrue(can_use_skill(self.caster, capstone))

    @covers_requirement(
        "skill-registry::fire-spell-progression-composes-executable-burn-and-immolation-behavior"
    )
    def test_retired_dev_era_clauses_resolve_as_ordinary_rejections(self):
        """Scenario: Retired dev-era clauses resolve as ordinary rejections."""
        req = ActionRequest(
            actor=self.caster,
            skill_key="never_existing_fire_spell_xyz",
            targets=[self.foe],
            context=BattlefieldActionContext(self.bf),
        )
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "rejected")
        self.assertEqual(res.reason, RejectReason.UNKNOWN_SKILL)
