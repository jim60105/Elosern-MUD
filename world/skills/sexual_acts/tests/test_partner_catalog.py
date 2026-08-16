"""Behaviour tests for the fourteen counter-gated 關係線 acts.

The two seed acts ship unconditionally in ``partner.py`` (covered by
``test_seed_acts.py``); this module covers the fourteen rows this change
adds: their counter-threshold unlock gates (including the Tier 3 compound
gate and the Tier 4 group-credit split), the symmetric duo/group counter
credits, the sole ``breast_sex_performed`` emitter, the D-4 baseline
pleasure trade-off between the two Tier 3 acts, and the D-3 regression
pinning 乳交's event recipient asymmetry.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver
from world.rules.sexual_act_effects import compute_pleasure_gain, mutator_name_for
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

_TIER_1 = (
    "partner_kiss",
    "partner_neck_caress",
    "partner_breast_play",
    "partner_ear_whisper",
)
_TIER_2 = (
    "partner_deep_caress",
    "partner_oral_service",
    "partner_breast_sex",
    "partner_thigh_rub",
    "partner_foot_service",
)
_TIER_3 = ("partner_anal_sex", "partner_mutual_masturbation")
_TIER_4 = ("partner_group_caress", "partner_group_orgy", "partner_group_service")
_ALL_ACTS = (*_TIER_1, *_TIER_2, *_TIER_3, *_TIER_4)

# The exact unlock table design.md D-1 pins, keyed per act.
_UNLOCK_TABLE = {
    "partner_kiss": {"duo_act_count": 5},
    "partner_neck_caress": {"duo_act_count": 5},
    "partner_breast_play": {"duo_act_count": 5},
    "partner_ear_whisper": {"duo_act_count": 5},
    "partner_deep_caress": {"duo_act_count": 15},
    "partner_oral_service": {"duo_act_count": 15},
    "partner_breast_sex": {"duo_act_count": 15},
    "partner_thigh_rub": {"duo_act_count": 15},
    "partner_foot_service": {"duo_act_count": 15},
    "partner_anal_sex": {"duo_act_count": 30, "climax_count": 10},
    "partner_mutual_masturbation": {"duo_act_count": 30, "climax_count": 10},
    "partner_group_caress": {"duo_act_count": 30},
    "partner_group_orgy": {"group_act_count": 15},
    "partner_group_service": {"group_act_count": 30},
}


def _entity(key="partner catalog owner", location=None):
    entity = create_object(PlayerCharacter, key=key, location=location)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _counter_up(entity, counter, times):
    # counter is a full attribute name (e.g. "duo_act_count"); the mutator
    # name comes from the sanctioned explicit table the effect pipeline uses
    # ("climax_count" → record_climax_count keeps its suffix, so a derived
    # string transform would be wrong).
    mutator = mutator_name_for(counter)
    for _ in range(times):
        getattr(entity.sexual, mutator)()


class PartnerActRegistrationTests(unittest.TestCase):
    """The fourteen rows carry exactly the D-1 unlock/event/part table."""

    @covers_requirement("sexual-catalog-partner::fourteen-tier-1-4-partner-acts-are-registered-gated-by-duo-act-count-and-or-group-act-count-and-or-climax-count-thresholds")
    def test_each_act_declares_its_d1_unlock_mapping(self):
        for key, expected in _UNLOCK_TABLE.items():
            with self.subTest(key=key):
                self.assertEqual(dict(SEXUAL_ACT_REGISTRY[key].unlock), expected)

    @covers_requirement("sexual-catalog-partner::every-tier-1-3-act-credits-duo-act-count-on-both-the-actor-and-the-target-every-tier-4-act-credits-group-act-count-on-both")
    def test_every_tier1_3_act_credits_duo_act_count_on_both_sides(self):
        for key in (*_TIER_1, *_TIER_2, *_TIER_3):
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.actor_counters, ("duo_act_count",))
                self.assertEqual(act.participant_counters, ("duo_act_count",))
                self.assertIs(SKILL_REGISTRY[key].target_spec, TargetSpec.SINGLE)
                self.assertEqual(act.actor_part, act.target_part)

    @covers_requirement("sexual-catalog-partner::every-tier-1-3-act-credits-duo-act-count-on-both-the-actor-and-the-target-every-tier-4-act-credits-group-act-count-on-both")
    def test_every_tier4_act_credits_group_act_count_on_both_sides(self):
        for key in _TIER_4:
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.actor_counters, ("group_act_count",))
                self.assertEqual(act.participant_counters, ("group_act_count",))
                self.assertIs(SKILL_REGISTRY[key].target_spec, TargetSpec.AREA)
                self.assertIsNone(act.actor_part)

    @covers_requirement("sexual-catalog-partner::partner-breast-sex-is-the-sole-emitter-of-breast-sex-performed")
    def test_only_breast_sex_declares_the_breast_sex_performed_event(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                expected = (
                    ("breast_sex_performed",)
                    if key == "partner_breast_sex"
                    else ()
                )
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].sexual_events, expected)

    @covers_requirement("sexual-catalog-partner::all-fourteen-acts-declare-resistible-true")
    def test_every_act_is_resistible(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertTrue(SEXUAL_ACT_REGISTRY[key].resistible)

    @covers_requirement("sexual-catalog-partner::none-of-this-change-s-fourteen-keys-collide-with-any-previously-registered-act-key")
    def test_new_keys_are_disjoint_from_every_pre_existing_registry_key(self):
        new_keys = set(_ALL_ACTS)
        self.assertEqual(len(new_keys), 14)
        pre_existing = set(SEXUAL_ACT_REGISTRY) - new_keys
        self.assertTrue(pre_existing.isdisjoint(new_keys))
        self.assertEqual(
            len(pre_existing),
            len(SEXUAL_ACT_REGISTRY) - 14,
        )

    @covers_requirement("sexual-catalog-partner::the-three-tier-4-acts-declare-target-part-as-a-body-parts-member-never-none")
    def test_every_area_act_declares_the_waist_target_part(self):
        for key in _TIER_4:
            with self.subTest(key=key):
                self.assertEqual(SKILL_REGISTRY[key].target_spec, TargetSpec.AREA)
                part = SEXUAL_ACT_REGISTRY[key].target_part
                self.assertEqual(part, "腰腹")
                self.assertIn(part, BODY_PARTS)


class PartnerUnlockTests(EvenniaTest):
    """The counter-threshold gates read through SkillHandler.owned_keys()."""

    @covers_requirement("sexual-catalog-partner::fourteen-tier-1-4-partner-acts-are-registered-gated-by-duo-act-count-and-or-group-act-count-and-or-climax-count-thresholds")
    def test_tier1_act_locked_below_threshold_and_unlocked_at_it(self):
        entity = _entity()
        _counter_up(entity, "duo_act_count", 4)
        self.assertNotIn("partner_kiss", entity.skills.owned_keys())
        entity.sexual.record_duo_act()
        self.assertIn("partner_kiss", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-partner::fourteen-tier-1-4-partner-acts-are-registered-gated-by-duo-act-count-and-or-group-act-count-and-or-climax-count-thresholds")
    def test_tier3_act_requires_both_duo_and_climax_not_duo_alone(self):
        entity = _entity()
        _counter_up(entity, "duo_act_count", 30)
        _counter_up(entity, "climax_count", 9)
        self.assertNotIn("partner_anal_sex", entity.skills.owned_keys())
        entity.sexual.record_climax_count()
        self.assertIn("partner_anal_sex", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-partner::fourteen-tier-1-4-partner-acts-are-registered-gated-by-duo-act-count-and-or-group-act-count-and-or-climax-count-thresholds")
    def test_group_orgy_is_gated_by_group_act_count_alone(self):
        entity = _entity()
        _counter_up(entity, "group_act_count", 15)
        self.assertEqual(entity.sexual.duo_act_count, 0)
        self.assertIn("partner_group_orgy", entity.skills.owned_keys())


class PartnerPleasureTradeOffTests(EvenniaTest):
    """D-4's baseline trade-off between the two Tier 3 acts, pinned numerically."""

    def setUp(self):
        super().setUp()
        self.entity = _entity()

    def _gain(self, base_pleasure, ratio, part):
        # participant_count == 2 is the only value either SINGLE act can reach
        # (actor + one target), resolving the crowd multiplier to 1.1.
        return compute_pleasure_gain(
            self.entity, part, base_pleasure, ratio, participant_count=2
        )

    @covers_requirement("sexual-catalog-partner::partner-anal-sex-and-partner-mutual-masturbation-are-the-two-tier-3-acts-trading-off-at-baseline-sensitivity")
    def test_anal_sex_grants_the_target_more_than_mutual_masturbation(self):
        # Target ratio is always 1.0: round(26 × 1.0 × 1.0 × 1.0 × 1.1) = 29
        # vs round(18 × 1.0 × 1.0 × 1.0 × 1.1) = 20 at baseline 普通/無.
        anal = SEXUAL_ACT_REGISTRY["partner_anal_sex"]
        mutual = SEXUAL_ACT_REGISTRY["partner_mutual_masturbation"]
        anal_gain = self._gain(anal.base_pleasure, 1.0, anal.target_part)
        mutual_gain = self._gain(mutual.base_pleasure, 1.0, mutual.target_part)
        self.assertEqual(anal_gain, 29)
        self.assertEqual(mutual_gain, 20)
        self.assertGreater(anal_gain, mutual_gain)

    @covers_requirement("sexual-catalog-partner::partner-anal-sex-and-partner-mutual-masturbation-are-the-two-tier-3-acts-trading-off-at-baseline-sensitivity")
    def test_mutual_masturbation_grants_the_actor_more_than_anal_sex(self):
        # Actor-side ratios come from the acts: round(18 × 1.0 × 1.1) = 20 vs
        # round(26 × 0.6 × 1.1) = 17 at baseline 普通/無.
        anal = SEXUAL_ACT_REGISTRY["partner_anal_sex"]
        mutual = SEXUAL_ACT_REGISTRY["partner_mutual_masturbation"]
        mutual_gain = self._gain(
            mutual.base_pleasure, mutual.actor_pleasure_ratio, mutual.actor_part
        )
        anal_gain = self._gain(
            anal.base_pleasure, anal.actor_pleasure_ratio, anal.actor_part
        )
        self.assertEqual(mutual_gain, 20)
        self.assertEqual(anal_gain, 17)
        self.assertGreater(mutual_gain, anal_gain)


