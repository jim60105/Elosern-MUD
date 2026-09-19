"""Synthetic behavior tests for the earth terrain-and-guard progression.

Covers requirements:
- skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior
- terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact
- terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield
- damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event
- damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion

All fixtures are earth-shaped synthetic skills/buff rows driven through the
real engine paths (wave discipline: behavior tests only — zero earth
data-catalog/契約 tests: no key-set equality, no row mirroring, no numeric
catalog pins). The carapace scenarios compose against the SHIPPED
``thorned_carapace_counter`` rule and the shipped ``earth_carapace`` mount
key, because that rule-row + buff-key pairing is the composition this
catalog change owns; they observe state transitions, never the row numbers.
"""

import importlib
import unittest
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
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
from world.rules.combat import Battlefield, BattlefieldActionContext, _handle_damage
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
)
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import dispatch_outcome_reaction
from world.rules.target_facts import matches_target_predicate
from world.skills.effects import EffectAudience, EffectPolicy, ResolvedEffect
from world.skills.registry import (
    DamageEffect,
    DamagePolicy,
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
    element: str | None = None,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
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
        cost={},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP[element] if element is not None else None,
        effects=list(effects),
        category=category,
        effect_policies=tuple(effect_policies),
        prerequisites=prerequisites,
        parsed_effects=tuple(parsed),
    )


