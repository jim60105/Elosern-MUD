"""Synthetic behavior tests for martial arts (劍術／影流刀術) progression.

Covers requirement:
- skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior
  - Scenario: The strike ladder settles at its authored coefficient for its stamina price
  - Scenario: The multi-strike rungs resolve their authored number of independent rolls
  - Scenario: The execution and devastation rungs settle at their authored rungs
  - Scenario: The impairing rider slows its victim on the real consumers and expires
  - Scenario: The lingering wound drains its victim and credits the striker
  - Scenario: The canopy's self-mounted rider arms only its holder
  - Scenario: The stance gate refuses and admits the shadow line
  - Scenario: Two independent trees branch and each canopy gates on both parents
  - Scenario: Martial skills stay outside the magic ladders

All fixtures are synthetic sword/shadow-shaped skills, buffs, and modifier
rules driven through the real engine paths (wave discipline: behavior tests
only — zero martial data-catalog tests: no key-set equality, no row
mirroring, no numeric catalog pins).
"""

import importlib
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_modifiers import _RULES, adjusted_agility, evaluate_combat_modifiers
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
    freeform_scales_for,
    missing_prerequisite,
    practice_xp_amount,
    proficiency_cap,
)
from world.rules.rulebook.schema import Rule
from world.rules.tests._combat_session_helpers import _monster, _player, live_skill_registry
from world.rules.tests.combat_fixtures import grant_lineage
from world.rules.traits import restore_gauges_to_full
from world.rules.upkeep import settle_upkeep
from world.skills.cast_conditions import CastCondition, CastConditionSubject
from world.skills.cost_tiers import spell_tier_for
from world.skills.effects import DamagePolicy, EffectAudience, EffectPolicy
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


def _make_synth_skill(
    key: str,
    effects: tuple[str, ...] | list[str] = (),
    *,
    kind: SkillKind = SkillKind.ACTIVE,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    category: SkillCategory = SkillCategory.MARTIAL_ARTS,
    cost: dict[str, int] | None = None,
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] = (),
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    cast_conditions: tuple[CastCondition, ...] = (),
) -> SkillDef:
    """Build one synthetic elementless sword/shadow-shaped skill.

    ``element`` is always ``None`` (the 劍術 route's shape): every scenario
    that needs the 影流 route's stance gate reaches it through
    ``cast_conditions``, never through the element field, which this family
    does not gate on.
    """
    if not effect_policies and effects:
        effect_policies = [EffectPolicy(coefficient=1.0, audience=EffectAudience.SELECTED)]
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost={} if cost is None else cost,
        usable_out_of_combat=True,
        element=None,
        effects=list(effects),
        faction_constraint=faction_constraint,
        category=category,
        effect_policies=tuple(effect_policies),
        prerequisites=prerequisites,
        cast_conditions=cast_conditions,
    )


# Synthetic rider buffs (martial-arts-catalog D2 shape: empty-modifier flat
# mounts resolved by a paired combat_modifiers rule; the wound is a direct
# rate DoT matching the shipped 60s/10s/-8 shape).
_SYNTH_HAMSTRING = BuffDefinition(
    key="t_synth_hamstring",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="debuff",
    modifiers={},
)
_SYNTH_WOUND = BuffDefinition(
    key="t_synth_wound",
    duration=60,
    tick_interval=10,
    stacking="refresh",
    polarity="debuff",
    modifiers={"rate": {"target": "hp", "delta": -8}},
)
_SYNTH_DOMAIN = BuffDefinition(
    key="t_synth_domain",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    polarity="buff",
    modifiers={},
)
_ALL_SYNTH_BUFFS = (_SYNTH_HAMSTRING, _SYNTH_WOUND, _SYNTH_DOMAIN)

_SYNTH_HAMSTRING_RULE = Rule(
    id="t_synth_hamstring_rule",
    when={"buff_active": "t_synth_hamstring"},
    then={"agility_flat": -5},
)
_SYNTH_DOMAIN_RULE = Rule(
    id="t_synth_domain_rule",
    when={"buff_active": "t_synth_domain"},
    then={"atk_phys": 12},
)
_ALL_SYNTH_RULES = (_SYNTH_HAMSTRING_RULE, _SYNTH_DOMAIN_RULE)


class MartialArtsBehaviorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="martial_synth_room")
        self.actor = _player("martial_actor")
        self.actor.location = self.room
        restore_gauges_to_full(self.actor)
        self.actor.traits.atk_phys.base = 40

        buff_patch = patch.dict(BUFF_DEFINITIONS, {b.key: b for b in _ALL_SYNTH_BUFFS})
        buff_patch.start()
        self.addCleanup(buff_patch.stop)

        rules_patch = patch("world.rules.combat_modifiers._RULES", [*_RULES, *_ALL_SYNTH_RULES])
        rules_patch.start()
        self.addCleanup(rules_patch.stop)

    def _register(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def _battlefield(self, *others):
        roster = {str(self.actor.key): self.actor}
        enemies = set()
        allies = {str(self.actor.key)}
        for other, team in others:
            roster[str(other.key)] = other
            if team == "enemy":
                enemies.add(str(other.key))
            else:
                allies.add(str(other.key))
        teams = {"players": frozenset(allies)}
        if enemies:
            teams["enemies"] = frozenset(enemies)
        return Battlefield(teams=teams, roster=roster)

    def _cast(self, actor, key, targets, ctx, *, roll=100):
        with patch("world.rules.combat.roll_d100", return_value=roll):
            req = ActionRequest(actor, key, targets, ctx)
            return ActionResolver.resolve(req)

    # --- Scenario: The strike ladder settles at its authored coefficient for its stamina price

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_strike_ladder_settles_at_coefficient_for_stamina_price(self):
        target = _monster("ladder_target", hp=10_000)
        target.location = self.room
        target.traits.defense.base = 0
        target.traits.defense.current = 0
        ctx = BattlefieldActionContext(battlefield=self._battlefield((target, "enemy")))

        weak = self._register(
            _make_synth_skill(
                "t_synth_weak_strike",
                ["damage:none:physical"],
                cost={"sp": 8},
                effect_policies=[EffectPolicy(coefficient=1.0)],
            )
        )
        strong = self._register(
            _make_synth_skill(
                "t_synth_strong_strike",
                ["damage:none:physical"],
                cost={"sp": 8},
                effect_policies=[EffectPolicy(coefficient=2.0)],
            )
        )
        grant_lineage(self.actor, [weak.key, strong.key])

        sp_before = self.actor.traits.sp.current
        hp_before = target.traits.hp.current
        res_weak = self._cast(self.actor, weak.key, [target], ctx)
        self.assertEqual(res_weak.outcome, "success")
        weak_dmg = hp_before - target.traits.hp.current
        self.assertGreater(weak_dmg, 0)
        self.assertEqual(sp_before - self.actor.traits.sp.current, 8)

        restore_gauges_to_full(self.actor)
        hp_before = target.traits.hp.current
        res_strong = self._cast(self.actor, strong.key, [target], ctx)
        self.assertEqual(res_strong.outcome, "success")
        strong_dmg = hp_before - target.traits.hp.current
        self.assertEqual(strong_dmg, weak_dmg * 2)

        # Insufficient stamina rejects before any damage or resource change.
        self.actor.traits.sp.current = 3
        hp_before = target.traits.hp.current
        res_reject = self._cast(self.actor, weak.key, [target], ctx)
        self.assertEqual(res_reject.outcome, "rejected")
        self.assertEqual(res_reject.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(target.traits.hp.current, hp_before)
        self.assertEqual(self.actor.traits.sp.current, 3)

    # --- Scenario: The multi-strike rungs resolve their authored number of independent rolls

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_multi_strike_rungs_resolve_authored_independent_rolls(self):
        target = _monster("multi_strike_target", hp=10_000)
        target.location = self.room
        ctx = BattlefieldActionContext(battlefield=self._battlefield((target, "enemy")), event_context={"now": 100})

        two_judgment = self._register(
            _make_synth_skill(
                "t_synth_two_judgment",
                ["damage:none:physical"],
                cost={"sp": 16},
                effect_policies=[EffectPolicy(coefficient=1.4, damage=DamagePolicy(extra_strikes=1))],
            )
        )
        three_judgment = self._register(
            _make_synth_skill(
                "t_synth_three_judgment",
                ["damage:none:physical"],
                cost={"sp": 30},
                effect_policies=[EffectPolicy(coefficient=2.8, damage=DamagePolicy(extra_strikes=2))],
            )
        )
        grant_lineage(self.actor, [two_judgment.key, three_judgment.key])

        restore_gauges_to_full(self.actor)
        with patch("world.rules.combat.roll_d100", side_effect=[100, 100]):
            res = ActionResolver.resolve(ActionRequest(self.actor, two_judgment.key, [target], ctx))
        self.assertEqual(res.outcome, "success")
        rolls = [e for e in res.event_log.entries if e.kind == "roll"]
        damages = [e for e in res.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(rolls), 2)
        self.assertEqual(len(damages), 2)
        self.assertEqual(damages[0].data.get("amount"), damages[1].data.get("amount"))

        restore_gauges_to_full(self.actor)
        with patch("world.rules.combat.roll_d100", side_effect=[100, 100, 100]):
            res3 = ActionResolver.resolve(ActionRequest(self.actor, three_judgment.key, [target], ctx))
        self.assertEqual(res3.outcome, "success")
        rolls3 = [e for e in res3.event_log.entries if e.kind == "roll"]
        damages3 = [e for e in res3.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(rolls3), 3)
        self.assertEqual(len(damages3), 3)

    # --- Scenario: The execution and devastation rungs settle at their authored rungs

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_execution_and_devastation_rungs_settle_at_authored_rungs(self):
        high_def_target = _monster("high_def_target", hp=10_000)
        high_def_target.location = self.room
        high_def_target.traits.defense.base = 200
        high_def_target.traits.defense.current = 200
        ctx = BattlefieldActionContext(battlefield=self._battlefield((high_def_target, "enemy")))

        execution = self._register(
            _make_synth_skill(
                "t_synth_execution",
                ["damage:none:physical"],
                cost={"sp": 38},
                effect_policies=[
                    EffectPolicy(coefficient=4.0, damage=DamagePolicy(bypass_defense=True, predicate=()))
                ],
            )
        )
        normal = self._register(
            _make_synth_skill(
                "t_synth_no_bypass",
                ["damage:none:physical"],
                cost={"sp": 38},
                effect_policies=[EffectPolicy(coefficient=4.0)],
            )
        )
        grant_lineage(self.actor, [execution.key, normal.key])

        hp_start = high_def_target.traits.hp.current
        res_exec = self._cast(self.actor, execution.key, [high_def_target], ctx)
        self.assertEqual(res_exec.outcome, "success")
        exec_dmg = hp_start - high_def_target.traits.hp.current

        high_def_target.traits.hp.current = hp_start
        restore_gauges_to_full(self.actor)
        res_norm = self._cast(self.actor, normal.key, [high_def_target], ctx)
        self.assertEqual(res_norm.outcome, "success")
        norm_dmg = hp_start - high_def_target.traits.hp.current
        self.assertGreater(exec_dmg, norm_dmg)

        # Devastation: max_hp_fraction adds a flat 10% of max HP on a landed hit.
        full_hp_target = _monster("full_hp_target", hp=2000)
        full_hp_target.location = self.room
        full_hp_target.traits.defense.base = 0
        full_hp_target.traits.defense.current = 0
        ctx2 = BattlefieldActionContext(battlefield=self._battlefield((full_hp_target, "enemy")))

        devastation = self._register(
            _make_synth_skill(
                "t_synth_devastation",
                ["damage:none:physical"],
                cost={"sp": 36},
                effect_policies=[EffectPolicy(coefficient=2.8, damage=DamagePolicy(max_hp_fraction=0.10))],
            )
        )
        non_devastation = self._register(
            _make_synth_skill(
                "t_synth_non_devastation",
                ["damage:none:physical"],
                cost={"sp": 36},
                effect_policies=[EffectPolicy(coefficient=2.8)],
            )
        )
        grant_lineage(self.actor, [devastation.key, non_devastation.key])

        restore_gauges_to_full(self.actor)
        hp_start2 = full_hp_target.traits.hp.current
        res_dev = self._cast(self.actor, devastation.key, [full_hp_target], ctx2)
        self.assertEqual(res_dev.outcome, "success")
        dev_dmg = hp_start2 - full_hp_target.traits.hp.current

        full_hp_target.traits.hp.current = hp_start2
        restore_gauges_to_full(self.actor)
        res_non_dev = self._cast(self.actor, non_devastation.key, [full_hp_target], ctx2)
        self.assertEqual(res_non_dev.outcome, "success")
        non_dev_dmg = hp_start2 - full_hp_target.traits.hp.current
        self.assertEqual(dev_dmg - non_dev_dmg, 200)

    # --- Scenario: The impairing rider slows its victim on the real consumers and expires

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_impairing_rider_slows_victim_and_expires(self):
        victim = _monster("hamstring_victim", hp=10_000)
        victim.location = self.room
        victim.traits.agility.base = 20
        twin = _monster("hamstring_twin", hp=10_000)
        twin.location = self.room
        twin.traits.agility.base = 20
        ctx = BattlefieldActionContext(battlefield=self._battlefield((victim, "enemy"), (twin, "enemy")))

        hamstring_skill = self._register(
            _make_synth_skill(
                "t_synth_hamstring_strike",
                ["damage:none:physical", "buff_apply:t_synth_hamstring"],
                cost={"sp": 24},
                effect_policies=[EffectPolicy(coefficient=2.0), EffectPolicy()],
            )
        )
        grant_lineage(self.actor, [hamstring_skill.key])

        base_agi = adjusted_agility(victim)
        res = self._cast(self.actor, hamstring_skill.key, [victim], ctx)
        self.assertEqual(res.outcome, "success")
        self.assertIn("t_synth_hamstring", entity_active_buffs(victim))
        self.assertEqual(evaluate_combat_modifiers(victim).get("agility_flat"), -5)
        self.assertEqual(adjusted_agility(victim), base_agi - 5)

        # Untouched twin is unmoved.
        self.assertEqual(evaluate_combat_modifiers(twin), {})
        self.assertEqual(adjusted_agility(twin), adjusted_agility(victim) + 5)

        # Expiry restores base agility and clears the buff.
        tick_buffs(victim, 61)
        self.assertNotIn("t_synth_hamstring", entity_active_buffs(victim))
        self.assertEqual(evaluate_combat_modifiers(victim).get("agility_flat", 0), 0)
        self.assertEqual(adjusted_agility(victim), base_agi)

    # --- Scenario: The lingering wound drains its victim and credits the striker

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_lingering_wound_drains_victim_and_credits_striker(self):
        victim = _monster("wound_victim", hp=100)
        victim.location = self.room
        twin = _monster("wound_twin", hp=100)
        twin.location = self.room
        ctx = BattlefieldActionContext(battlefield=self._battlefield((victim, "enemy"), (twin, "enemy")))

        wound_skill = self._register(
            _make_synth_skill(
                "t_synth_wound_strike",
                ["damage:none:physical", "buff_apply:t_synth_wound"],
                cost={"sp": 28},
                effect_policies=[EffectPolicy(coefficient=2.8), EffectPolicy()],
            )
        )
        grant_lineage(self.actor, [wound_skill.key])

        # Land the strike but keep the victim's remaining HP under our
        # control for a deterministic multi-tick drain-to-defeat.
        res = self._cast(self.actor, wound_skill.key, [victim], ctx)
        self.assertEqual(res.outcome, "success")
        self.assertIn("t_synth_wound", entity_active_buffs(victim))
        victim.traits.hp.current = 20

        battlefield = ctx.battlefield
        for _ in range(2):
            records = {str(victim.key): tick_buffs(victim, 10)}
            settle_upkeep(battlefield, records)
        self.assertEqual(victim.traits.hp.current, 4)
        self.assertNotIn("t_synth_wound", entity_active_buffs(twin))
        self.assertEqual(twin.traits.hp.current, 100)

        # A further tick crosses zero HP; the defeat is credited to the striker.
        records = {str(victim.key): tick_buffs(victim, 10)}
        logs = settle_upkeep(battlefield, records)
        defeated = [e for log in logs for e in log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeated), 1)
        self.assertEqual(defeated[0].actor, self.actor.key)

    # --- Scenario: The canopy's self-mounted rider arms only its holder

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_self_mounted_rider_arms_only_its_holder(self):
        target = _monster("domain_target", hp=10_000)
        target.location = self.room
        ally = _player("domain_ally")
        ally.location = self.room
        restore_gauges_to_full(ally)
        ally.traits.atk_phys.base = 40
        ctx = BattlefieldActionContext(
            battlefield=Battlefield(
                teams={
                    "players": frozenset({str(self.actor.key), str(ally.key)}),
                    "enemies": frozenset({str(target.key)}),
                },
                roster={
                    str(self.actor.key): self.actor,
                    str(ally.key): ally,
                    str(target.key): target,
                },
            )
        )

        canopy = self._register(
            _make_synth_skill(
                "t_synth_canopy_finisher",
                ["damage:none:physical", "self_buff_apply:t_synth_domain"],
                cost={"sp": 48},
                effect_policies=[
                    EffectPolicy(coefficient=5.5, damage=DamagePolicy(bypass_defense=True, predicate=())),
                    EffectPolicy(),
                ],
            )
        )
        grant_lineage(self.actor, [canopy.key])

        base_atk = evaluate_combat_modifiers(self.actor).get("atk_phys", 0)
        res = self._cast(self.actor, canopy.key, [target], ctx)
        self.assertEqual(res.outcome, "success")

        self.assertIn("t_synth_domain", entity_active_buffs(self.actor))
        self.assertEqual(evaluate_combat_modifiers(self.actor).get("atk_phys"), base_atk + 12)

        # Neither the ally nor the struck target reads any part of it.
        self.assertNotIn("t_synth_domain", entity_active_buffs(ally))
        self.assertNotIn("t_synth_domain", entity_active_buffs(target))
        self.assertEqual(evaluate_combat_modifiers(ally).get("atk_phys", 0), 0)
        self.assertEqual(evaluate_combat_modifiers(target).get("atk_phys", 0), 0)

        tick_buffs(self.actor, 61)
        self.assertNotIn("t_synth_domain", entity_active_buffs(self.actor))
        self.assertEqual(evaluate_combat_modifiers(self.actor).get("atk_phys", 0), base_atk)

    # --- Scenario: The stance gate refuses and admits the shadow line

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_stance_gate_refuses_and_admits_the_shadow_line(self):
        target = _monster("stance_gate_target", hp=10_000)
        target.location = self.room
        ctx = BattlefieldActionContext(battlefield=self._battlefield((target, "enemy")))

        root = self._register(_make_synth_skill("t_synth_stance_root", ["damage:none:physical"], cost={"sp": 18}))
        gated = self._register(
            _make_synth_skill(
                "t_synth_stance_gated",
                ["damage:none:physical"],
                cost={"sp": 24},
                prerequisites=(SkillPrerequisite(root.key, 3),),
                cast_conditions=(
                    CastCondition(CastConditionSubject.ACTOR, {"skill_owned": "t_synth_stance"}),
                ),
            )
        )
        # `t_synth_stance` is a bare stance key the closure has never heard
        # of; grant_lineage's prerequisite walk never seeds a CastCondition
        # target, so ownership of the stance is set up independently for
        # each arm of this scenario.
        grant_lineage(self.actor, [root.key, gated.key], rungs={root.key: 3})

        # Refused without the stance: the ungated root still resolves.
        res_gated_refused = ActionResolver.preflight(
            ActionRequest(self.actor, gated.key, [target], ctx)
        )
        self.assertEqual(res_gated_refused.outcome, "rejected")
        self.assertEqual(res_gated_refused.reason, RejectReason.CAST_CONDITION_UNMET)

        res_root_before = self._cast(self.actor, root.key, [target], ctx)
        self.assertEqual(res_root_before.outcome, "success")

        # Admitted once the stance is owned.
        self.actor.db.skills = {
            "active": list(self.actor.db.skills.get("active", [])),
            "passive": [*self.actor.db.skills.get("passive", []), "t_synth_stance"],
        }
        restore_gauges_to_full(self.actor)
        res_gated_admitted = self._cast(self.actor, gated.key, [target], ctx)
        self.assertEqual(res_gated_admitted.outcome, "success")

        res_root_after = self._cast(self.actor, root.key, [target], ctx)
        self.assertEqual(res_root_after.outcome, "success")

    # --- Scenario: Two independent trees branch and each canopy gates on both parents

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_two_independent_trees_branch_and_canopies_gate_on_both_parents(self):
        # Registered before any _register() patch.dict() call: addCleanup
        # runs LIFO, so this must be the FIRST cleanup registered in this
        # test to be the LAST one to run — re-validating the lineage caches
        # only after every patch.dict() has already restored SKILL_REGISTRY,
        # never while a synthetic key is still live in it.
        self.addCleanup(validate_prerequisite_graph, live_skill_registry())

        # Tree A: a single-chain route ending in a solo tip cap.
        a_root = self._register(_make_synth_skill("t_synth_a_root"))
        a_leaf = self._register(
            _make_synth_skill("t_synth_a_leaf", prerequisites=(SkillPrerequisite(a_root.key, 3),))
        )

        # Tree B: root branches into two children converging on a two-parent canopy.
        b_root = self._register(_make_synth_skill("t_synth_b_root"))
        b_branch_x = self._register(
            _make_synth_skill("t_synth_b_branch_x", prerequisites=(SkillPrerequisite(b_root.key, 3),))
        )
        b_parent_x = self._register(
            _make_synth_skill("t_synth_b_parent_x", prerequisites=(SkillPrerequisite(b_branch_x.key, 5),))
        )
        b_branch_y = self._register(
            _make_synth_skill("t_synth_b_branch_y", prerequisites=(SkillPrerequisite(b_root.key, 3),))
        )
        b_parent_y = self._register(
            _make_synth_skill("t_synth_b_parent_y", prerequisites=(SkillPrerequisite(b_branch_y.key, 5),))
        )
        b_canopy = self._register(
            _make_synth_skill(
                "t_synth_b_canopy",
                prerequisites=(
                    SkillPrerequisite(b_parent_x.key, 10),
                    SkillPrerequisite(b_parent_y.key, 10),
                ),
            )
        )

        all_keys = [
            a_root.key, a_leaf.key,
            b_root.key, b_branch_x.key, b_parent_x.key,
            b_branch_y.key, b_parent_y.key, b_canopy.key,
        ]
        self.actor.db.skills = {"active": all_keys, "passive": []}
        self.actor.db.skill_proficiency = {}

        validate_prerequisite_graph(live_skill_registry())

        # Both roots usable immediately; no edge exists between the trees.
        self.assertTrue(can_use_skill(self.actor, a_root))
        self.assertTrue(can_use_skill(self.actor, b_root))
        self.assertFalse(can_use_skill(self.actor, a_leaf))
        self.assertFalse(can_use_skill(self.actor, b_branch_x))

        self.actor.db.skill_proficiency[a_root.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, a_leaf))

        # Tree B's root branch point admits BOTH children once met.
        self.actor.db.skill_proficiency[b_root.key] = 3 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, b_branch_x))
        self.assertTrue(can_use_skill(self.actor, b_branch_y))

        # Canopy gates on BOTH parents reaching their threshold.
        self.assertFalse(can_use_skill(self.actor, b_canopy))
        self.actor.db.skill_proficiency[b_parent_x.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.actor.db.skill_proficiency[b_parent_y.key] = 9 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertFalse(can_use_skill(self.actor, b_canopy))
        self.assertEqual(missing_prerequisite(self.actor, b_canopy), SkillPrerequisite(b_parent_y.key, 10))
        self.actor.db.skill_proficiency[b_parent_y.key] = 10 * SKILL_PROFICIENCY_XP_PER_LEVEL
        self.assertTrue(can_use_skill(self.actor, b_canopy))
        self.assertIsNone(missing_prerequisite(self.actor, b_canopy))

        # Tip caps stay derived from the shared reverse-edge map: a_root is
        # capped by a_leaf's own threshold, while the parents are capped by
        # the canopy's threshold on each of them.
        self.assertEqual(proficiency_cap(a_root.key), 3)
        self.assertEqual(proficiency_cap(b_parent_x.key), 10)
        self.assertEqual(proficiency_cap(b_parent_y.key), 10)

    # --- Scenario: Martial skills stay outside the magic ladders

    @covers_requirement(
        "skill-registry::martial-arts-progression-composes-executable-sword-and-shadow-behavior"
    )
    def test_martial_skills_stay_outside_magic_ladders(self):
        elementless = self._register(
            _make_synth_skill(
                "t_synth_neutral_strike",
                ["damage:none:physical"],
                cost={"sp": 8},
            )
        )

        affinity_actor = _player("affinity_actor")
        affinity_actor.location = self.room
        affinity_actor.db.affinity_elements = ["fire", "dark"]
        control_actor = _player("control_actor")
        control_actor.location = self.room

        affinity_amount = practice_xp_amount(affinity_actor, elementless)
        control_amount = practice_xp_amount(control_actor, elementless)
        self.assertEqual(affinity_amount, control_amount)

        # No magic-tier label for a stamina-costed, elementless martial skill.
        self.assertIsNone(spell_tier_for(elementless))

        # No freeform scale ladder for an elementless skill regardless of
        # the actor's element-mastery ownership.
        self.assertEqual(freeform_scales_for(affinity_actor, elementless), ())
