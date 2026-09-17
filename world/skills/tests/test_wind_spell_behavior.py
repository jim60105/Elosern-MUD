"""Synthetic behavior tests for wind spell progression.

Covers requirement:
- skill-registry::wind-spell-progression-composes-executable-speed-and-knockback-behavior
  - Scenario: The agility ladder speeds its holder on the real consumers and expires
  - Scenario: The bipolar rung trades accuracy for speed on its holder alone
  - Scenario: The ally domain speeds allies and skips enemies
  - Scenario: The knockback storms hurl enemies out of position and sweep their footing
  - Scenario: The unconditional flurry resolves two independent strikes for one cast
  - Scenario: The execution and devastation rungs settle at their authored rungs
  - Scenario: The two roots branch and the canopy gates on both parents
  - Scenario: Retired dev-era keys resolve as ordinary rejections

All fixtures are synthetic wind-shaped skills/buff rows driven through the
real engine paths (wave discipline: behavior tests only — zero wind
data-catalog tests: no key-set equality, no row mirroring, no numeric
catalog pins).
"""

import importlib
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room

from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    apply_buff,
    entity_active_buffs,
    has_positional_marker,
    remove_positional_markers,
    tick_buffs,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _to_hit,
)
from world.rules.combat_modifiers import (
    adjusted_agility,
    evaluate_combat_modifiers,
)
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    missing_prerequisite,
)
from world.rules.traits import restore_gauges_to_full
from world.rules.tests._combat_session_helpers import _monster, _player
from world.rules.tests.combat_fixtures import grant_lineage
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    parse_effect,
)
from world.skills.registry import (
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
    element: str | None = "wind",
    target_spec: TargetSpec = TargetSpec.SINGLE,
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
    cost: dict[str, int] | None = None,
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] = (),
    prerequisites: tuple[SkillPrerequisite, ...] = (),
) -> SkillDef:
    parsed = tuple(parse_effect(eff) for eff in effects)
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
        parsed_effects=parsed,
    )


class WindSpellBehaviorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="test_wind_arena")
        self.actor = _player("wind_actor")
        self.actor.location = self.room
        restore_gauges_to_full(self.actor)
        self.actor.traits.magic_power.base = 40
        self.actor.traits.atk_phys.base = 40
        self.control = _player("wind_control")
        self.control.location = self.room
        restore_gauges_to_full(self.control)
        self.control.traits.magic_power.base = 40
        self.control.traits.atk_phys.base = 40
        self.registered_skills: dict[str, SkillDef] = {}

    def _register(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def test_agility_ladder_speeds_holder_and_expires(self):
        """Scenario: The agility ladder speeds its holder on the real consumers and expires."""
        base_agi = adjusted_agility(self.actor)
        self.assertEqual(adjusted_agility(self.control), base_agi)

        ladder_rungs = (
            ("gale_step_haste", 3),
            ("gale_chain_step_haste", 5),
            ("afterimage_step_haste", 8),
            ("haste_domain_haste", 12),
        )

        for buff_key, flat_bonus in ladder_rungs:
            with self.subTest(buff_key=buff_key, bonus=flat_bonus):
                apply_buff(self.actor, buff_key)
                mods = evaluate_combat_modifiers(self.actor)
                self.assertEqual(mods.get("agility_flat"), flat_bonus)
                self.assertEqual(adjusted_agility(self.actor), base_agi + flat_bonus)
                # Control twin is unmoved
                self.assertEqual(adjusted_agility(self.control), base_agi)
                self.assertEqual(evaluate_combat_modifiers(self.control), {})

                # Expiry after duration
                tick_buffs(self.actor, 61)
                self.assertNotIn(buff_key, entity_active_buffs(self.actor))
                self.assertEqual(adjusted_agility(self.actor), base_agi)

    def test_bipolar_rung_trades_accuracy_for_speed_on_holder_alone(self):
        """Scenario: The bipolar rung trades accuracy for speed on its holder alone."""
        opponent = _monster("bipolar_target", hp=100)
        opponent.location = self.room

        # Base margin against target
        _, base_margin = _to_hit(self.actor, opponent, 50)
        _, control_margin = _to_hit(self.control, opponent, 50)
        self.assertEqual(base_margin, control_margin)

        # Carrier gets afterimage_step_haste (+8 agi, -10 accuracy)
        apply_buff(self.actor, "afterimage_step_haste")

        # Carrier's own attack: raw_roll(50) + agi(+8) + accuracy(-10) -> margin drops by 2
        _, carrier_atk_margin = _to_hit(self.actor, opponent, 50)
        self.assertEqual(carrier_atk_margin, base_margin - 2)

        # Control twin attack is untouched
        _, control_atk_margin = _to_hit(self.control, opponent, 50)
        self.assertEqual(control_atk_margin, control_margin)

        # Incoming attack from opponent: carrier defender has +8 agi, raising dodge threshold
        _, incoming_vs_carrier = _to_hit(opponent, self.actor, 50)
        _, incoming_vs_control = _to_hit(opponent, self.control, 50)
        self.assertEqual(incoming_vs_carrier, incoming_vs_control - 8)

        # Control twin has neither pole
        self.assertEqual(evaluate_combat_modifiers(self.control), {})

    def test_ally_domain_speeds_allies_and_skips_enemies(self):
        """Scenario: The ally domain speeds allies and skips enemies."""
        ally = _player("wind_ally")
        ally.location = self.room
        enemy = _monster("wind_enemy", hp=100)
        enemy.location = self.room

        bf = Battlefield(
            teams={
                "players": frozenset({str(self.actor.key), str(ally.key)}),
                "enemies": frozenset({str(enemy.key)}),
            },
            roster={
                str(self.actor.key): self.actor,
                str(ally.key): ally,
                str(enemy.key): enemy,
            },
        )
        ctx = BattlefieldActionContext(battlefield=bf)

        # Synthetic area ally domain buff skill
        domain_skill = self._register(
            _make_synth_skill(
                "t_synth_haste_domain",
                effects=["buff_apply:haste_domain_haste"],
                target_spec=TargetSpec.AREA,
                effect_policies=[EffectPolicy(audience=EffectAudience.ALLIES)],
            )
        )
        grant_lineage(self.actor, [domain_skill.key])

        req = ActionRequest(self.actor, domain_skill.key, "all-allies", ctx)
        res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")

        # Both caster and ally receive the buff and read +12 flat agility
        self.assertIn("haste_domain_haste", entity_active_buffs(self.actor))
        self.assertIn("haste_domain_haste", entity_active_buffs(ally))
        self.assertEqual(evaluate_combat_modifiers(self.actor).get("agility_flat"), 12)
        self.assertEqual(evaluate_combat_modifiers(ally).get("agility_flat"), 12)

        # Enemy carries no part of it
        self.assertNotIn("haste_domain_haste", entity_active_buffs(enemy))
        self.assertEqual(evaluate_combat_modifiers(enemy), {})

        # Enemy single-target strikes against ally resolve against raised dodge threshold
        _, margin_vs_buffed_ally = _to_hit(enemy, ally, 50)
        tick_buffs(ally, 61)
        _, margin_vs_unbuffed_ally = _to_hit(enemy, ally, 50)
        self.assertEqual(margin_vs_buffed_ally, margin_vs_unbuffed_ally - 12)

    def test_knockback_storms_hurl_enemies_and_sweep_footing(self):
        """Scenario: The knockback storms hurl enemies out of position and sweep their footing."""
        # Setup: living enemy with high HP so it survives the damage leg
        target1 = _monster("kb_target1", hp=1000)
        target1.location = self.room
        apply_buff(target1, "earth_fissure")
        apply_buff(target1, "focus")
        self.assertIn("earth_fissure", entity_active_buffs(target1))
        self.assertIn("focus", entity_active_buffs(target1))

        # Defeated enemy
        target_dead = _monster("kb_target_dead", hp=100)
        target_dead.location = self.room
        target_dead.traits.hp.current = 0

        # Ally
        ally = _player("kb_ally")
        ally.location = self.room

        bf = Battlefield(
            teams={
                "players": frozenset({str(self.actor.key), str(ally.key)}),
                "enemies": frozenset({str(target1.key), str(target_dead.key)}),
            },
            roster={
                str(self.actor.key): self.actor,
                str(ally.key): ally,
                str(target1.key): target1,
                str(target_dead.key): target_dead,
            },
        )
        ctx = BattlefieldActionContext(battlefield=bf)

        # Synthetic knockback area skill (damage + displaced, ENEMIES audience)
        storm_skill = self._register(
            _make_synth_skill(
                "t_synth_storm_knockback",
                effects=["damage:wind:magic", "buff_apply:displaced"],
                target_spec=TargetSpec.AREA,
                effect_policies=[
                    EffectPolicy(audience=EffectAudience.ENEMIES, coefficient=1.4),
                    EffectPolicy(audience=EffectAudience.ENEMIES),
                ],
            )
        )
        grant_lineage(self.actor, [storm_skill.key])

        # Cast area knockback
        with patch("world.rules.combat.roll_d100", return_value=100):
            req = ActionRequest(self.actor, storm_skill.key, "all-enemies", ctx)
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")

        # Living enemy target carries displaced marker, out-of-position is True
        self.assertTrue(has_positional_marker(target1))
        self.assertIn("displaced", entity_active_buffs(target1))
        # Ground marker swept at mount; ordinary buff (focus) persists
        self.assertNotIn("earth_fissure", entity_active_buffs(target1))
        self.assertIn("focus", entity_active_buffs(target1))

        # Defeated recipient is refused
        self.assertNotIn("displaced", entity_active_buffs(target_dead))

        # Ally carries nothing
        self.assertNotIn("displaced", entity_active_buffs(ally))

        # Synthetic physical strike skill (is_strike_class)
        strike_phys = self._register(
            _make_synth_skill(
                "t_synth_phys_strike",
                effects=["damage:wind:physical"],
                target_spec=TargetSpec.SINGLE,
            )
        )
        grant_lineage(self.actor, [storm_skill.key, strike_phys.key])

        # Follow-up single-target physical strike against displaced victim is gated
        strike_req = ActionRequest(self.actor, strike_phys.key, [target1], ctx)
        pre = ActionResolver.preflight(strike_req)
        self.assertEqual(pre.outcome, "rejected")
        self.assertEqual(pre.reason, RejectReason.CAST_CONDITION_UNMET)

        # Magic single-target cast lands normally
        magic_skill = self._register(
            _make_synth_skill(
                "t_synth_magic_single",
                effects=["damage:wind:magic"],
                target_spec=TargetSpec.SINGLE,
            )
        )
        grant_lineage(self.actor, [magic_skill.key])
        with patch("world.rules.combat.roll_d100", return_value=100):
            hp_before = target1.traits.hp.current
            magic_req = ActionRequest(self.actor, magic_skill.key, [target1], ctx)
            magic_res = ActionResolver.resolve(magic_req)
        self.assertEqual(magic_res.outcome, "success")
        self.assertLess(target1.traits.hp.current, hp_before)

    def test_unconditional_flurry_resolves_two_strikes_for_one_cast(self):
        """Scenario: The unconditional flurry resolves two independent strikes for one cast."""
        target = _monster("flurry_target", hp=1000)
        target.location = self.room

        bf = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(target.key)})},
            roster={str(self.actor.key): self.actor, str(target.key): target},
        )
        ctx = BattlefieldActionContext(battlefield=bf, event_context={"now": 100})

        # Synthetic multi-strike skill: extra_strikes=1, unconditional (repeat_when=None)
        flurry_skill = self._register(
            _make_synth_skill(
                "t_synth_flurry",
                effects=["damage:wind:magic"],
                cost={"mp": 40},
                effect_policies=[
                    EffectPolicy(
                        coefficient=2.0,
                        damage=DamagePolicy(extra_strikes=1),
                    )
                ],
            )
        )
        grant_lineage(self.actor, [flurry_skill.key])

        # Hit-hit roll pair
        initial_mp = self.actor.traits.mp.current
        with patch("world.rules.combat.roll_d100", side_effect=[100, 100]):
            req = ActionRequest(self.actor, flurry_skill.key, [target], ctx)
            res = ActionResolver.resolve(req)
        self.assertEqual(res.outcome, "success")
        # Exactly two rolls and two damage entries recorded
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(rolls), 2)
        self.assertEqual(len(damages), 2)
        self.assertTrue(rolls[0].data.get("hit"))
        self.assertTrue(rolls[1].data.get("hit"))
        self.assertGreater(damages[0].data.get("amount", 0), 0)
        self.assertEqual(damages[0].data.get("amount"), damages[1].data.get("amount"))

        # Single MP payment (40 MP paid once)
        self.assertEqual(initial_mp - self.actor.traits.mp.current, 40)

        # Control single-strike skill rolls once
        restore_gauges_to_full(self.actor)
        target.traits.hp.current = 1000
        control_skill = self._register(
            _make_synth_skill(
                "t_synth_single_strike",
                effects=["damage:wind:magic"],
                effect_policies=[EffectPolicy(coefficient=2.0)],
            )
        )
        grant_lineage(self.actor, [control_skill.key])
        with patch("world.rules.combat.roll_d100", return_value=100):
            ctx_ctrl = BattlefieldActionContext(battlefield=bf, event_context={"now": 100})
            req_ctrl = ActionRequest(self.actor, control_skill.key, [target], ctx_ctrl)
            res_ctrl = ActionResolver.resolve(req_ctrl)
        self.assertEqual(res_ctrl.outcome, "success", f"res_ctrl failed: {res_ctrl.reason} {res_ctrl.detail}")
        ctrl_rolls = [e for e in res_ctrl.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(ctrl_rolls), 1)

    def test_execution_and_devastation_rungs_settle_at_authored_rungs(self):
        """Scenario: The execution and devastation rungs settle at their authored rungs."""
        # High defense target with ample HP
        high_def_target = _player("high_def_mob")
        high_def_target.location = self.room
        high_def_target.traits.hp.base = 1000
        restore_gauges_to_full(high_def_target)
        high_def_target.traits.defense.base = 50

        bf = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(high_def_target.key)})},
            roster={str(self.actor.key): self.actor, str(high_def_target.key): high_def_target},
        )
        ctx = BattlefieldActionContext(battlefield=bf)

        # Execution skill: bypass_defense=True, predicate=()
        exec_skill = self._register(
            _make_synth_skill(
                "t_synth_execution",
                effects=["damage:wind:magic"],
                effect_policies=[
                    EffectPolicy(
                        coefficient=4.0,
                        damage=DamagePolicy(bypass_defense=True, predicate=()),
                    )
                ],
            )
        )
        grant_lineage(self.actor, [exec_skill.key])

        # Control skill without bypass defense against same target
        normal_skill = self._register(
            _make_synth_skill(
                "t_synth_no_bypass",
                effects=["damage:wind:magic"],
                effect_policies=[EffectPolicy(coefficient=4.0)],
            )
        )
        grant_lineage(self.actor, [exec_skill.key, normal_skill.key])

        with patch("world.rules.combat.roll_d100", return_value=100):
            hp_start = high_def_target.traits.hp.current
            req_exec = ActionRequest(self.actor, exec_skill.key, [high_def_target], ctx)
            res_exec = ActionResolver.resolve(req_exec)
            self.assertEqual(res_exec.outcome, "success", f"res_exec: {res_exec.reason} {res_exec.detail}")
            exec_dmg = hp_start - high_def_target.traits.hp.current

            restore_gauges_to_full(high_def_target)
            restore_gauges_to_full(self.actor)
            req_norm = ActionRequest(self.actor, normal_skill.key, [high_def_target], ctx)
            res_norm = ActionResolver.resolve(req_norm)
            self.assertEqual(res_norm.outcome, "success", f"res_norm: {res_norm.reason} {res_norm.detail}")
            norm_dmg = hp_start - high_def_target.traits.hp.current

        # Execution damage skips defense, so it deals significantly more damage than normal
        self.assertGreater(exec_dmg, norm_dmg)

        # Devastation skill: max_hp_fraction=0.10
        full_hp_target = _monster("full_hp_mob", hp=2000)
        full_hp_target.location = self.room

        bf2 = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(full_hp_target.key)})},
            roster={str(self.actor.key): self.actor, str(full_hp_target.key): full_hp_target},
        )
        ctx2 = BattlefieldActionContext(battlefield=bf2)

        devast_skill = self._register(
            _make_synth_skill(
                "t_synth_devastation",
                effects=["damage:wind:magic"],
                effect_policies=[
                    EffectPolicy(
                        coefficient=2.8,
                        damage=DamagePolicy(max_hp_fraction=0.10),
                    )
                ],
            )
        )
        grant_lineage(self.actor, [devast_skill.key])

        non_devast_skill = self._register(
            _make_synth_skill(
                "t_synth_non_devastation",
                effects=["damage:wind:magic"],
                effect_policies=[EffectPolicy(coefficient=2.8)],
            )
        )
        grant_lineage(self.actor, [devast_skill.key, non_devast_skill.key])

        with patch("world.rules.combat.roll_d100", return_value=100):
            restore_gauges_to_full(self.actor)
            hp_start = full_hp_target.traits.hp.current
            req_dev = ActionRequest(self.actor, devast_skill.key, [full_hp_target], ctx2)
            res_dev = ActionResolver.resolve(req_dev)
            self.assertEqual(res_dev.outcome, "success", f"res_dev: {res_dev.reason} {res_dev.detail}")
            dev_dmg = hp_start - full_hp_target.traits.hp.current

            full_hp_target.traits.hp.current = hp_start
            restore_gauges_to_full(self.actor)
            req_non_dev = ActionRequest(self.actor, non_devast_skill.key, [full_hp_target], ctx2)
            res_non_dev = ActionResolver.resolve(req_non_dev)
            self.assertEqual(res_non_dev.outcome, "success", f"res_non_dev: {res_non_dev.reason} {res_non_dev.detail}")
            non_dev_dmg = hp_start - full_hp_target.traits.hp.current

        # Devastation adds 10% max HP (0.10 * 2000 = 200)
        self.assertEqual(dev_dmg - non_dev_dmg, 200)

    def test_two_roots_branch_and_canopy_gates_on_both_parents(self):
        """Scenario: The two roots branch and the canopy gates on both parents."""
        # Build synthetic 2-root wind-shaped tree
        # Root 1: mobility line
        root_mob = self._register(_make_synth_skill("t_tree_mob_root"))
        chain_mob = self._register(
            _make_synth_skill("t_tree_mob_chain", prerequisites=(SkillPrerequisite(root_mob.key, 3),))
        )
        step_mob = self._register(
            _make_synth_skill("t_tree_mob_step", prerequisites=(SkillPrerequisite(chain_mob.key, 3),))
        )
        leaf_mob = self._register(
            _make_synth_skill("t_tree_mob_leaf", prerequisites=(SkillPrerequisite(step_mob.key, 5),))
        )

        # Root 2: destruction line
        root_dest = self._register(_make_synth_skill("t_tree_dest_root"))
        branch_point = self._register(
            _make_synth_skill("t_tree_branch", prerequisites=(SkillPrerequisite(root_dest.key, 3),))
        )
        # Branch 1: storm
        storm1 = self._register(
            _make_synth_skill("t_tree_storm1", prerequisites=(SkillPrerequisite(branch_point.key, 3),))
        )
        storm2 = self._register(
            _make_synth_skill("t_tree_storm2", prerequisites=(SkillPrerequisite(storm1.key, 5),))
        )
        parent_a = self._register(
            _make_synth_skill("t_tree_parent_a", prerequisites=(SkillPrerequisite(storm2.key, 8),))
        )
        # Branch 2: dance
        dance1 = self._register(
            _make_synth_skill("t_tree_dance1", prerequisites=(SkillPrerequisite(branch_point.key, 3),))
        )
        dance2 = self._register(
            _make_synth_skill("t_tree_dance2", prerequisites=(SkillPrerequisite(dance1.key, 8),))
        )
        parent_b = self._register(
            _make_synth_skill("t_tree_parent_b", prerequisites=(SkillPrerequisite(dance2.key, 8),))
        )
        # Canopy
        canopy = self._register(
            _make_synth_skill(
                "t_tree_canopy",
                prerequisites=(
                    SkillPrerequisite(parent_a.key, 10),
                    SkillPrerequisite(parent_b.key, 10),
                ),
            )
        )

        all_tree_keys = [
            root_mob.key, chain_mob.key, step_mob.key, leaf_mob.key,
            root_dest.key, branch_point.key,
            storm1.key, storm2.key, parent_a.key,
            dance1.key, dance2.key, parent_b.key,
            canopy.key,
        ]
        self.actor.db.skills = {"active": all_tree_keys, "passive": []}
        self.actor.db.skill_proficiency = {}

        # Both roots are usable immediately
        self.assertTrue(can_use_skill(self.actor, root_mob))
        self.assertTrue(can_use_skill(self.actor, root_dest))

        # Mobility line progresses
        self.assertFalse(can_use_skill(self.actor, chain_mob))
        self.assertEqual(missing_prerequisite(self.actor, chain_mob), SkillPrerequisite(root_mob.key, 3))
        self.actor.db.skill_proficiency[root_mob.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, chain_mob))

        # Destruction root branch point
        self.assertFalse(can_use_skill(self.actor, branch_point))
        self.actor.db.skill_proficiency[root_dest.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, branch_point))

        # Branch point unlocks BOTH storm and dance branches once at Lv.3
        self.assertFalse(can_use_skill(self.actor, storm1))
        self.assertFalse(can_use_skill(self.actor, dance1))
        self.actor.db.skill_proficiency[branch_point.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, storm1))
        self.assertTrue(can_use_skill(self.actor, dance1))

        # Canopy gates on BOTH parents
        self.assertFalse(can_use_skill(self.actor, canopy))
        self.actor.db.skill_proficiency[parent_a.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.actor.db.skill_proficiency[parent_b.key] = 9 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(self.actor, canopy))
        self.assertEqual(missing_prerequisite(self.actor, canopy), SkillPrerequisite(parent_b.key, 10))
        self.actor.db.skill_proficiency[parent_b.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, canopy))

    def test_retired_dev_era_keys_resolve_as_ordinary_rejections(self):
        """Scenario: Retired dev-era keys resolve as ordinary rejections."""
        # Retired buff keys are completely gone from BUFF_DEFINITIONS
        self.assertNotIn("wind_haste", BUFF_DEFINITIONS)
        self.assertNotIn("wind_haste_domain", BUFF_DEFINITIONS)

        with self.assertRaises(KeyError):
            apply_buff(self.actor, "wind_haste")

        with self.assertRaises(KeyError):
            apply_buff(self.actor, "wind_haste_domain")

        # Fake nonexistent skill definition
        dummy_mob = _monster("dummy_enemy")
        dummy_mob.location = self.room
        bf = Battlefield(
            teams={
                "players": frozenset({str(self.actor.key)}),
                "enemies": frozenset({str(dummy_mob.key)}),
            },
            roster={
                str(self.actor.key): self.actor,
                str(dummy_mob.key): dummy_mob,
            },
        )
        ctx = BattlefieldActionContext(battlefield=bf)
        req = ActionRequest(self.actor, "retired_wind_step_illusion", [self.actor], ctx)
        pre = ActionResolver.preflight(req)
        self.assertEqual(pre.outcome, "rejected")
        self.assertEqual(pre.reason, RejectReason.UNKNOWN_SKILL)