# Earth-shaped synthetic buff rows (mirroring the authored clause shapes;
# never asserting the shipped rows' numbers).
_SYNTH_ARMOR_MOUNT = BuffDefinition(
    key="t_earth_armor",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
)
_SYNTH_WARD_MOUNT = BuffDefinition(
    key="t_earth_ward",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
)
_SYNTH_DUST_MOUNT = BuffDefinition(
    key="t_earth_dust",
    duration=20,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_FISSURE = BuffDefinition(
    key="t_earth_fissure",
    duration=60,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    marker="ground",
    modifiers={"rate": {"target": "hp", "delta": -12}},
)
_SYNTH_FISSURE_QUAKE = BuffDefinition(
    key="t_earth_fissure_quake",
    duration=40,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    marker="ground",
    modifiers={"rate": {"target": "hp", "delta": -12}},
)
_SYNTH_CONTROL = BuffDefinition(
    key="t_earth_control",
    duration=90,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
    polarity="buff",
    marker=None,
)
_SYNTH_SLOW = BuffDefinition(
    key="t_ice_slow_synth",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)

# Synthetic ladder rules riding the shipped modifier table (the
# light-sustained-recovery D3 pattern: timed defense/accuracy is rule-table
# data, the buff rows are mounts).
_SYNTH_ARMOR_RULE = Rule(
    id="t_earth_armor_rule",
    when={"buff_active": "t_earth_armor"},
    then={"defense": 5},
)
_SYNTH_WARD_RULE = Rule(
    id="t_earth_ward_rule",
    when={"buff_active": "t_earth_ward"},
    then={"defense": 12},
)
_SYNTH_DUST_RULE = Rule(
    id="t_earth_dust_rule",
    when={"buff_active": "t_earth_dust"},
    then={"accuracy": -5},
)


class EarthTerrainGuardBehaviorTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="earth_synth_room")
        self.caster = self._char("earth_synth_caster")
        self.foe = self._char("earth_synth_foe")
        self.foe2 = self._char("earth_synth_foe2")
        self.ally = self._char("earth_synth_ally")
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
                    _SYNTH_ARMOR_MOUNT,
                    _SYNTH_WARD_MOUNT,
                    _SYNTH_DUST_MOUNT,
                    _SYNTH_FISSURE,
                    _SYNTH_FISSURE_QUAKE,
                    _SYNTH_CONTROL,
                    _SYNTH_SLOW,
                )
            },
            clear=False,
        )
        buff_patch.start()
        self.addCleanup(buff_patch.stop)
        rules_patch = patch(
            "world.rules.combat_modifiers._RULES",
            [*_RULES, _SYNTH_ARMOR_RULE, _SYNTH_WARD_RULE, _SYNTH_DUST_RULE],
        )
        rules_patch.start()
        self.addCleanup(rules_patch.stop)

    def _char(self, key: str) -> PlayerCharacter:
        char = create_object(PlayerCharacter, key=key)
        char.location = self.room
        char.race = "human"
        char.apply_race_baseline()
        char.traits.hp.base = 1000
        char.traits.hp.current = 1000
        char.traits.mp.base = 900
        char.traits.mp.current = 900
        char.traits.defense.base = 10
        char.traits.atk_phys.base = 50
        char.traits.agility.base = 10
        char.traits.magic_power.base = 30
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
        with patch("world.rules.combat.damage.roll_d100", return_value=roll):
            return ActionResolver.resolve(req)

    # --- Scenario: The defense ladder guards observable stats at settlement

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_self_cast_defense_guard_rises_and_recovers_on_expiry(self):
        """Synthetic self-cast guard raises effective defense through the rule table for its duration and recovers on expiry."""
        skill = self._register(
            _make_synth_skill(
                "synth_guard_self",
                ["self_buff_apply:t_earth_armor"],
                target_spec=TargetSpec.SELF,
            )
        )
        self._own(self.caster, skill.key)
        baseline = evaluate_combat_modifiers(self.caster).get("defense", 0)
        self.assertEqual(baseline, 0)
        res = self._cast(self.caster, skill.key, [])
        self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
        self.assertIn("t_earth_armor", entity_active_buffs(self.caster))
        self.assertEqual(evaluate_combat_modifiers(self.caster).get("defense"), 5)
        # refresh re-cast never stacks the ladder
        self._cast(self.caster, skill.key, [])
        self.assertEqual(evaluate_combat_modifiers(self.caster).get("defense"), 5)
        tick_buffs(self.caster, 60)
        self.assertNotIn("t_earth_armor", entity_active_buffs(self.caster))
        self.assertEqual(
            evaluate_combat_modifiers(self.caster).get("defense", 0), 0
        )

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_ally_area_guard_spares_enemies(self):
        """Synthetic ALLIES-audience area guard raises ally settlement defense and spares enemies."""
        skill = self._register(
            _make_synth_skill(
                "synth_guard_area",
                ["buff_apply:t_earth_ward"],
                target_spec=TargetSpec.AREA,
                effect_policies=(EffectPolicy(audience=EffectAudience.ALLIES),),
            )
        )
        self._own(self.caster, skill.key)
        res = self._cast(
            self.caster, skill.key, [self.foe, self.foe2, self.ally]
        )
        self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
        self.assertIn("t_earth_ward", entity_active_buffs(self.ally))
        self.assertNotIn("t_earth_ward", entity_active_buffs(self.foe))
        self.assertNotIn("t_earth_ward", entity_active_buffs(self.foe2))
        self.assertEqual(evaluate_combat_modifiers(self.ally).get("defense"), 12)
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("defense", 0), 0)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_accuracy_debuff_rung_settles_and_expires(self):
        """Synthetic accuracy debuff enters the to-hit bundle and clears at its duration."""
        skill = self._register(
            _make_synth_skill(
                "synth_dust_area",
                ["buff_apply:t_earth_dust"],
                target_spec=TargetSpec.AREA,
            )
        )
        self._own(self.caster, skill.key)
        res = self._cast(self.caster, skill.key, [self.foe, self.foe2])
        self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
        self.assertIn("t_earth_dust", entity_active_buffs(self.foe))
        self.assertEqual(evaluate_combat_modifiers(self.foe).get("accuracy"), -5)
        tick_buffs(self.foe, 19)
        self.assertIn("t_earth_dust", entity_active_buffs(self.foe))
        tick_buffs(self.foe, 2)
        self.assertNotIn("t_earth_dust", entity_active_buffs(self.foe))
        self.assertEqual(
            evaluate_combat_modifiers(self.foe).get("accuracy", 0), 0
        )

    # --- Scenario: Fissure hazards burn whoever keeps standing on them

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    @covers_requirement(
        "terrain-marker::a-ground-marker-buff-row-makes-holding-it-the-canonical-standing-on-it-fact"
    )
    def test_marker_hazard_ticks_dot_while_standing_and_stops_on_expiry(self):
        """A marker + reused-slow composition burns the standing victim per interval; expiry ends ticking and the standing-on-it fact."""
        skill = self._register(
            _make_synth_skill(
                "synth_fissure_area",
                ["buff_apply:t_earth_fissure", "buff_apply:t_ice_slow_synth"],
                target_spec=TargetSpec.AREA,
            )
        )
        self._own(self.caster, skill.key)
        victim = self.foe
        res = self._cast(self.caster, skill.key, [victim])
        self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
        self.assertIn("t_earth_fissure", entity_active_buffs(victim))
        self.assertIn("t_ice_slow_synth", entity_active_buffs(victim))
        # standing-on-it fact == holding the marker
        self.assertTrue(
            matches_target_predicate(victim, ("buff:t_earth_fissure",))
        )
        hp_before = victim.traits.hp.current
        records = tick_buffs(victim, 10)
        fired = [r for r in records if r.definition_key == "t_earth_fissure"]
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0].delta, -12)
        self.assertEqual(victim.traits.hp.current, hp_before - 12)
        # expiry ends the ticking and the standing-on-it fact together
        tick_buffs(victim, 50)
        self.assertNotIn("t_earth_fissure", entity_active_buffs(victim))
        self.assertFalse(
            matches_target_predicate(victim, ("buff:t_earth_fissure",))
        )
        hp_end = victim.traits.hp.current
        tick_buffs(victim, 10)
        self.assertEqual(victim.traits.hp.current, hp_end)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    @covers_requirement(
        "terrain-marker::a-ground-marker-extinguishes-when-its-holder-leaves-the-battlefield"
    )
    def test_flee_sweep_stops_ticking_and_spares_control_buff(self):
        """The ground-marker sweep extinguishes the hazard mid-duration while a control buff persists."""
        apply_buff(self.foe, "t_earth_fissure")
        apply_buff(self.foe, "t_earth_control")
        self.assertIn("t_earth_fissure", entity_active_buffs(self.foe))
        self.assertEqual(remove_ground_markers(self.foe), 1)
        self.assertNotIn("t_earth_fissure", entity_active_buffs(self.foe))
        self.assertIn("t_earth_control", entity_active_buffs(self.foe))
        hp_before = self.foe.traits.hp.current
        records = tick_buffs(self.foe, 10)
        self.assertEqual(
            [r for r in records if r.definition_key == "t_earth_fissure"], []
        )
        self.assertEqual(self.foe.traits.hp.current, hp_before)
        self.assertEqual(remove_ground_markers(self.foe), 0)

    # --- Scenario: The synergy strike prices the marker once and bypasses
    #               defense always

    def _settle_strike(self, skill: SkillDef, target: Any) -> int:
        policy_effect = skill.effect_policies[0]
        with patch("world.rules.combat.damage.roll_d100", return_value=75):
            before = target.traits.hp.current
            pending = _handle_damage(
                self.caster,
                [target],
                "damage:earth:magic",
                event_context={
                    "resolved_effect": ResolvedEffect(policy=policy_effect),
                    "battlefield": self.bf,
                },
                scale=1.0,
            )
            for eff in pending:
                eff.apply()
        return int(before - target.traits.hp.current)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_synergy_prices_marker_once_and_bypasses_defense_always(self):
        """Parallel marker rungs share one multiplier application; defense is ignored on and off marker."""
        skill = self._register(
            _make_synth_skill(
                "synth_judgment_like",
                ["damage:earth:magic"],
                effect_policies=(
                    EffectPolicy(
                        coefficient=2.0,
                        damage=DamagePolicy(
                            predicate=(
                                "buff:t_earth_fissure",
                                "buff:t_earth_fissure_quake",
                            ),
                            attack_multiplier=1.15,
                            unconditional_defense_bypass=True,
                        ),
                    ),
                ),
            )
        )
        target = self.foe
        target.traits.defense.base = 400  # impenetrable without the bypass
        target.traits.hp.current = 1000

        off = self._settle_strike(skill, target)
        # unconditional bypass: a 400-defense target takes exactly what a
        # 0-defense twin takes — the hardened defense never clamps the strike
        twin = self.foe2
        twin.traits.defense.base = 0
        twin.traits.hp.current = 1000
        off_twin = self._settle_strike(skill, twin)
        self.assertEqual(off, off_twin)
        self.assertGreater(off, 1)

        target.traits.hp.current = 1000
        apply_buff(target, "t_earth_fissure")
        single = self._settle_strike(skill, target)
        # the target's 400 defense is still bypassed on-marker
        self.assertGreater(single, off)  # marker rung prices in once

        target.traits.hp.current = 1000
        apply_buff(target, "t_earth_fissure_quake")  # parallel duration rung
        both = self._settle_strike(skill, target)
        self.assertEqual(both, single)  # any-match-once: never twice

    # --- Scenario: The carapace returns physical pain and ignores everything
    #               else (composition with the SHIPPED thorned_carapace rule)

    def _carapace_strike(self, physical: bool, *, roll: int = 100, hit: bool = True):
        """Attacker (caster) strikes the foe, who mounts the shipped carapace."""
        holder = self.foe
        apply_buff(holder, "earth_carapace")
        effects = ["damage:earth:physical"] if physical else ["damage:earth:magic"]
        skill = self._register(
            _make_synth_skill(
                "synth_carapace_strike" if physical else "synth_carapace_bolt",
                effects,
                element=None if physical else "earth",
                category=(
                    SkillCategory.MARTIAL_ARTS
                    if physical
                    else SkillCategory.ELEMENTAL_MAGIC
                ),
            )
        )
        self._own(self.caster, skill.key)
        attacker_hp = self.caster.traits.hp.current
        cm_patch = None
        if not hit:
            cm_patch = patch(
                "world.rules.combat.damage._to_hit", return_value=(False, -20.0)
            )
            cm_patch.start()
        try:
            res = self._cast(self.caster, skill.key, [holder], roll=roll)
        finally:
            if cm_patch is not None:
                cm_patch.stop()
        return res, int(attacker_hp - self.caster.traits.hp.current)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    @covers_requirement(
        "damage-state-feedback::a-qualifying-physical-strike-dispatches-one-source-attributed-on-hit-event"
    )
    def test_carapace_prices_once_per_landed_physical_strike(self):
        """A landed physical strike on the mount-holder moves the attacker's HP; the counter settles without recursion."""
        res, counter = self._carapace_strike(physical=True)
        self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
        # the counter leg lands on the attacker (holder HP movement is the
        # strike itself; non-recursion is pinned in the dispatch test below)
        self.assertGreater(counter, 0)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_carapace_is_silent_for_magic_and_miss(self):
        """Magic strikes and missed swings dispatch no qualifying physical_hit; the counter moves no HP."""
        with self.subTest("magic"):
            res, counter = self._carapace_strike(physical=False)
            self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
            self.assertEqual(counter, 0)
        with self.subTest("miss"):
            res, counter = self._carapace_strike(physical=True, hit=False)
            self.assertEqual(res.outcome, "success", getattr(res, "detail", res))
            self.assertEqual(counter, 0)

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    @covers_requirement(
        "damage-state-feedback::source-targeted-reaction-actions-settle-once-in-transaction-without-recursion"
    )
    def test_counter_does_not_chain_and_dies_with_the_mount(self):
        """A mounted-vs-mounted exchange settles one counter per dispatch, and an unmounted holder is silent."""
        holder = self.foe
        apply_buff(holder, "earth_carapace")
        apply_buff(self.caster, "earth_carapace")
        before = self.caster.traits.hp.current
        dispatch_outcome_reaction(holder, "physical_hit", source=self.caster)
        # one counter leg settles on the attacker; the attacker's own mount
        # does not fire back (counter legs are not qualifying physical
        # strikes), so the holder's HP is untouched
        self.assertLess(self.caster.traits.hp.current, before)
        self.assertEqual(holder.traits.hp.current, 1000)
        # mount expiry (empty buff state) means silence
        holder.db.buffs = {}
        self.assertNotIn("earth_carapace", entity_active_buffs(holder))
        before = self.caster.traits.hp.current
        dispatch_outcome_reaction(holder, "physical_hit", source=self.caster)
        self.assertEqual(self.caster.traits.hp.current, before)

    # --- Scenario: Devastation and execution rungs behave through the shared
    #               policies

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_devastation_rung_and_execution_rung_share_policies(self):
        """A devastation synthetic adds the max-HP rider; an execution synthetic ignores defense — no earth-specific code."""
        target = self.foe
        target.traits.defense.base = 10  # positive margins: no floor clamping
        target.traits.hp.base = 1000
        target.traits.hp.current = 1000

        plain = self._register(
            _make_synth_skill("synth_plain_strike", ["damage:earth:magic"])
        )
        devastating = self._register(
            _make_synth_skill(
                "synth_devastating_strike",
                ["damage:earth:magic"],
                effect_policies=(
                    EffectPolicy(
                        coefficient=1.0,
                        damage=DamagePolicy(max_hp_fraction=0.10),
                    ),
                ),
            )
        )
        executing = self._register(
            _make_synth_skill(
                "synth_executing_strike",
                ["damage:earth:magic"],
                effect_policies=(
                    EffectPolicy(
                        coefficient=1.0,
                        damage=DamagePolicy(unconditional_defense_bypass=True),
                    ),
                ),
            )
        )

        plain_damage = self._settle_strike(plain, target)
        devas_damage = self._settle_strike(devastating, target)
        exec_damage = self._settle_strike(executing, target)
        self.assertEqual(devas_damage - plain_damage, 100)  # 10% of max HP
        self.assertGreater(exec_damage, plain_damage)

    # --- Scenario: Two roots, branches, and the two-parent capstone gate

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_two_root_branch_convergence_gates(self):
        """A synthetic earth-shaped lineage gates use on every authored threshold and converges on a two-parent capstone."""
        root_guard = self._register(
            _make_synth_skill(
                "synth_e_root_guard",
                ["self_buff_apply:t_earth_armor"],
                target_spec=TargetSpec.SELF,
            )
        )
        guard_child = self._register(
            _make_synth_skill(
                "synth_e_guard_child",
                ["self_buff_apply:t_earth_ward"],
                target_spec=TargetSpec.SELF,
                prerequisites=(SkillPrerequisite("synth_e_root_guard", 3),),
            )
        )
        root_terrain = self._register(
            _make_synth_skill(
                "synth_e_root_terrain",
                ["buff_apply:t_earth_dust"],
                target_spec=TargetSpec.AREA,
            )
        )
        terrain_deep = self._register(
            _make_synth_skill(
                "synth_e_terrain_deep",
                ["damage:earth:magic"],
                prerequisites=(SkillPrerequisite("synth_e_root_terrain", 3),),
            )
        )
        capstone = self._register(
            _make_synth_skill(
                "synth_e_capstone",
                ["damage:earth:magic"],
                prerequisites=(
                    SkillPrerequisite("synth_e_guard_child", 10),
                    SkillPrerequisite("synth_e_terrain_deep", 10),
                ),
            )
        )
        char = self.ally
        self._own(
            char,
            root_guard.key,
            guard_child.key,
            root_terrain.key,
            terrain_deep.key,
            capstone.key,
        )
        prof = dict(char.db.skill_proficiency or {})
        char.db.skill_proficiency = prof
        self.assertFalse(can_use_skill(char, capstone))
        self.assertIsNotNone(missing_prerequisite(char, capstone))

        prof["synth_e_guard_child"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        char.db.skill_proficiency = prof
        self.assertFalse(can_use_skill(char, capstone))
        self.assertEqual(
            missing_prerequisite(char, capstone).skill_key,
            "synth_e_terrain_deep",
        )

        prof["synth_e_terrain_deep"] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        char.db.skill_proficiency = prof
        self.assertTrue(can_use_skill(char, capstone))
        self.assertIsNone(missing_prerequisite(char, capstone))

    # --- Scenario: Retired dev-era bindings resolve as ordinary rejections

    @covers_requirement(
        "skill-registry::earth-spell-progression-composes-executable-terrain-and-guard-behavior"
    )
    def test_retired_dev_era_bindings_resolve_as_ordinary_rejections(self):
        """Retired bind/root keys reject exactly like never-existing keys through cast and buff paths."""
        for key in ("earth_bind", "earth_root", "never_existed_key"):
            with self.subTest(key=key):
                res = self._cast(self.caster, key, [self.foe])
                self.assertEqual(res.outcome, "rejected")
                self.assertEqual(res.reason, RejectReason.UNKNOWN_SKILL)
        with self.assertRaises(KeyError):
            apply_buff(self.foe, "earth_root")
        with self.assertRaises(KeyError):
            apply_buff(self.foe, "earth_bind")
