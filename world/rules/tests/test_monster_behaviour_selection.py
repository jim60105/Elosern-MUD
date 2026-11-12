"""Skill, enemy, and tie-break selection tests."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
from unittest.mock import patch

from world.rules import combat_modifiers
from world.rules.combat import Battlefield
from world.rules.monster_behaviour import (
    _choose_skill,
    _choose_target,
    _living_enemies,
    _owned_damage_skills,
    _reflex_estimates,
)
from world.rules.rulebook.schema import Rule
from world.skills.effects import EffectPolicy
from world.skills.registry import SkillKind, TargetSpec

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    open_synthetic_scope,
    synth_damage_skill,
)
from .combat_fixtures import FakeEntity, FakeGauge
from world.rules.combat_identity import stable_actor_id

# File-local synthetic rows (data independence): a passive, a non-damage
# active, a zero-cost physical strike, and an MP-costing magic spell. Their
# relative costs/stats are authored here, so every expectation below names
# its own numbers.
_T_PASSIVE = synth_damage_skill(
    "t_guard_shell", "合成護殼", effects=["passive_buff:t_guard_shell"], kind=SkillKind.PASSIVE
)
_T_FLIGHT = synth_damage_skill("t_synth_flight", "合成飛行", effects=["movement:flight"])
_T_CLAW = synth_damage_skill("t_split_claw", "裂爪擊")
_T_SPELL = synth_damage_skill(
    "t_rain_spray",
    "瀧灑法術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 12},
)
_T_AREA = synth_damage_skill(
    "t_rain_sweep",
    "瀧灑橫掃",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 12},
    target_spec=TargetSpec.AREA,
)
# One flat atk_phys bonus rule keyed to the synthetic passive, mirroring the
# rule-table shape any shipped ownership bonus uses (see test_stat_breakdown).
_T_BONUS_PASSIVE = synth_damage_skill(
    "t_training_drill", "合成鍛鍊", effects=["passive_buff:t_training_drill"], kind=SkillKind.PASSIVE
)
_T_BONUS_RULE = Rule(
    "t_training_drill_atk_phys_bonus",
    {"skill_owned": _T_BONUS_PASSIVE.key},
    {"atk_phys": 5},
)
_SCOPE_EXTRA = {
    "skills": {
        row.key: row
        for row in (
            _T_PASSIVE,
            _T_FLIGHT,
            _T_CLAW,
            _T_SPELL,
            _T_AREA,
            _T_BONUS_PASSIVE,
        )
    }
}


class _FixedDraw:
    """The injectable selection generator: one exact uniform draw."""

    def __init__(self, draw: float):
        self.draw = draw

    def random(self) -> float:
        return self.draw


class MonsterBehaviourSelectionTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    def test_owned_damage_skills_preserve_owned_order(self):
        entity = FakeEntity(
            "actor", combat_identity='actor',
            owned=[_T_PASSIVE.key, _T_FLIGHT.key, _T_CLAW.key, _T_SPELL.key],
        )
        entity.traits.sp = FakeGauge(18, 18)
        entity.traits.mp = FakeGauge(20, 20)
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            [_T_CLAW.key, _T_SPELL.key],
        )
        entity.traits.mp.value = 0
        self.assertEqual(
            [skill.key for skill in _owned_damage_skills(entity)],
            [_T_CLAW.key],
        )
        entity.skills._owned = [_T_FLIGHT.key]
        self.assertEqual(_owned_damage_skills(entity), [])

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected",
    )
    def test_ineligible_skill_filtered_from_damage_candidates(self):
        from world.skills.registry import SkillEligibility
        ineligible_skill = replace(
            synth_damage_skill("t_ineligible_dmg", "不合身分傷害"),
            eligibility=SkillEligibility(allowed_actor_kinds=("player",))
        )
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {ineligible_skill.key: ineligible_skill}):
            entity = FakeEntity("monster_actor", combat_identity='monster_actor', owned=[ineligible_skill.key, _T_CLAW.key])
            entity.traits.sp = FakeGauge(18, 18)
            entity.traits.mp = FakeGauge(20, 20)
            self.assertEqual([s.key for s in _owned_damage_skills(entity)], [_T_CLAW.key])

    def test_living_enemies_excludes_dead_and_fled(self):
        actor = FakeEntity("actor", combat_identity='actor')
        alive = FakeEntity("alive", combat_identity='alive')
        dead = FakeEntity("dead", combat_identity='dead', hp=0, max_hp=100)
        fled = FakeEntity("fled", combat_identity='fled')
        field = Battlefield(
            {
                'monsters': frozenset({"fixture:actor"}),
                'party': frozenset({"fixture:alive", "fixture:dead", "fixture:fled"}),
            },
            {stable_actor_id(entity): entity for entity in (actor, alive, dead, fled)},
            fled={stable_actor_id(fled)},
        )
        self.assertEqual(_living_enemies(field, actor), [alive])
        field.fled.add(stable_actor_id(alive))
        self.assertEqual(_living_enemies(field, actor), [])

    @covers_requirement("monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed")
    def test_target_strategies_and_seeded_tie_break(self):
        actor = FakeEntity("actor", combat_identity='actor')
        weak = FakeEntity("weak", combat_identity='weak', hp=20, max_hp=100, atk_phys=2)
        strong = FakeEntity("strong", combat_identity='strong', hp=80, atk_phys=30)
        enemies = [weak, strong]
        self.assertIs(_choose_target(actor, enemies, "lowest_hp"), weak)
        self.assertIs(
            _choose_target(actor, enemies, "highest_effective_power"),
            strong,
        )
        first = FakeEntity("first", combat_identity='first')
        second = FakeEntity("second", combat_identity='second')
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=1,
        ) as roller:
            self.assertIs(
                _choose_target(actor, [first, second], "lowest_hp"),
                second,
            )
        roller.assert_called_once_with()

    @covers_requirement(
        "monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll",
    )
    def test_exact_estimate_is_attack_times_coefficient_times_recipients(self):
        entity = FakeEntity(
            "actor", combat_identity='actor', atk_phys=10, magic_power=10
        )
        stronger = replace(
            _T_CLAW, effect_policies=(EffectPolicy(coefficient=1.5),)
        )
        sweep = replace(
            _T_AREA, effect_policies=(EffectPolicy(coefficient=1.0),)
        )
        # 10 * 1.5 * 1 and 10 * 1.5 * 1: a SINGLE kit always counts one
        # recipient, however many enemies stand in the field.
        self.assertEqual(
            _reflex_estimates(entity, [stronger], area_recipients=1), [15.0]
        )
        self.assertEqual(
            _reflex_estimates(entity, [stronger], area_recipients=2), [15.0]
        )
        # 10 * 1.0 * 1 and 10 * 1.0 * 2: an AREA kit counts its recipients.
        self.assertEqual(
            _reflex_estimates(entity, [sweep], area_recipients=1), [10.0]
        )
        self.assertEqual(
            _reflex_estimates(entity, [sweep], area_recipients=2), [20.0]
        )

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected"
    )
    def test_the_first_damage_occurrence_supplies_the_coefficient(self):
        entity = FakeEntity("actor", combat_identity='actor', atk_phys=10)
        probe = synth_damage_skill(
            "t_ordinal_probe",
            "合成序位探針",
            effects=["self_heal", f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
        )
        probe = replace(
            probe,
            effect_policies=(
                EffectPolicy(coefficient=2.0),
                EffectPolicy(coefficient=1.5),
            ),
        )
        # 10 * 1.5 * 1: the damage occurrence's own 1.5 is read, never the
        # preceding non-damage occurrence's 2.0 (which would give 20).
        self.assertEqual(
            _reflex_estimates(entity, [probe], area_recipients=1), [15.0]
        )

    @covers_requirement(
        "combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math"
    )
    def test_each_school_reads_its_own_adjusted_attack(self):
        entity = FakeEntity(
            "actor", combat_identity='actor', atk_phys=30, magic_power=30
        )
        entity.skills._owned = [_T_BONUS_PASSIVE.key]
        with patch.object(
            combat_modifiers,
            "_RULES",
            list(combat_modifiers._RULES) + [_T_BONUS_RULE],
        ):
            # The owned 5-point atk_phys bundle enters the physical estimate...
            self.assertEqual(
                _reflex_estimates(entity, [_T_CLAW], area_recipients=1), [35.0]
            )
            # ...and never the magic one, which keeps its own adjusted value.
            self.assertEqual(
                _reflex_estimates(entity, [_T_SPELL], area_recipients=1), [30.0]
            )

    @covers_requirement(
        "monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll",
    )
    def test_a_larger_exact_estimate_is_more_probable_without_being_certain(self):
        entity = FakeEntity("actor", combat_identity='actor', atk_phys=10)
        weak = replace(
            _T_CLAW, effect_policies=(EffectPolicy(coefficient=1.0),)
        )
        strong = replace(
            _T_CLAW,
            key="t_strong_probe",
            effect_policies=(EffectPolicy(coefficient=2.0),),
        )

        def pick(draw: float) -> str:
            return _choose_skill(
                entity,
                [weak, strong],
                "highest_expected_damage",
                area_recipients=1,
                temperature=10.0,
                rng=_FixedDraw(draw),
            ).key

        # E is 10 and 20 at temperature 10, so the weak interval is
        # [0, 0.2689) and the strong one the rest of [0, 1).
        self.assertEqual(pick(0.2), weak.key)
        self.assertEqual(pick(0.5), strong.key)
        # No quantisation merges the two scores, and nothing guarantees the
        # maximum: a draw inside the strong interval is required for it.
        self.assertEqual(pick(0.1), weak.key)
        self.assertEqual(pick(0.99), strong.key)

    @covers_requirement(
        "monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll",
    )
    def test_equal_estimates_share_one_interval_apart(self):
        entity = FakeEntity("actor", combat_identity='actor', atk_phys=10)
        first = replace(
            _T_CLAW, effect_policies=(EffectPolicy(coefficient=1.0),)
        )
        second = replace(
            _T_CLAW,
            key="t_tied_probe",
            effect_policies=(EffectPolicy(coefficient=1.0),),
        )

        def pick(draw: float) -> str:
            return _choose_skill(
                entity,
                [first, second],
                "highest_expected_damage",
                area_recipients=1,
                temperature=10.0,
                rng=_FixedDraw(draw),
            ).key

        # Equal exact E is a uniform [0, 0.5) / [0.5, 1) split in owned order:
        # equal probabilities, no base-rate bonus for either position.
        self.assertEqual(pick(0.25), first.key)
        self.assertEqual(pick(0.75), second.key)

    @covers_requirement(
        "monster-action-policy::highest-expected-damage-comparison-uses-effective-value-and-one-tie-breaking-roll",
    )
    def test_fixed_seed_distribution_favours_the_stronger_estimate(self):
        entity = FakeEntity("actor", combat_identity='actor', atk_phys=10)
        weak = replace(
            _T_CLAW, effect_policies=(EffectPolicy(coefficient=1.0),)
        )
        strong = replace(
            _T_CLAW,
            key="t_strong_probe",
            effect_policies=(EffectPolicy(coefficient=2.0),),
        )

        def sweep() -> list[str]:
            return [
                _choose_skill(
                    entity,
                    [weak, strong],
                    "highest_expected_damage",
                    area_recipients=1,
                    temperature=10.0,
                    seed=seed,
                ).key
                for seed in range(200)
            ]

        chosen = sweep()
        # E = (10, 20) at temperature 10: the stronger kit must win more than
        # half of the enumerated 0..199 seeds and can never win all of them.
        self.assertGreater(chosen.count(strong.key), 100)
        self.assertLess(chosen.count(strong.key), 200)
        # The finite seed set replays exactly.
        self.assertEqual(sweep(), chosen)

    @covers_requirement(
        "monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected"
    )
    def test_first_owned_and_a_singleton_kit_evaluate_and_draw_nothing(self):
        entity = FakeEntity(
            "actor", combat_identity='actor', atk_phys=10, magic_power=10
        )
        with (
            patch(
                "world.rules.monster_behaviour._reflex_estimates",
                side_effect=AssertionError("a deterministic choice evaluated"),
            ),
            patch(
                "world.rules.monster_behaviour.dice.roll_d100"
            ) as roller,
        ):
            self.assertIs(
                _choose_skill(
                    entity,
                    [_T_CLAW, _T_SPELL],
                    "first_owned",
                    area_recipients=2,
                ),
                _T_CLAW,
            )
            self.assertIs(
                _choose_skill(
                    entity,
                    [_T_SPELL],
                    "highest_expected_damage",
                    area_recipients=2,
                    temperature=10.0,
                ),
                _T_SPELL,
            )
        roller.assert_not_called()
