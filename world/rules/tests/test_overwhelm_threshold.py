"""Tests for deterministic overwhelm classification signals."""

from tools.spec_traceability import covers_requirement

import math
import inspect
import unittest
from unittest.mock import patch

from world.rules.combat import Battlefield, effective_power
from world.rules import combat_modifiers, overwhelm
from world.rules.rulebook.schema import Rule
from world.rules.overwhelm import (
    _agility_saturation,
    _decided_direction,
    _expected_damage_per_attack,
    commanded_damage_reaches_enemy,
    classify_overwhelm,
    estimated_rounds_to_conclude,
    hit_rate_verdict,
    power_ratio_verdict,
    team_effective_power,
)
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

from ._combat_session_helpers import live_skill_registry
from .combat_fixtures import FakeEntity


def battlefield(
    first: list[FakeEntity],
    second: list[FakeEntity],
) -> Battlefield:
    members = first + second
    return Battlefield(
        {
            "first": frozenset(entity.key for entity in first),
            "second": frozenset(entity.key for entity in second),
        },
        {entity.key: entity for entity in members},
    )


def _skill_def(key: str, effects: list[str]) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"fixture {key}",
        description="Test fixture skill for the commanded-damage query.",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=False,
        element=None,
        effects=effects,
        category=SkillCategory.UTILITY,
    )


QUERY_SKILLS = {
    definition.key: definition
    for definition in (
        _skill_def("q_damage", ["damage:fire:physical"]),
        _skill_def("q_buff", ["buff_apply:fixture_focus"]),
        _skill_def("q_heal", ["heal:single"]),
        _skill_def("q_self_heal", ["self_heal"]),
        _skill_def("q_cleanse", ["cleanse:status"]),
        _skill_def("q_debuff", ["buff_apply:fixture_curse"]),
        _skill_def("q_disguise", ["set_disguise"]),
        _skill_def("q_movement", ["movement:flight"]),
        _skill_def("q_composite", ["damage:water:magic", "buff_apply:fixture_focus"]),
        _skill_def("q_drain", ["divine_drain:測試"]),
    )
}


class PowerRatioTests(unittest.TestCase):
    def test_ratio_comparable_zero_and_inactive_members(self):
        giant = FakeEntity("giant", hp=10000, max_hp=10000, defense=100)
        small = FakeEntity("small", hp=10, max_hp=10)
        field = battlefield([giant], [small])
        self.assertEqual(power_ratio_verdict(field, "first", "second"), "first")

        peer = FakeEntity("peer", hp=10000, max_hp=10000, defense=100)
        comparable = battlefield([giant], [peer])
        self.assertIsNone(
            power_ratio_verdict(comparable, "first", "second")
        )

        small.traits.hp.value = 0
        self.assertEqual(power_ratio_verdict(field, "first", "second"), "first")
        self.assertEqual(team_effective_power(field, "second"), 0)

        ally = FakeEntity("ally", hp=100, max_hp=100)
        mixed = battlefield([giant, ally], [peer])
        giant.traits.hp.value = 0
        self.assertEqual(team_effective_power(mixed, "first"), effective_power(ally))

    @covers_requirement("overwhelm-threshold::classify-overwhelm-is-a-pure-query-recomputable-every-round-with-no-stale-state")
    def test_living_member_power_ignores_current_hp(self):
        entity = FakeEntity("entity", hp=100, max_hp=100)
        field = battlefield([entity], [FakeEntity("other")])
        before = team_effective_power(field, "first")
        entity.traits.hp.value = 1
        self.assertEqual(team_effective_power(field, "first"), before)