class PartnerCastTests(EvenniaTest):
    """Casting the gated acts through ActionResolver credits what D-1 declares."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = _entity(key="partner catalog caster", location=self.room1)
        self.target = _entity(key="partner catalog target", location=self.room1)

    def _cast(self, actor, act_key, targets):
        # Every act this change adds is resistible=True, and the merged
        # sexual-resist-cast-wiring runs one d100 contest per non-actor target
        # inside ActionResolver.resolve(). Both fixtures are floor humans with
        # equal contest scores, so forcing roll=1 guarantees the target
        # complies and every target-side credit lands deterministically
        # (sexual-resist-cast-wiring design D-3a).
        with patch("world.rules.action.roll_d100", return_value=1):
            return ActionResolver.resolve(
                ActionRequest(
                    actor,
                    act_key,
                    targets,
                    RoomActionContext(actor.location, {}),
                )
            )

    @covers_requirement("sexual-catalog-partner::every-tier-1-3-act-credits-duo-act-count-on-both-the-actor-and-the-target-every-tier-4-act-credits-group-act-count-on-both")
    def test_every_tier1_3_act_increments_duo_act_count_on_both_participants(self):
        for key in (*_TIER_1, *_TIER_2, *_TIER_3):
            with self.subTest(key=key):
                actor = _entity(key=f"duo caster {key}", location=self.room1)
                target = _entity(key=f"duo target {key}", location=self.room1)
                act = SEXUAL_ACT_REGISTRY[key]
                _counter_up(actor, "duo_act_count", act.unlock["duo_act_count"])
                if "climax_count" in act.unlock:
                    _counter_up(actor, "climax_count", act.unlock["climax_count"])
                result = self._cast(actor, key, [target])
                self.assertEqual(result.outcome, "success", key)
                self.assertEqual(
                    actor.sexual.duo_act_count,
                    act.unlock["duo_act_count"] + 1,
                    key,
                )
                self.assertEqual(target.sexual.duo_act_count, 1, key)

    @covers_requirement("sexual-catalog-partner::every-tier-1-3-act-credits-duo-act-count-on-both-the-actor-and-the-target-every-tier-4-act-credits-group-act-count-on-both")
    def test_every_tier4_act_increments_group_act_count_not_duo_on_every_participant(self):
        for key in _TIER_4:
            with self.subTest(key=key):
                actor = _entity(key=f"group caster {key}", location=self.room1)
                targets = [
                    _entity(key=f"group target {key} {n}", location=self.room1)
                    for n in (1, 2)
                ]
                act = SEXUAL_ACT_REGISTRY[key]
                for counter, threshold in act.unlock.items():
                    _counter_up(actor, counter, threshold)
                result = self._cast(actor, key, targets)
                self.assertEqual(result.outcome, "success", key)
                self.assertEqual(
                    actor.sexual.group_act_count,
                    act.unlock.get("group_act_count", 0) + 1,
                    key,
                )
                for target in targets:
                    self.assertEqual(target.sexual.group_act_count, 1, key)
                    self.assertEqual(target.sexual.duo_act_count, 0, key)
                self.assertEqual(
                    actor.sexual.duo_act_count,
                    act.unlock.get("duo_act_count", 0),
                    key,
                )

    @covers_requirement("sexual-catalog-partner::partner-breast-sex-is-the-sole-emitter-of-breast-sex-performed")
    def test_breast_sex_credits_the_breast_sex_experience_type_to_the_target_only(self):
        # design.md D-3 regression: _handle_sexual_event fires on the cast's
        # targets only, so the breast_sex_performed → 乳交 experience credit
        # lands on the chosen partner and never on the initiating actor. This
        # pins the presently-shipped asymmetry so a future participant-expanded
        # event handler is a deliberate, visible behavior change.
        _counter_up(self.actor, "duo_act_count", 15)
        self.assertEqual(self.actor.sexual.experience_types, frozenset())
        result = self._cast(self.actor, "partner_breast_sex", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertIn("乳交", self.target.sexual.experience_types)
        self.assertNotIn("乳交", self.actor.sexual.experience_types)
