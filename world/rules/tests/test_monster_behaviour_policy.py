"""Decision-tree and structural boundary tests."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.monster_behaviour import monster_behaviour_policy

from .combat_fixtures import FakeEntity, FakeGauge


class FakeMonster(FakeEntity):
    def __init__(
        self,
        key,
        *,
        threat_tier="low",
        behaviour_tree=None,
        magic_level=30,
        **kwargs,
    ):
        # Default 30 keeps elemental spell picks castable (術師 tier); tests
        # that exercise the element-mastery gate pass magic_level=0 instead.
        super().__init__(key, magic_level=magic_level, **kwargs)
        self.threat_tier = threat_tier
        self.behaviour_tree = behaviour_tree
        self.traits.mp = FakeGauge(100, 100)
        self.traits.sp = FakeGauge(100, 100)


def _field(actor, enemies):
    entities = [actor, *enemies]
    return Battlefield(
        {
            "monsters": frozenset({actor.key}),
            "party": frozenset(enemy.key for enemy in enemies),
        },
        {entity.key: entity for entity in entities},
    )


class MonsterBehaviourPolicyTests(unittest.TestCase):
    def test_area_preference_and_single_enemy_suppression(self):
        actor = FakeMonster(
            "actor",
            threat_tier="mid",
            owned=["fire_ball", "wind_blade"],
        )
        enemies = [FakeEntity("one"), FakeEntity("two")]
        request = monster_behaviour_policy(actor, _field(actor, enemies))
        self.assertEqual(request.skill_key, "wind_blade")
        self.assertEqual(request.targets, "all-enemies")
        request = monster_behaviour_policy(actor, _field(actor, enemies[:1]))
        self.assertEqual(request.skill_key, "fire_ball")
        self.assertEqual(request.targets, enemies[:1])

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_area_fallback_and_no_eligible_skill(self):
        actor = FakeMonster("actor", owned=["wind_blade"])
        actor.traits.mp = FakeGauge(24, 24)
        enemy = FakeEntity("enemy")
        request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.targets, "all-enemies")
        actor.skills._owned = ["flight"]
        self.assertIsNone(monster_behaviour_policy(actor, _field(actor, [enemy])))

    @covers_requirement("monster-action-policy::a-non-monster-entity-is-delegated-to-change-9-s-default-attack-policy-unmodified")
    def test_non_monster_delegates_but_monster_does_not(self):
        actor = FakeEntity("actor")
        field = _field(actor, [FakeEntity("enemy")])
        sentinel = object()
        with patch(
            "world.rules.monster_behaviour.combat.default_attack_policy",
            return_value=sentinel,
        ) as default:
            self.assertIs(monster_behaviour_policy(actor, field), sentinel)
            default.assert_called_once_with(actor, field)
        monster = FakeMonster("monster", owned=[])
        field = _field(monster, [FakeEntity("enemy-two")])
        with patch(
            "world.rules.monster_behaviour.combat.default_attack_policy"
        ) as default:
            self.assertIsNone(monster_behaviour_policy(monster, field))
            default.assert_not_called()

    @covers_requirement("monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected")
    def test_unaffordable_preference_falls_back_to_affordable_skill(self):
        actor = FakeMonster(
            "actor",
            threat_tier="mid",
            owned=["wind_blade", "shadow_slash"],
        )
        actor.traits.mp = FakeGauge(0, 24)
        actor.traits.sp = FakeGauge(18, 18)
        enemies = [FakeEntity("one"), FakeEntity("two")]
        # The two affordable single-target physical skills tie on expected
        # damage, so pin the dice tie-break to the first owned candidate.
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=0,
        ):
            request = monster_behaviour_policy(actor, _field(actor, enemies))
        self.assertEqual(request.skill_key, "shadow_slash")
        self.assertNotEqual(request.targets, "all-enemies")

    def test_elemental_spell_above_the_magic_tier_is_never_chosen(self):
        # A production monster sits at magic level 0, so an owned 術師-tier
        # wind_blade cannot resolve; the policy falls back to the innate
        # physical attack instead of choosing an action the resolver rejects.
        actor = FakeMonster(
            "tierless",
            magic_level=0,
            owned=["wind_blade", "basic_attack"],
        )
        enemy = FakeEntity("enemy")
        request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.skill_key, "basic_attack")

    def test_direct_mastery_unlocks_an_elemental_spell_for_the_policy(self):
        actor = FakeMonster(
            "master",
            magic_level=0,
            owned=["wind_blade", "wind_mastery"],
        )
        enemy = FakeEntity("enemy")
        request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.skill_key, "wind_blade")

    @covers_requirement("element-mastery::can-cast-spell-tier-gates-casting-by-element-effective-numeric-level-overridden-by-direct-mastery-ownership")
    def test_malformed_element_spell_is_denied_not_raised(self):
        from world.skills.registry import SKILL_REGISTRY

        actor = FakeMonster(
            "malformed",
            magic_level=0,
            owned=["wind_blade", "basic_attack"],
        )
        enemy = FakeEntity("enemy")
        with patch(
            "world.rules.progression.can_cast_spell_tier",
            side_effect=ValueError("unknown element"),
        ):
            request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.skill_key, "basic_attack")

    def test_source_has_no_forbidden_dependencies(self):
        source = (
            Path(__file__).parents[1] / "monster_behaviour.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "combat_modifiers",
            "evaluate_combat_modifiers",
            "actions_per_turn",
            "entity.buffs",
            "entity.sexual",
            "world.ai",
            "random.choice",
        ):
            self.assertNotIn(forbidden, source)