class HitRateTests(unittest.TestCase):
    def test_saturation_and_cross_pair_requirement(self):
        fast = FakeEntity("fast", agility=60)
        slow = FakeEntity("slow", agility=10)
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertEqual(_agility_saturation(fast, slow), "hit")
            self.assertEqual(_agility_saturation(slow, fast), "miss")
            field = battlefield([fast], [slow])
            self.assertEqual(
                hit_rate_verdict(field, "first", "second"),
                "first",
            )
            field = battlefield(
                [fast, FakeEntity("middling", agility=20)],
                [slow],
            )
            self.assertIsNone(
                hit_rate_verdict(field, "first", "second")
            )

    def test_accuracy_is_evaluated_independently(self):
        first = FakeEntity("first", agility=10)
        second = FakeEntity("second", agility=10)

        def modifiers(entity):
            return {"accuracy": 50} if entity is first else {}

        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            side_effect=modifiers,
        ):
            self.assertEqual(_agility_saturation(first, second), "hit")
            self.assertEqual(
                _agility_saturation(second, first),
                "contested",
            )
            self.assertIsNone(
                hit_rate_verdict(
                    battlefield([first], [second]),
                    "first",
                    "second",
                )
            )

    def test_fractional_modifier_matches_integer_d100_boundaries(self):
        attacker = FakeEntity("attacker", agility=59)
        defender = FakeEntity("defender", agility=100)

        def modifiers(entity):
            return {"agility": "-15%"} if entity is attacker else {}

        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            side_effect=modifiers,
        ):
            self.assertEqual(
                _agility_saturation(attacker, defender),
                "miss",
            )
            self.assertEqual(
                _expected_damage_per_attack(attacker, defender),
                0,
            )

    @covers_requirement(
        "combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math"
    )
    def test_estimate_terms_include_the_flat_bundle_bonuses(self):
        # Synthetic ownership doctrines: file-local rule-table rows (the same
        # shape every shipped flat ownership bonus uses — see
        # test_damage_effect_handler's guardian stand-in) keyed to invented
        # skill keys the fixtures own directly. The expected estimate names
        # the +5 bonuses these local rows declare.
        rules = [
            Rule(
                "t_drill_mastery_bonus",
                {"skill_owned": "t_drill_mastery"},
                {"atk_phys": 5},
            ),
            Rule(
                "t_shell_doctrine_bonus",
                {"skill_owned": "t_shell_doctrine"},
                {"defense": 5},
            ),
        ]
        attacker = FakeEntity(
            "attacker", atk_phys=20, agility=10
        )
        attacker.skills._owned = ["t_drill_mastery"]
        defender = FakeEntity("defender", defense=5, agility=10)
        defender.skills._owned = ["t_shell_doctrine"]
        with patch.object(
            combat_modifiers, "_RULES", list(combat_modifiers._RULES) + rules
        ):
            estimate = _expected_damage_per_attack(attacker, defender)
        self.assertAlmostEqual(estimate, 0.5 * (round((20 + 5) * 1.0) - (5 + 5)))


class RoundEstimateTests(unittest.TestCase):
    def test_calibration_examples(self):
        elf = FakeEntity(
            "elf",
            hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
        )
        human = FakeEntity(
            "human",
            hp=120,
            atk_phys=8,
            agility=9,
            defense=7,
            magic_power=40,
        )
        monsters = [
            FakeEntity(
                f"monster-{index}",
                hp=90,
                atk_phys=6,
                agility=6,
                defense=6,
                magic_power=0,
            )
            for index in range(3)
        ]
        apex = FakeEntity("t_apex_raider", hp=10000, atk_phys=100, agility=92)
        humans = [
            FakeEntity(
                f"human-{index}",
                hp=120,
                agility=9,
                defense=7,
            )
            for index in range(3)
        ]
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([elf], [human]),
                    "first",
                    "second",
                ),
                120 / 81,
            )
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([elf], monsters),
                    "first",
                    "second",
                ),
                270 / 82,
            )
            self.assertAlmostEqual(
                estimated_rounds_to_conclude(
                    battlefield([apex], humans),
                    "first",
                    "second",
                ),
                360 / 93,
            )
            weak = FakeEntity("weak", atk_phys=1, agility=60)
            wall = FakeEntity(
                "wall",
                hp=10000,
                max_hp=10000,
                agility=10,
                defense=999,
            )
            self.assertEqual(
                estimated_rounds_to_conclude(
                    battlefield([weak], [wall]),
                    "first",
                    "second",
                ),
                10000,
            )

    def test_estimate_uses_current_hp_and_handles_no_damage(self):
        attacker = FakeEntity("attacker", atk_phys=20, agility=60)
        defender = FakeEntity("defender", hp=100, max_hp=100, agility=10)
        field = battlefield([attacker], [defender])
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            power = team_effective_power(field, "second")
            first = estimated_rounds_to_conclude(field, "first", "second")
            defender.traits.hp.value = 50
            self.assertLess(
                estimated_rounds_to_conclude(field, "first", "second"),
                first,
            )
            self.assertEqual(team_effective_power(field, "second"), power)
            self.assertGreater(_expected_damage_per_attack(attacker, defender), 0)
            # A modifier-blind negative raw agility is clamped at 0 by the
            # shared adjusted-agility path, so unreachable comes from the
            # defender's agility instead (required roll beyond 100).
            defender.skills.values["agility"] = 1000
            self.assertTrue(
                math.isinf(
                    estimated_rounds_to_conclude(
                        field,
                        "first",
                        "second",
                    )
                )
            )


