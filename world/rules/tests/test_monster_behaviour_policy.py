"""Decision-tree and structural boundary tests."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.monster_behaviour import monster_behaviour_policy
from world.skills.registry import TargetSpec

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    open_synthetic_scope,
    synth_damage_skill,
)
from .combat_fixtures import FakeEntity, FakeGauge


class FakeMonster(FakeEntity):
    def __init__(
        self,
        key,
        *,
        threat_tier="low",
        behaviour_tree=None,
        magic_power=30,
        **kwargs,
    ):
        # Default 30 is a harmless stat value; spell selection is gated only
        # by ownership and MP affordability (the tier gate retired).
        super().__init__(key, magic_power=magic_power, **kwargs)
        self.threat_tier = threat_tier
        self.behaviour_tree = behaviour_tree
        self.traits.mp = FakeGauge(100, 100)
        self.traits.sp = FakeGauge(100, 100)


def _field(actor, enemies):
    entities = [actor, *enemies]
    return Battlefield(
        {
            "monsters": frozenset({str(actor.key)}),
            "party": frozenset(str(entity.key) for entity in enemies),
        },
        {str(entity.key): entity for entity in entities},
    )


# File-local synthetic rows (data independence): an MP-costing single-target
# spell, an MP-costing area spell, and a free single-target physical strike.
# The 12-MP cost is authored here, so the affordability fixtures below spend
# their own numbers against it.
_T_SPELL = synth_damage_skill(
    "t_policy_spell",
    "合成單體法術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 12},
)
_T_AREA = synth_damage_skill(
    "t_policy_sweep",
    "合成範圍法術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={"mp": 12},
    target_spec=TargetSpec.AREA,
)
# Real damage effects (physically scaled, outranks any zero-magic caster's
# spell) plus a 1-SP cost: a threat tier built with zero sp cannot afford it
# and falls back to the innate attack row, mirroring the shipped zero-magic
# apex case this migration replaced.
_T_CLAW = synth_damage_skill(
    "t_policy_claw",
    "合成爪擊",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
    cost={"sp": 1},
)
# Non-damage active: owned-but-never-eligible filler.
_T_FLIGHT = synth_damage_skill("t_policy_flight", "合成飛行", effects=["movement:flight"])
_SCOPE_EXTRA = {
    "skills": {
        row.key: row
        for row in (_T_SPELL, _T_AREA, _T_CLAW, _T_FLIGHT)
    }
}


class MonsterBehaviourPolicyTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    def test_area_preference_and_single_enemy_suppression(self):
        actor = FakeMonster(
            "actor",
            threat_tier="mid",
            owned=[_T_SPELL.key, _T_AREA.key],
        )
        enemies = [FakeEntity("one"), FakeEntity("two")]
        request = monster_behaviour_policy(actor, _field(actor, enemies))
        self.assertEqual(request.skill_key, _T_AREA.key)
        self.assertEqual(request.targets, "all-enemies")
        request = monster_behaviour_policy(actor, _field(actor, enemies[:1]))
        self.assertEqual(request.skill_key, _T_SPELL.key)
        self.assertEqual(request.targets, enemies[:1])

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_area_fallback_and_no_eligible_skill(self):
        actor = FakeMonster("actor", owned=[_T_AREA.key])
        actor.traits.mp = FakeGauge(24, 24)
        enemy = FakeEntity("enemy")
        request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.targets, "all-enemies")
        actor.skills._owned = [_T_FLIGHT.key]
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
            owned=[_T_AREA.key, _T_CLAW.key],
        )
        actor.traits.mp = FakeGauge(0, 12)
        actor.traits.sp = FakeGauge(18, 18)
        enemies = [FakeEntity("one", hp=40), FakeEntity("two", hp=60)]
        # The area spell costs 12 MP the monster does not have, so only the
        # zero-cost strike remains eligible — a single-candidate choice that
        # must consume no tie-break dice (the targets differ in hp, so the
        # lowest-hp strategy is decisive too).
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100"
        ) as roller:
            request = monster_behaviour_policy(actor, _field(actor, enemies))
        roller.assert_not_called()
        self.assertEqual(request.skill_key, _T_CLAW.key)
        self.assertNotEqual(request.targets, "all-enemies")

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
