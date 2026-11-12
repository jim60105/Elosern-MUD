"""Decision-tree and structural boundary tests."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules.combat.decision_scope import (
    ExecutionScope,
    decision_scope,
    stable_actor_id,
)
from world.rules.combat import Battlefield
from world.rules.monster_behaviour import (
    INNATE_ATTACK_KEY,
    monster_behaviour_policy,
)
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
            'monsters': frozenset({stable_actor_id(actor)}),
            'party': frozenset(stable_actor_id(entity) for entity in enemies),
        },
        {stable_actor_id(entity): entity for entity in entities},
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


class _FixedDraw:
    """The injectable selection generator: one exact uniform draw.

    Selection walks cumulative probability with a single ``random()`` call, so
    a test that pins that draw decides the outcome exactly and proves which
    interval the decision was in without asserting that the maximum wins.
    """

    def __init__(self, draw: float):
        self.draw = draw

    def random(self) -> float:
        return self.draw


def _shape(request) -> object:
    """One request's target shape: the shorthand, or the target keys."""
    if request.targets == "all-enemies":
        return "all-enemies"
    return [target.key for target in request.targets]


class MonsterBehaviourPolicyTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_single_and_area_kits_compete_in_one_selection(self):
        actor = FakeMonster(
            "actor", combat_identity='actor',
            threat_tier="mid",
            owned=[_T_SPELL.key, _T_AREA.key],
        )
        enemies = [
            FakeEntity("one", combat_identity='one', hp=40),
            FakeEntity("two", combat_identity='two', hp=60),
        ]
        # Owned 30 magic: E is 30 for the single spell and 60 for the area
        # spell with two hostile recipients, so the pinned draw 0.5 lands in
        # the area interval and the request keeps the all-enemies shorthand.
        area = monster_behaviour_policy(
            actor, _field(actor, enemies), rng=_FixedDraw(0.5)
        )
        self.assertEqual(area.skill_key, _T_AREA.key)
        self.assertEqual(area.targets, "all-enemies")
        # One living hostile leaves both estimates at 30: the shape gate is
        # gone, so the same draw decides between two equal intervals.
        single = monster_behaviour_policy(
            actor, _field(actor, enemies[:1]), rng=_FixedDraw(0.1)
        )
        self.assertEqual(single.skill_key, _T_SPELL.key)
        self.assertEqual(single.targets, enemies[:1])
        area_one = monster_behaviour_policy(
            actor, _field(actor, enemies[:1]), rng=_FixedDraw(0.9)
        )
        self.assertEqual(area_one.skill_key, _T_AREA.key)
        self.assertEqual(area_one.targets, "all-enemies")

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_the_area_flag_grants_no_reflex_admission_or_bonus(self):
        enemies = [
            FakeEntity("one", combat_identity='one', hp=40, atk_phys=5),
            FakeEntity("two", combat_identity='two', hp=60, atk_phys=70),
        ]
        # pack_hunter (mid) prefers area and brute (high) does not; every other
        # authored leaf differs too, so the assertion is that the SAME draws
        # over the same kit produce the same shapes either way: the flag is not
        # a reflex input.
        # E is 30 for the single spell and 60 for the area spell with two
        # hostile recipients, so the single interval is [0, 0.0474) and the
        # area one the rest.
        for draw, expected in ((0.01, _T_SPELL.key), (0.5, _T_AREA.key)):
            with self.subTest(draw=draw):
                shapes = []
                for tier in ("mid", "high"):
                    actor = FakeMonster(
                        f"actor-{tier}",
                        combat_identity=f"actor-{tier}",
                        threat_tier=tier,
                        owned=[_T_SPELL.key, _T_AREA.key],
                    )
                    request = monster_behaviour_policy(
                        actor, _field(actor, enemies), rng=_FixedDraw(draw)
                    )
                    self.assertEqual(request.skill_key, expected)
                    shapes.append(request.targets == "all-enemies")
                self.assertEqual(shapes, [expected == _T_AREA.key] * 2)

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_recipient_controls_leave_the_area_estimate_at_two(self):
        actor = FakeMonster(
            "actor", combat_identity='actor',
            threat_tier="mid",
            owned=[_T_SPELL.key, _T_AREA.key],
        )
        alive = [
            FakeEntity("one", combat_identity='one', hp=40),
            FakeEntity("two", combat_identity='two', hp=60),
        ]
        dead = FakeEntity("dead", combat_identity='dead', hp=0, max_hp=10)
        fled = FakeEntity("fled", combat_identity='fled')
        ally = FakeMonster("ally", combat_identity='ally')
        field = Battlefield(
            {
                'monsters': frozenset(
                    {stable_actor_id(actor), stable_actor_id(ally)}
                ),
                'party': frozenset(
                    stable_actor_id(entity) for entity in (*alive, dead, fled)
                ),
            },
            {
                stable_actor_id(entity): entity
                for entity in (actor, ally, *alive, dead, fled)
            },
            fled={stable_actor_id(fled)},
        )
        # R = 2 gives the area kit 60 against the single kit's 30, so a pinned
        # draw of 0.4 is inside the area interval. Counting the dead, the fled
        # or the ally would put the draw inside neither interval and choose the
        # single kit instead, so this discriminates R exactly.
        request = monster_behaviour_policy(actor, field, rng=_FixedDraw(0.4))
        self.assertEqual(request.skill_key, _T_AREA.key)
        self.assertEqual(request.targets, "all-enemies")

    @covers_requirement("combat-modifier-table::damage-estimation-surfaces-mirror-the-live-adjusted-damage-math")
    def test_defender_state_never_changes_a_reflex_decision(self):
        actor = FakeMonster(
            "actor", combat_identity='actor',
            threat_tier="mid",
            owned=[_T_SPELL.key, _T_AREA.key],
        )
        soft = [
            FakeEntity("one", combat_identity='one', hp=40, defense=0, agility=0),
            FakeEntity("two", combat_identity='two', hp=60, defense=0, agility=0),
        ]
        hardened = [
            FakeEntity("one", combat_identity='one', hp=40, defense=90, agility=90),
            FakeEntity("two", combat_identity='two', hp=60, defense=90, agility=90),
        ]
        for draw in (0.01, 0.4, 0.99):
            with self.subTest(draw=draw):
                before = monster_behaviour_policy(
                    actor, _field(actor, soft), rng=_FixedDraw(draw)
                )
                after = monster_behaviour_policy(
                    actor, _field(actor, hardened), rng=_FixedDraw(draw)
                )
                self.assertEqual(before.skill_key, after.skill_key)
                self.assertEqual(_shape(before), _shape(after))

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_an_authored_area_kit_never_resolves_a_single_target(self):
        # The innate attack makes a SINGLE domain resolvable, but an authored
        # AREA kit never needs it: with two exactly tied enemies a target draw
        # would consume a combat die for a target no request can use.
        innate = synth_damage_skill(
            INNATE_ATTACK_KEY,
            "合成基本攻擊",
            effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
            cost={},
        )
        actor = FakeMonster(
            "actor", combat_identity='actor',
            owned=[_T_AREA.key, INNATE_ATTACK_KEY],
        )
        enemies = [
            FakeEntity("one", combat_identity='one', hp=50),
            FakeEntity("two", combat_identity='two', hp=50),
        ]
        with (
            patch.dict(
                "world.skills.registry.SKILL_REGISTRY", {innate.key: innate}
            ),
            patch(
                "world.rules.monster_behaviour.dice.roll_d100",
                side_effect=AssertionError("an AREA-only kit drew a target"),
            ),
        ):
            request = monster_behaviour_policy(
                actor, _field(actor, enemies)
            )
        self.assertEqual(request.skill_key, _T_AREA.key)
        self.assertEqual(request.targets, "all-enemies")

    @covers_requirement("monster-action-policy::area-versus-single-target-shape-is-decided-before-target-skill-selection-reusing-the")
    def test_only_an_authored_area_kit_still_uses_the_all_enemies_shorthand(self):
        actor = FakeMonster("actor", combat_identity='actor', owned=[_T_AREA.key])
        actor.traits.mp = FakeGauge(24, 24)
        enemy = FakeEntity("enemy", combat_identity='enemy')
        # One usable kit never samples, so no generator is consulted at all.
        request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.targets, "all-enemies")

    @covers_requirement("monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback")
    def test_no_usable_authored_kit_falls_back_to_the_innate_attack(self):
        # The innate attack is owned but never an *authored* option, so it is
        # the fallback rather than the first entry of the comparison.
        innate = synth_damage_skill(
            INNATE_ATTACK_KEY,
            "合成基本攻擊",
            effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
            cost={},
        )
        actor = FakeMonster(
            "actor", combat_identity='actor',
            owned=[_T_FLIGHT.key, INNATE_ATTACK_KEY],
        )
        enemy = FakeEntity("enemy", combat_identity='enemy')
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {innate.key: innate}
        ):
            request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.skill_key, INNATE_ATTACK_KEY)
        self.assertEqual(request.targets, [enemy])

    @covers_requirement("monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback")
    def test_an_authored_kit_precedes_the_innate_attack_in_owned_order(self):
        innate = synth_damage_skill(
            INNATE_ATTACK_KEY,
            "合成基本攻擊",
            effects=[f"damage:{SYNTH_GLOW_ELEMENT}:physical"],
            cost={},
        )
        actor = FakeMonster(
            "actor",
            combat_identity='actor',
            threat_tier="mid",
            owned=[INNATE_ATTACK_KEY, _T_CLAW.key],
        )
        actor.traits.sp = FakeGauge(18, 18)
        enemy = FakeEntity("enemy", combat_identity='enemy')
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {innate.key: innate}
        ):
            request = monster_behaviour_policy(actor, _field(actor, [enemy]))
        self.assertEqual(request.skill_key, _T_CLAW.key)

    @covers_requirement("monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback")
    def test_no_usable_kit_of_either_kind_returns_none(self):
        actor = FakeMonster(
            "actor", combat_identity='actor', owned=[_T_FLIGHT.key]
        )
        enemy = FakeEntity("enemy", combat_identity='enemy')
        self.assertIsNone(monster_behaviour_policy(actor, _field(actor, [enemy])))

    @covers_requirement("monster-action-policy::a-non-monster-entity-is-delegated-to-change-9-s-default-attack-policy-unmodified")
    def test_non_monster_delegates_but_monster_does_not(self):
        actor = FakeEntity("actor", combat_identity='actor')
        field = _field(actor, [FakeEntity("enemy", combat_identity='enemy')])
        sentinel = object()
        with patch(
            "world.rules.monster_behaviour.combat.default_attack_policy",
            return_value=sentinel,
        ) as default:
            self.assertIs(monster_behaviour_policy(actor, field), sentinel)
            default.assert_called_once_with(actor, field)
        monster = FakeMonster("monster", combat_identity='monster', owned=[])
        enemy = FakeEntity("enemy-two", combat_identity='enemy-two')
        field = _field(monster, [enemy])
        with patch(
            "world.rules.monster_behaviour.combat.default_attack_policy"
        ) as default:
            # A registered monster owns its own decision: it proposes nothing
            # rather than ever reaching the delegated non-monster policy.
            self.assertIsNone(monster_behaviour_policy(monster, field))
            default.assert_not_called()

    @covers_requirement("monster-action-policy::skill-selection-differs-by-archetype-comparing-owned-skills-by-a-dice-free-expected")
    def test_unaffordable_preference_falls_back_to_affordable_skill(self):
        actor = FakeMonster(
            "actor", combat_identity='actor',
            threat_tier="mid",
            owned=[_T_AREA.key, _T_CLAW.key],
        )
        actor.traits.mp = FakeGauge(0, 12)
        actor.traits.sp = FakeGauge(18, 18)
        enemies = [FakeEntity("one", combat_identity='one', hp=40), FakeEntity("two", combat_identity='two', hp=60)]
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