class CombinedSignalTests(unittest.TestCase):
    def test_signal_combinations_and_round_gate(self):
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            ratio = battlefield(
                [
                    FakeEntity(
                        "large",
                        hp=10000,
                        max_hp=10000,
                        atk_phys=3000,
                        agility=10,
                    )
                ],
                [FakeEntity("small", hp=10, agility=10)],
            )
            self.assertEqual(
                power_ratio_verdict(ratio, "first", "second"),
                "first",
            )
            self.assertIsNone(
                hit_rate_verdict(ratio, "first", "second")
            )
            self.assertEqual(classify_overwhelm(ratio), "first")

            rate = battlefield(
                [FakeEntity("fast", atk_phys=100, agility=60)],
                [FakeEntity("slow", hp=100, agility=10)],
            )
            self.assertIsNone(
                power_ratio_verdict(rate, "first", "second")
            )
            self.assertEqual(
                hit_rate_verdict(rate, "first", "second"),
                "first",
            )
            self.assertEqual(classify_overwhelm(rate), "first")

            contested = battlefield(
                [FakeEntity("a")],
                [FakeEntity("b")],
            )
            self.assertIsNone(classify_overwhelm(contested))

            grind = battlefield(
                [
                    FakeEntity(
                        "durable",
                        hp=100000000,
                        max_hp=100000000,
                        atk_phys=1,
                        agility=10,
                    )
                ],
                [
                    FakeEntity(
                        "wall",
                        hp=10000,
                        max_hp=10000,
                        agility=10,
                        defense=999,
                    )
                ],
            )
            self.assertEqual(
                power_ratio_verdict(grind, "first", "second"),
                "first",
            )
            self.assertIsNone(classify_overwhelm(grind))

    def test_disagreement_does_not_consult_estimate(self):
        field = battlefield([FakeEntity("a")], [FakeEntity("b")])
        with (
            patch(
                "world.rules.overwhelm.power_ratio_verdict",
                return_value="first",
            ),
            patch(
                "world.rules.overwhelm.hit_rate_verdict",
                return_value="second",
            ),
            patch(
                "world.rules.overwhelm.estimated_rounds_to_conclude"
            ) as estimate,
        ):
            self.assertIsNone(
                _decided_direction(field, "first", "second")
            )
            self.assertIsNone(classify_overwhelm(field))
            estimate.assert_not_called()

    def test_classification_recomputes_without_cached_state(self):
        strong = FakeEntity(
            "strong",
            hp=10000,
            max_hp=10000,
            atk_phys=88,
            agility=92,
            defense=90,
            magic_power=250,
        )
        weak = FakeEntity("weak", hp=120, agility=9, defense=7)
        field = battlefield([strong], [weak])
        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertEqual(classify_overwhelm(field), "first")
            self.assertEqual(classify_overwhelm(field), "first")
            strong.skills.values.update(
                atk_phys=1,
                agility=10,
                defense=1,
                magic_power=1,
            )
            self.assertIsNone(classify_overwhelm(field))


