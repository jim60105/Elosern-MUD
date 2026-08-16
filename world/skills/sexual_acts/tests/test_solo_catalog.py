"""Behaviour tests for the eleven counter-gated 獨處線 acts.

The three seed acts ship unconditionally in ``solo.py`` (covered by
``test_seed_acts.py``); this module covers the eleven rows this change adds:
their counter-threshold unlock gates, the dual-counter credit of the toy
acts, and the masturbation-experience-type split.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

_TIER_1 = (
    "solo_deep_touch",
    "solo_both_hands",
    "solo_finger_lick",
    "solo_rear_touch",
    "solo_nipple_play",
)
_TIER_2 = ("solo_toy_vibrator", "solo_toy_clamps", "solo_toy_plug")
_TIER_3 = (
    "solo_toy_advanced_link",
    "solo_toy_advanced_full",
    "solo_bound_masturbation",
)
_ALL_ACTS = (*_TIER_1, *_TIER_2, *_TIER_3)

# The exact unlock table design.md D-1 pins, keyed per act.
_UNLOCK_TABLE = {
    "solo_deep_touch": {"masturbation_count": 10},
    "solo_both_hands": {"masturbation_count": 10},
    "solo_finger_lick": {"masturbation_count": 10},
    "solo_rear_touch": {"masturbation_count": 10},
    "solo_nipple_play": {"masturbation_count": 10},
    "solo_toy_vibrator": {"masturbation_count": 25},
    "solo_toy_clamps": {"masturbation_count": 25},
    "solo_toy_plug": {"masturbation_count": 25},
    "solo_toy_advanced_link": {
        "masturbation_count": 25,
        "toy_use_count": 15,
    },
    "solo_toy_advanced_full": {
        "masturbation_count": 25,
        "toy_use_count": 15,
    },
    "solo_bound_masturbation": {
        "masturbation_count": 25,
        "toy_use_count": 15,
    },
}


def _entity(key="solo catalog owner"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _masturbate(entity, times):
    for _ in range(times):
        entity.sexual.record_masturbation()


def _use_toys(entity, times):
    for _ in range(times):
        entity.sexual.record_toy_use()


class SoloActRegistrationTests(unittest.TestCase):
    """The eleven rows carry exactly the D-1 unlock/self-shape table."""

    @covers_requirement("sexual-catalog-solo::eleven-tier-1-3-solo-acts-are-registered-gated-by-masturbation-count-and-or-toy-use-count-thresholds")
    def test_each_act_declares_its_d1_unlock_mapping(self):
        for key, expected in _UNLOCK_TABLE.items():
            with self.subTest(key=key):
                self.assertEqual(dict(SEXUAL_ACT_REGISTRY[key].unlock), expected)

    @covers_requirement("sexual-catalog-solo::eleven-tier-1-3-solo-acts-are-registered-gated-by-masturbation-count-and-or-toy-use-count-thresholds")
    def test_every_act_is_a_self_targeted_unresistible_solo_act(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertEqual(SKILL_REGISTRY[key].target_spec, TargetSpec.SELF)
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertIsNone(act.target_part)
                self.assertEqual(act.participant_counters, ())
                self.assertFalse(act.resistible)

    @covers_requirement("sexual-catalog-solo::tier-2-and-tier-3-acts-credit-both-masturbation-count-and-toy-use-count-on-cast")
    def test_every_toy_act_declares_both_counters(self):
        for key in (*_TIER_2, *_TIER_3):
            with self.subTest(key=key):
                self.assertEqual(
                    SEXUAL_ACT_REGISTRY[key].actor_counters,
                    ("masturbation_count", "toy_use_count"),
                )

    @covers_requirement("sexual-catalog-solo::only-the-two-deepest-tier-1-acts-add-the-masturbation-experience-type")
    def test_only_the_two_deepest_acts_declare_the_masturbation_climax_event(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                expected = (
                    ("masturbation_climax",)
                    if key in ("solo_deep_touch", "solo_both_hands")
                    else ()
                )
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].sexual_events, expected)


class SoloUnlockTests(EvenniaTestCase):
    """The counter-threshold gates read through SkillHandler.owned_keys()."""

    @covers_requirement("sexual-catalog-solo::eleven-tier-1-3-solo-acts-are-registered-gated-by-masturbation-count-and-or-toy-use-count-thresholds")
    def test_tier1_act_locked_below_threshold_and_unlocked_at_it(self):
        entity = _entity()
        _masturbate(entity, 9)
        self.assertNotIn("solo_deep_touch", entity.skills.owned_keys())
        entity.sexual.record_masturbation()
        self.assertIn("solo_deep_touch", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-solo::eleven-tier-1-3-solo-acts-are-registered-gated-by-masturbation-count-and-or-toy-use-count-thresholds")
    def test_tier2_act_requires_masturbation_count_not_toy_use_count(self):
        entity = _entity()
        _masturbate(entity, 25)
        self.assertEqual(entity.sexual.toy_use_count, 0)
        self.assertIn("solo_toy_vibrator", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-solo::eleven-tier-1-3-solo-acts-are-registered-gated-by-masturbation-count-and-or-toy-use-count-thresholds")
    def test_tier3_act_requires_both_counters_not_toy_use_count_alone(self):
        entity = _entity()
        _masturbate(entity, 24)
        _use_toys(entity, 15)
        self.assertNotIn("solo_toy_advanced_link", entity.skills.owned_keys())
        entity.sexual.record_masturbation()
        self.assertIn("solo_toy_advanced_link", entity.skills.owned_keys())


class SoloCastTests(EvenniaTest):
    """Casting the gated acts through ActionResolver credits what D-1 declares."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(
            PlayerCharacter, key="solo catalog caster", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}

    def _cast(self, act_key):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                [],
                RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-catalog-solo::tier-2-and-tier-3-acts-credit-both-masturbation-count-and-toy-use-count-on-cast")
    def test_toy_act_increments_both_counters_by_exactly_one(self):
        _masturbate(self.actor, 25)
        result = self._cast("solo_toy_vibrator")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.masturbation_count, 26)
        self.assertEqual(self.actor.sexual.toy_use_count, 1)

    @covers_requirement("sexual-catalog-solo::tier-2-and-tier-3-acts-credit-both-masturbation-count-and-toy-use-count-on-cast")
    def test_tier3_act_also_increments_both_counters_by_exactly_one(self):
        _masturbate(self.actor, 25)
        _use_toys(self.actor, 15)
        result = self._cast("solo_toy_advanced_full")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.masturbation_count, 26)
        self.assertEqual(self.actor.sexual.toy_use_count, 16)

    @covers_requirement("sexual-catalog-solo::only-the-two-deepest-tier-1-acts-add-the-masturbation-experience-type")
    def test_solo_deep_touch_adds_the_masturbation_experience_type(self):
        _masturbate(self.actor, 10)
        self.assertEqual(self.actor.sexual.experience_types, frozenset())
        result = self._cast("solo_deep_touch")
        self.assertEqual(result.outcome, "success")
        self.assertIn("自慰", self.actor.sexual.experience_types)

    @covers_requirement("sexual-catalog-solo::only-the-two-deepest-tier-1-acts-add-the-masturbation-experience-type")
    def test_tier1_act_outside_the_deepest_two_adds_no_experience_type(self):
        _masturbate(self.actor, 10)
        result = self._cast("solo_finger_lick")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.experience_types, frozenset())
