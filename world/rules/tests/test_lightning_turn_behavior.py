"""Synthetic behavior tests for lightning turn-order mechanics and spell progression.

Covers requirement:
- skill-registry::lightning-spell-progression-composes-executable-turn-order-behavior
  - Scenario: The extra-action grant provisions its second slot while live and one after lapse
  - Scenario: The ward micro-rung marks melee attackers and the declared chance decides
  - Scenario: The self advance and the canopy tail-push relocate only the still-to-act
  - Scenario: The paralysis ladder locks at the authored rungs on family keys
  - Scenario: The three-strike 多段 rung lands three judgments in one paid cast
  - Scenario: The execution and devastation rungs price their clauses
  - Scenario: Branching and the two-parent capstone gate through the lineage engine
  - Scenario: Retired dev-era clauses resolve as ordinary rejections

All fixtures are synthetic lightning-shaped skills/buff rows driven through the
real engine paths (wave discipline: behavior tests only — zero data-catalog
tests: no key-set equality, no row mirroring, no numeric catalog pins).
"""

import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room

from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    BuffDefinition,
    apply_buff,
    blocks_action,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    missing_prerequisite,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    run_round,
)
from world.rules.combat_modifiers import (
    evaluate_combat_modifiers,
    matched_combat_modifiers,
)
from world.rules.progression import (
    can_use_skill,
)
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import (
    dispatch_outcome_reaction,
    load_state_reaction_rules,
)
from world.rules.tests._combat_session_helpers import _monster, _player
from world.rules.tests.combat_fixtures import FakeEntity, grant_lineage
from world.rules.traits import restore_gauges_to_full
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
_ELEMENT_MAP = getattr(_skills_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_skill(
    key: str,
    effects: tuple[str, ...] | list[str] = (),
    *,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = "lightning",
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


class LightningTurnBehaviorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="test_lightning_arena")
        self.actor = _player("lightning_actor")
        self.actor.location = self.room
        restore_gauges_to_full(self.actor)
        self.actor.traits.magic_power.base = 40
        self.actor.traits.atk_phys.base = 40
        self.actor.traits.defense.base = 20

        self.target = _monster("lightning_target", hp=1000)
        self.target.location = self.room
        restore_gauges_to_full(self.target)
        self.target.traits.defense.base = 20

        self.ally = _player("lightning_ally")
        self.ally.location = self.room
        restore_gauges_to_full(self.ally)

    def _register(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def test_extra_action_grant_provisions_slots_while_live_and_one_after_lapse(self):
        """Scenario: The extra-action grant provisions its second slot while live and one after lapse."""
        fast = _player("fast")
        fast.location = self.room
        slow = _player("slow")
        slow.location = self.room
        bf = Battlefield(
            {"team_a": frozenset({"fast"}), "team_b": frozenset({"slow"})},
            {"fast": fast, "slow": slow},
        )

        # 1. Mount is live: evaluate_combat_modifiers returns actions_per_turn: 2
        apply_buff(fast, "lightning_extra_action")
        self.assertEqual(evaluate_combat_modifiers(fast), {"actions_per_turn": 2})

        calls: list[str] = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "slow"]),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(bf, lambda entity, field: calls.append(entity.key) or None)

        # fast received exactly two action slots, slow received one
        self.assertEqual(calls, ["fast", "fast", "slow"])

        # 2. Mount is allowed to lapse: tick_buffs expires it after 12s
        tick_buffs(fast, 12)
        self.assertNotIn("lightning_extra_action", entity_active_buffs(fast))
        self.assertEqual(evaluate_combat_modifiers(fast), {})

        calls.clear()
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "slow"]),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(bf, lambda entity, field: calls.append(entity.key) or None)

        # Lapsed combatant receives exactly one slot, slow receives one
        self.assertEqual(calls, ["fast", "slow"])

    def test_ward_micro_rung_marks_melee_attackers_and_chance_decides(self):
        """Scenario: The ward micro-rung marks melee attackers and the declared chance decides."""
        ward_carrier = self.actor
        attacker = self.target

        # Mount static_ward
        apply_buff(ward_carrier, "lightning_static_ward")
        self.assertIn("lightning_static_ward", entity_active_buffs(ward_carrier))

        # Real state reaction rules for static_ward
        reactions = load_state_reaction_rules()

        # Landed physical attack: dispatch_outcome_reaction with physical_hit
        dispatch_outcome_reaction(
            ward_carrier,
            "physical_hit",
            source=attacker,
            rules=reactions,
        )

        # Attacker received the static_ward_stun marker, ward_carrier did not
        self.assertIn("static_ward_stun", entity_active_buffs(attacker))
        self.assertNotIn("static_ward_stun", entity_active_buffs(ward_carrier))

        # Attacker carries round_order: retreat_to_tail and matched rule with chance 15
        matched = dict(matched_combat_modifiers(attacker))
        self.assertIn("static_ward_micro_stun", matched)
        self.assertEqual(matched["static_ward_micro_stun"], {"actions_per_turn": 0, "chance": 15})

        # Sourceless write: source=None -> applies nothing
        dispatch_outcome_reaction(
            ward_carrier,
            "physical_hit",
            source=None,
            rules=reactions,
        )

        # Magic event (not physical_hit) -> applies nothing new
        dispatch_outcome_reaction(
            ward_carrier,
            "hp_loss",
            source=self.ally,
            rules=reactions,
        )
        self.assertNotIn("static_ward_stun", entity_active_buffs(self.ally))

        # Chance gate: losing dice (<= 15, e.g. 10) produces action_skipped event
        fast = _player("chance_fast")
        fast.location = self.room
        dummy = _player("chance_dummy")
        dummy.location = self.room
        bf = Battlefield(
            {"team_a": frozenset({str(fast.key)}), "team_b": frozenset({str(dummy.key)})},
            {str(fast.key): fast, str(dummy.key): dummy},
        )
        apply_buff(fast, "static_ward_stun")

        calls: list[str] = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=[str(fast.key)]),
            patch("world.rules.combat.roll_d100", return_value=10),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(bf, lambda entity, field: calls.append(entity.key) or None)

        self.assertEqual(calls, [])  # Skipped!
        skipped_entries = [e for log in logs for e in log.entries if e.kind == "action_skipped"]
        self.assertEqual(len(skipped_entries), 1)
        self.assertEqual(skipped_entries[0].data, {"chance": 15, "roll": 10})

        # Winning dice (> 15, e.g. 50) lets attacker act
        calls.clear()
        with (
            patch("world.rules.combat.roll_initiative", return_value=[str(fast.key)]),
            patch("world.rules.combat.roll_d100", return_value=50),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(bf, lambda entity, field: calls.append(entity.key) or None)

        self.assertEqual(calls, [str(fast.key)])

    def test_self_advance_and_canopy_tail_push_relocate_only_still_to_act(self):
        """Scenario: The self advance and the canopy tail-push relocate only the still-to-act."""
        p1 = _player("p1")
        p1.location = self.room
        p2 = _player("p2")
        p2.location = self.room
        p3 = _player("p3")
        p3.location = self.room
        p4 = _player("p4")
        p4.location = self.room

        bf = Battlefield(
            {"team_a": frozenset({"p1", "p2", "p4"}), "team_b": frozenset({"p3"})},
            {"p1": p1, "p2": p2, "p3": p3, "p4": p4},
        )

        # p4 carries flicker_advance (action: advance_to_head)
        apply_buff(p4, "flicker_advance")

        calls: list[str] = []
        # During round: p4 advances ahead of p2 and p3 (p1 acts first)
        def provider(entity, field):
            calls.append(entity.key)
            if entity.key == "p1":
                # p1 casts canopy pushing p2 (not yet acted) and p1 (already acted)
                apply_buff(p2, "apotheosis_retreat")
                apply_buff(p1, "apotheosis_retreat")
            return None

        with (
            patch("world.rules.combat.roll_initiative", return_value=["p1", "p2", "p3", "p4"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(bf, provider)

        # Analysis:
        # Initial: [p1, p2, p3, p4]. p4 has advance_to_head.
        # Before p1 acts, fold sees p4 has advance_to_head, moves p4 to head: [p4, p1, p2, p3].
        # p4 acts first.
        # Then p1 acts. During p1's turn, p2 gets apotheosis_retreat (retreat_to_tail) and p1 gets retreat_to_tail.
        # Remaining tail is [p2, p3].
        # p2 has retreat_to_tail, moves behind p3: [p3, p2].
        # p1 has already acted, so p1's retreat_to_tail is a no-op!
        # Execution order: p4, p1, p3, p2.
        self.assertEqual(calls, ["p4", "p1", "p3", "p2"])

    def test_paralysis_ladder_locks_at_authored_rungs_on_family_keys(self):
        """Scenario: The paralysis ladder locks at the authored rungs on family keys."""
        target = self.target

        # Base paralysis (20s)
        apply_buff(target, "paralysis")
        self.assertEqual(evaluate_combat_modifiers(target), {"actions_per_turn": 0})
        # Marker path: paralysis is in BLOCKING_BUFF_KEYS
        self.assertTrue(blocks_action(target))

        # Ticking 20s expires base paralysis
        tick_buffs(target, 20)
        self.assertNotIn("paralysis", entity_active_buffs(target))
        self.assertEqual(evaluate_combat_modifiers(target), {})
        self.assertFalse(blocks_action(target))

        # Enhanced paralysis (30s)
        apply_buff(target, "paralysis_enhanced")
        self.assertEqual(evaluate_combat_modifiers(target), {"actions_per_turn": 0})
        # Enhanced paralysis locks through rule table, not marker inventory
        self.assertFalse(blocks_action(target))

        # Ticking 30s expires enhanced paralysis
        tick_buffs(target, 30)
        self.assertNotIn("paralysis_enhanced", entity_active_buffs(target))
        self.assertEqual(evaluate_combat_modifiers(target), {})

    def test_three_strike_rung_lands_three_judgments_in_one_paid_cast(self):
        """Scenario: The three-strike 多段 rung lands three judgments in one paid cast."""
        target = _monster("combo_target", hp=2000)
        target.location = self.room

        bf = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(target.key)})},
            roster={str(self.actor.key): self.actor, str(target.key): target},
        )
        ctx = BattlefieldActionContext(battlefield=bf, event_context={"now": 100})

        # Synthetic thunder_combo: extra_strikes=2, coefficient=2.0
        combo_skill = self._register(
            _make_synth_skill(
                "t_synth_thunder_combo",
                effects=["damage:lightning:magic"],
                cost={"mp": 46},
                effect_policies=[
                    EffectPolicy(
                        coefficient=2.0,
                        damage=DamagePolicy(extra_strikes=2),
                    )
                ],
            )
        )
        grant_lineage(self.actor, [combo_skill.key])

        initial_mp = self.actor.traits.mp.current
        # All three strikes hit
        with patch("world.rules.combat.roll_d100", side_effect=[100, 100, 100]):
            req = ActionRequest(self.actor, combo_skill.key, [target], ctx)
            res = ActionResolver.resolve(req)

        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]

        # Exactly 3 rolls and 3 damage entries recorded
        self.assertEqual(len(rolls), 3)
        self.assertEqual(len(damages), 3)
        self.assertTrue(rolls[0].data.get("hit"))
        self.assertTrue(rolls[1].data.get("hit"))
        self.assertTrue(rolls[2].data.get("hit"))
        self.assertEqual(damages[0].data.get("amount"), damages[1].data.get("amount"))
        self.assertEqual(damages[1].data.get("amount"), damages[2].data.get("amount"))

        # MP paid exactly once (46 MP)
        self.assertEqual(initial_mp - self.actor.traits.mp.current, 46)

    def test_execution_and_devastation_rungs_price_their_clauses(self):
        """Scenario: The execution and devastation rungs price their clauses."""
        high_def_target = _player("high_def_target")
        high_def_target.location = self.room
        high_def_target.traits.hp.base = 1000
        restore_gauges_to_full(high_def_target)
        high_def_target.traits.defense.base = 50

        bf = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(high_def_target.key)})},
            roster={str(self.actor.key): self.actor, str(high_def_target.key): high_def_target},
        )
        ctx = BattlefieldActionContext(battlefield=bf)

        # Execution skill: coefficient=4.0, bypass_defense=True, predicate=()
        exec_skill = self._register(
            _make_synth_skill(
                "t_synth_judgement",
                effects=["damage:lightning:magic"],
                effect_policies=[
                    EffectPolicy(
                        coefficient=4.0,
                        damage=DamagePolicy(bypass_defense=True, predicate=()),
                    )
                ],
            )
        )
        grant_lineage(self.actor, [exec_skill.key])

        normal_skill = self._register(
            _make_synth_skill(
                "t_synth_normal_exec",
                effects=["damage:lightning:magic"],
                effect_policies=[EffectPolicy(coefficient=4.0)],
            )
        )
        grant_lineage(self.actor, [exec_skill.key, normal_skill.key])

        with patch("world.rules.combat.roll_d100", return_value=100):
            hp_start = high_def_target.traits.hp.current
            req_exec = ActionRequest(self.actor, exec_skill.key, [high_def_target], ctx)
            res_exec = ActionResolver.resolve(req_exec)
            self.assertEqual(res_exec.outcome, "success")
            exec_dmg = hp_start - high_def_target.traits.hp.current

            restore_gauges_to_full(high_def_target)
            restore_gauges_to_full(self.actor)
            req_norm = ActionRequest(self.actor, normal_skill.key, [high_def_target], ctx)
            res_norm = ActionResolver.resolve(req_norm)
            self.assertEqual(res_norm.outcome, "success")
            norm_dmg = hp_start - high_def_target.traits.hp.current

        # Execution strike bypasses defense, dealing significantly more damage
        self.assertGreater(exec_dmg, norm_dmg)

        # Devastation skill: max_hp_fraction=0.10
        full_hp_target = _monster("devast_target", hp=2000)
        full_hp_target.location = self.room
        bf2 = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(full_hp_target.key)})},
            roster={str(self.actor.key): self.actor, str(full_hp_target.key): full_hp_target},
        )
        ctx2 = BattlefieldActionContext(battlefield=bf2)

        devast_skill = self._register(
            _make_synth_skill(
                "t_synth_slaughter",
                effects=["damage:lightning:magic"],
                effect_policies=[
                    EffectPolicy(
                        coefficient=2.8,
                        damage=DamagePolicy(max_hp_fraction=0.10),
                    )
                ],
            )
        )
        non_devast_skill = self._register(
            _make_synth_skill(
                "t_synth_non_slaughter",
                effects=["damage:lightning:magic"],
                effect_policies=[EffectPolicy(coefficient=2.8)],
            )
        )
        grant_lineage(self.actor, [devast_skill.key, non_devast_skill.key])

        with patch("world.rules.combat.roll_d100", return_value=100):
            restore_gauges_to_full(self.actor)
            hp_start = full_hp_target.traits.hp.current
            req_dev = ActionRequest(self.actor, devast_skill.key, [full_hp_target], ctx2)
            res_dev = ActionResolver.resolve(req_dev)
            self.assertEqual(res_dev.outcome, "success")
            dev_dmg = hp_start - full_hp_target.traits.hp.current

            full_hp_target.traits.hp.current = hp_start
            restore_gauges_to_full(self.actor)
            req_non_dev = ActionRequest(self.actor, non_devast_skill.key, [full_hp_target], ctx2)
            res_non_dev = ActionResolver.resolve(req_non_dev)
            self.assertEqual(res_non_dev.outcome, "success")
            non_dev_dmg = hp_start - full_hp_target.traits.hp.current

        # Devastation adds 10% of 2000 max HP = 200 damage
        self.assertEqual(dev_dmg - non_dev_dmg, 200)

    def test_branching_and_two_parent_capstone_gate_through_lineage_engine(self):
        """Scenario: Branching and the two-parent capstone gate through the lineage engine."""
        # Root 1: 先制路線
        r1 = self._register(_make_synth_skill("t_r1_root"))
        flicker = self._register(
            _make_synth_skill("t_r1_flicker", prerequisites=(SkillPrerequisite(r1.key, 3),))
        )
        combo = self._register(
            _make_synth_skill("t_r1_combo", prerequisites=(SkillPrerequisite(flicker.key, 3),))
        )
        haste = self._register(
            _make_synth_skill("t_r1_haste", prerequisites=(SkillPrerequisite(combo.key, 5),))
        )
        shatter = self._register(
            _make_synth_skill("t_r1_shatter", prerequisites=(SkillPrerequisite(combo.key, 5),))
        )
        judge = self._register(
            _make_synth_skill("t_r1_judge", prerequisites=(SkillPrerequisite(haste.key, 8),))
        )

        # Root 2: 過載路線
        r2 = self._register(_make_synth_skill("t_r2_root"))
        chain = self._register(
            _make_synth_skill("t_r2_chain", prerequisites=(SkillPrerequisite(r2.key, 3),))
        )
        parabolt = self._register(
            _make_synth_skill("t_r2_parabolt", prerequisites=(SkillPrerequisite(r2.key, 3),))
        )
        strike = self._register(
            _make_synth_skill("t_r2_strike", prerequisites=(SkillPrerequisite(chain.key, 3),))
        )
        prison = self._register(
            _make_synth_skill("t_r2_prison", prerequisites=(SkillPrerequisite(parabolt.key, 3),))
        )
        heavens = self._register(
            _make_synth_skill("t_r2_heavens", prerequisites=(SkillPrerequisite(strike.key, 5),))
        )
        slaughter = self._register(
            _make_synth_skill("t_r2_slaughter", prerequisites=(SkillPrerequisite(heavens.key, 8),))
        )

        # Canopy
        canopy = self._register(
            _make_synth_skill(
                "t_canopy_apotheosis",
                prerequisites=(
                    SkillPrerequisite(judge.key, 10),
                    SkillPrerequisite(slaughter.key, 10),
                ),
            )
        )

        all_keys = [
            r1.key, flicker.key, combo.key, haste.key, shatter.key, judge.key,
            r2.key, chain.key, parabolt.key, strike.key, prison.key, heavens.key, slaughter.key,
            canopy.key,
        ]
        self.actor.db.skills = {"active": all_keys, "passive": []}
        self.actor.db.skill_proficiency = {}

        # Roots are usable immediately
        self.assertTrue(can_use_skill(self.actor, r1))
        self.assertTrue(can_use_skill(self.actor, r2))

        # Canopy is locked
        self.assertFalse(can_use_skill(self.actor, canopy))

        # Progress root 1 side
        self.assertFalse(can_use_skill(self.actor, flicker))
        self.actor.db.skill_proficiency[r1.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, flicker))

        self.actor.db.skill_proficiency[flicker.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, combo))

        self.actor.db.skill_proficiency[combo.key] = 5 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, haste))
        self.assertTrue(can_use_skill(self.actor, shatter))

        self.actor.db.skill_proficiency[haste.key] = 8 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, judge))

        # judge reaches Lv.10, but slaughter is not yet Lv.10 -> canopy locked
        self.actor.db.skill_proficiency[judge.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(self.actor, canopy))
        self.actor.db.skill_proficiency[slaughter.key] = 9 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(self.actor, canopy))

        # Bring slaughter to 10 -> canopy UNLOCKED!
        self.actor.db.skill_proficiency[slaughter.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, canopy))

    def test_retired_dev_era_clauses_resolve_as_ordinary_rejections(self):
        """Scenario: Retired dev-era clauses resolve as ordinary rejections."""
        bf = Battlefield(
            teams={"players": frozenset({str(self.actor.key)}), "enemies": frozenset({str(self.target.key)})},
            roster={str(self.actor.key): self.actor, str(self.target.key): self.target},
        )
        ctx = BattlefieldActionContext(battlefield=bf)

        # Never-existing or retired skill key rejects with UNKNOWN_SKILL
        req = ActionRequest(self.actor, "never_existing_lightning_spell", [self.target], ctx)
        pre = ActionResolver.preflight(req)
        self.assertEqual(pre.outcome, "rejected")
        self.assertEqual(pre.reason, RejectReason.UNKNOWN_SKILL)