class CommandedDamageQueryTests(unittest.TestCase):
    """commanded_damage_reaches_enemy() static-read truth table and purity."""

    def field(self) -> Battlefield:
        return battlefield(
            [FakeEntity("actor"), FakeEntity("ally")],
            [FakeEntity("enemy")],
        )

    def query(self, field, skill_key, target_keys):
        with patch.dict(live_skill_registry(), QUERY_SKILLS):
            return commanded_damage_reaches_enemy(
                field, "actor", skill_key, target_keys
            )

    @covers_requirement("overwhelm-threshold::a-pure-query-answers-whether-a-commanded-action-damages-an-enemy-read-statically-from-the-skill-definition")
    def test_damage_at_enemy_is_the_only_true_skill_row(self):
        field = self.field()
        self.assertTrue(self.query(field, "q_damage", ["enemy"]))
        self.assertTrue(self.query(field, "q_composite", ["enemy"]))
        for non_damage_key in (
            "q_buff",
            "q_heal",
            "q_self_heal",
            "q_cleanse",
            "q_debuff",
            "q_disguise",
            "q_movement",
            # SexualDrainEffect moves pleasure into the caster's own pools;
            # it is deliberately not damage.
            "q_drain",
        ):
            with self.subTest(skill=non_damage_key):
                self.assertFalse(self.query(field, non_damage_key, ["enemy"]))

    @covers_requirement("overwhelm-threshold::a-pure-query-answers-whether-a-commanded-action-damages-an-enemy-read-statically-from-the-skill-definition")
    def test_damage_skill_aimed_away_from_the_enemy_team_is_false(self):
        field = self.field()
        for label, targets in (
            ("self", ["actor"]),
            ("ally", ["ally"]),
            ("nothing", []),
            ("mixed-allies", ["actor", "ally"]),
        ):
            with self.subTest(aim=label):
                self.assertFalse(self.query(field, "q_damage", targets))

    @covers_requirement("overwhelm-threshold::a-pure-query-answers-whether-a-commanded-action-damages-an-enemy-read-statically-from-the-skill-definition")
    def test_non_concrete_values_and_unknown_keys_fail_closed(self):
        field = self.field()
        # An un-resolved AREA shorthand is the caller's job to expand; as a
        # bare string it simply fails to match the enemy team.
        self.assertFalse(self.query(field, "q_damage", ["all-enemies"]))
        # A key removed from the roster after construction is not a concrete
        # roster combatant either.
        stale = self.field()
        del stale.roster["enemy"]
        self.assertFalse(self.query(stale, "q_damage", ["enemy"]))
        # An actor key on no team defines no opposing team at all.
        with patch.dict(live_skill_registry(), QUERY_SKILLS):
            self.assertFalse(
                commanded_damage_reaches_enemy(
                    field, "not-in-teams", "q_damage", ["enemy"]
                )
            )
        self.assertFalse(self.query(field, "not-in-registry", ["enemy"]))

    @covers_requirement("overwhelm-threshold::the-damage-query-is-side-effect-free-roll-free-and-recomputable")
    def test_query_is_pure_and_never_consulted_by_classify(self):
        field = self.field()

        def snapshot():
            return (
                dict(field.teams),
                list(field.roster),
                set(field.fled),
                set(field.knocked_out),
                {
                    key: (
                        entity.traits.hp.value,
                        entity.traits.hp.current,
                        entity.traits.magic_power.value,
                        dict(entity.buffs.all),
                        dict(entity.db.__dict__)
                        if hasattr(entity.db, "__dict__")
                        else None,
                    )
                    for key, entity in field.roster.items()
                },
            )

        with patch(
            "world.rules.overwhelm.evaluate_combat_modifiers",
            return_value={},
        ):
            verdict_before = classify_overwhelm(field)
            before = snapshot()
            # Any dice the query rolled would raise through this patch.
            with patch(
                "world.rules.combat.roll_d100",
                side_effect=AssertionError("query rolled dice"),
            ):
                first = self.query(field, "q_damage", ["enemy"])
                second = self.query(field, "q_damage", ["enemy"])
            self.assertTrue(first)
            self.assertEqual(first, second)
            self.assertEqual(before, snapshot())
            self.assertEqual(classify_overwhelm(field), verdict_before)

    @covers_requirement("overwhelm-threshold::the-damage-query-is-side-effect-free-roll-free-and-recomputable")
    def test_query_recomputes_instead_of_caching(self):
        # The answer follows the current registry definition and current
        # team membership: changing either between calls must change the
        # result, which a cached answer would not.
        field = self.field()
        self.assertTrue(self.query(field, "q_damage", ["enemy"]))
        moved = battlefield(
            [FakeEntity("actor"), FakeEntity("ally"), FakeEntity("enemy")],
            [FakeEntity("other")],
        )
        self.assertFalse(self.query(moved, "q_damage", ["enemy"]))
        weakened = dict(QUERY_SKILLS)
        weakened["q_damage"] = _skill_def("q_damage", ["buff_apply:fixture_focus"])
        with patch.dict(live_skill_registry(), weakened):
            self.assertFalse(
                commanded_damage_reaches_enemy(
                    self.field(), "actor", "q_damage", ["enemy"]
                )
            )
        # Implementation inspection: the query computes from a registry
        # lookup and team membership alone, and classify_overwhelm() never
        # consults it.
        query_source = inspect.getsource(overwhelm.commanded_damage_reaches_enemy)
        for forbidden in (
            "roll_d100",
            "PendingEffect",
            "ActionResolver",
            "lru_cache",
            "functools",
        ):
            self.assertNotIn(forbidden, query_source)
        self.assertNotIn(
            "commanded_damage_reaches_enemy",
            inspect.getsource(overwhelm.classify_overwhelm),
        )
