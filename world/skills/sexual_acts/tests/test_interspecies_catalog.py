"""Behaviour tests for the seven counter-gated 異種線 acts.

Covers the full line this change registers: the tiered counter-threshold
unlock gates (Tiers 1-4), the actor-only ``interspecies_act_count`` credit
against a ``Monster`` target, the parless ``target_part=None`` contract and
its ``resolve_part`` collapse to ``GENERIC_BODY_PART``, 異種交合's sole
emission of ``sexual_activity_with_nonhuman``, and the design.md D-1/D-4
regressions: the worst-case actor-gain ordering across Tiers 2→3 on the same
body part, and the presently-shipped event-recipient asymmetry that credits
異種性愛 to the Monster target, never the actor.
"""

from tools.spec_traceability import covers_requirement

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver
from world.rules.sexual_act_effects import (
    _EFFECTS_CONFIG,
    compute_pleasure_gain,
    resolve_part,
)
from world.rules.sexual_state import PLEASURE_CONFIG
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

# design.md D-1's exact unlock table, keyed per act.
_UNLOCK_TABLE = {
    "interspecies_touch": {"hostile_act_count": 10},
    "interspecies_caress": {"hostile_act_count": 10},
    "interspecies_entangle": {"hostile_act_count": 30},
    "interspecies_receive": {"hostile_act_count": 30},
    "interspecies_mating": {"hostile_act_count": 30, "climax_count": 20},
    "interspecies_domination": {"interspecies_act_count": 20},
    "interspecies_resonance": {"interspecies_act_count": 20},
}

_ALL_ACTS = tuple(_UNLOCK_TABLE)

# design.md D-1: actor body part, base pleasure, and actor-side ratio.
_ACTOR_TABLE = {
    "interspecies_touch": ("腰腹", 12, 0.5),
    "interspecies_caress": ("私處", 14, 0.6),
    "interspecies_entangle": ("腰腹", 18, 0.7),
    "interspecies_receive": ("私處", 18, 0.9),
    "interspecies_mating": ("私處", 26, 0.7),
    "interspecies_domination": ("大腿", 22, 0.6),
    "interspecies_resonance": ("乳房", 22, 0.6),
}


def _entity(key="interspecies owner"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _monster(key="interspecies target"):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier()
    monster.db.skills = {"active": [], "passive": []}
    return monster


def _counter_up(entity, counter, times):
    for _ in range(times):
        getattr(entity.sexual, f"record_{counter}")()


class InterspeciesActRegistrationTests(unittest.TestCase):
    """The seven rows carry exactly the D-1 unlock/part/ratio/event table."""

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_each_act_declares_its_d1_unlock_mapping(self):
        for key, expected in _UNLOCK_TABLE.items():
            with self.subTest(key=key):
                self.assertEqual(dict(SEXUAL_ACT_REGISTRY[key].unlock), expected)

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_every_act_declares_single_spec_actor_only_counters_and_resistibility(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                skill = SKILL_REGISTRY[key]
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertIs(skill.target_spec, TargetSpec.SINGLE)
                self.assertEqual(act.actor_counters, ("interspecies_act_count",))
                self.assertEqual(act.participant_counters, ())
                self.assertTrue(act.resistible)

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_every_act_declares_no_target_part(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertIsNone(SEXUAL_ACT_REGISTRY[key].target_part)

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_every_actor_part_is_a_body_parts_member(self):
        for key, (part, _base, _ratio) in _ACTOR_TABLE.items():
            with self.subTest(key=key):
                self.assertIn(part, BODY_PARTS)

    @covers_requirement("sexual-catalog-interspecies::interspecies-mating-is-the-sole-emitter-of-sexual-activity-with-nonhuman")
    def test_only_mating_declares_the_nonhuman_event(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                expected = (
                    ("sexual_activity_with_nonhuman",)
                    if key == "interspecies_mating"
                    else ()
                )
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].sexual_events, expected)

    @covers_requirement(
        "sexual-catalog-interspecies::interspecies-receive-declares-the-highest-actor-pleasure-ratio-among-this-change-s-seven-acts",
        "sexual-catalog-interspecies::interspecies-mating-grants-the-actor-strictly-more-pleasure-than-interspecies-receive-despite-the-lower-ratio",
    )
    def test_each_act_declares_its_d1_actor_table(self):
        for key, (part, base, ratio) in _ACTOR_TABLE.items():
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.actor_part, part)
                self.assertEqual(act.base_pleasure, base)
                self.assertEqual(act.actor_pleasure_ratio, ratio)

    @covers_requirement("sexual-catalog-interspecies::interspecies-receive-declares-the-highest-actor-pleasure-ratio-among-this-change-s-seven-acts")
    def test_receive_ratio_exceeds_every_sibling_act_ratio(self):
        receive_ratio = SEXUAL_ACT_REGISTRY["interspecies_receive"].actor_pleasure_ratio
        self.assertEqual(receive_ratio, 0.9)
        for key in _ALL_ACTS:
            if key == "interspecies_receive":
                continue
            with self.subTest(key=key):
                self.assertGreater(
                    receive_ratio,
                    SEXUAL_ACT_REGISTRY[key].actor_pleasure_ratio,
                )

    @covers_requirement("sexual-catalog-interspecies::interspecies-mating-grants-the-actor-strictly-more-pleasure-than-interspecies-receive-despite-the-lower-ratio")
    def test_worst_case_actor_gain_orders_mating_above_receive(self):
        # design.md D-1's corrected margin, values read from the registry:
        # round(26 × 0.7 × 1.0 × 0.65 × 1.1) = 13 vs
        # round(18 × 0.9 × 1.0 × 0.65 × 1.1) = 12.
        mating = SEXUAL_ACT_REGISTRY["interspecies_mating"]
        receive = SEXUAL_ACT_REGISTRY["interspecies_receive"]
        worst_case = SimpleNamespace(
            sexual=SimpleNamespace(
                sensitivity={"私處": SimpleNamespace(level="普通")},
                shame=SimpleNamespace(level="強烈"),
            )
        )
        mating_gain = compute_pleasure_gain(
            worst_case, "私處", mating.base_pleasure, mating.actor_pleasure_ratio, 2
        )
        receive_gain = compute_pleasure_gain(
            worst_case, "私處", receive.base_pleasure, receive.actor_pleasure_ratio, 2
        )
        self.assertEqual(mating_gain, 13)
        self.assertEqual(receive_gain, 12)
        self.assertGreater(mating_gain, receive_gain)

    @covers_requirement("sexual-catalog-interspecies::interspecies-mating-grants-the-actor-strictly-more-pleasure-than-interspecies-receive-despite-the-lower-ratio")
    def test_ordering_holds_for_every_shipped_multiplier_combination(self):
        # design.md D-1 claims the same-part ordering survives round() at
        # every multiplier combination the live tables can produce; enumerate
        # all 60 (sensitivity × shame × participant-count) combinations.
        mating = SEXUAL_ACT_REGISTRY["interspecies_mating"]
        receive = SEXUAL_ACT_REGISTRY["interspecies_receive"]
        for sensitivity_level in PLEASURE_CONFIG.sensitivity_multipliers:
            for shame_level in PLEASURE_CONFIG.shame_multipliers:
                for count in (1, 2, 4):
                    with self.subTest(
                        sensitivity=sensitivity_level,
                        shame=shame_level,
                        participant_count=count,
                    ):
                        participant = SimpleNamespace(
                            sexual=SimpleNamespace(
                                sensitivity={
                                    "私處": SimpleNamespace(level=sensitivity_level)
                                },
                                shame=SimpleNamespace(level=shame_level),
                            )
                        )
                        mating_gain = compute_pleasure_gain(
                            participant,
                            "私處",
                            mating.base_pleasure,
                            mating.actor_pleasure_ratio,
                            count,
                        )
                        receive_gain = compute_pleasure_gain(
                            participant,
                            "私處",
                            receive.base_pleasure,
                            receive.actor_pleasure_ratio,
                            count,
                        )
                        self.assertGreater(mating_gain, receive_gain)


class InterspeciesUnlockTests(EvenniaTestCase):
    """The counter-threshold gates read through SkillHandler.owned_keys()."""

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_tier1_act_locked_below_threshold_and_unlocked_at_it(self):
        entity = _entity()
        _counter_up(entity, "hostile_act", 9)
        self.assertNotIn("interspecies_touch", entity.skills.owned_keys())
        entity.sexual.record_hostile_act()
        self.assertIn("interspecies_touch", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_mating_requires_both_hostile_and_climax_counts(self):
        entity = _entity()
        _counter_up(entity, "hostile_act", 30)
        _counter_up(entity, "climax_count", 19)
        self.assertNotIn("interspecies_mating", entity.skills.owned_keys())
        entity.sexual.record_climax_count()
        self.assertIn("interspecies_mating", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_tier4_act_is_gated_by_interspecies_count_alone(self):
        entity = _entity()
        _counter_up(entity, "interspecies_act", 20)
        self.assertEqual(entity.sexual.hostile_act_count, 0)
        self.assertIn("interspecies_domination", entity.skills.owned_keys())


class InterspeciesCastTests(EvenniaTest):
    """Casting the gated acts through ActionResolver credits what D-1 declares."""

    def setUp(self):
        super().setUp()
        # Every cast of a resistible act resolves one contest per target; the
        # resist config validates against the quest registry, which only test
        # setup populates (same requirement sexual-resist-cast-wiring's own
        # test changes add).
        register_catalog()
        self.actor = _entity(key="interspecies caster")
        self.actor.location = self.room1
        self.monster = _monster(key="interspecies monster")
        self.monster.location = self.room1

    def _cast(self, act_key, targets):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_cast_credits_interspecies_count_on_the_actor_only(self):
        _counter_up(self.actor, "hostile_act", 10)
        self.assertEqual(self.actor.sexual.interspecies_act_count, 0)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 0)
        result = self._cast("interspecies_touch", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.interspecies_act_count, 1)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 0)

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_monster_target_resolves_to_the_generic_channel(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(
                    resolve_part(self.monster, act.target_part),
                    GENERIC_BODY_PART,
                )

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_cast_against_a_monster_applies_pleasure_through_the_generic_channel(self):
        # End-to-end proof of the generic-channel resolution: a fresh monster
        # at 普通 sensitivity / 無 shame receives round(12 × 1.0 × 1.1) = 13
        # from 觸碰異種 through resolve_part's Monster collapse. The monster's
        # resist is a pure stat contest (no affinity record), so the roll is
        # forced low — a monster at the tier floor scores 3.0 against the
        # actor's 1.0, and any roll below 49 complies — to keep the target-side
        # pleasure assertion deterministic.
        _counter_up(self.actor, "hostile_act", 10)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("interspecies_touch", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.monster.sexual.pleasure.base, 13)

    @covers_requirement("sexual-catalog-interspecies::interspecies-mating-is-the-sole-emitter-of-sexual-activity-with-nonhuman")
    def test_mating_cast_emits_the_nonhuman_event(self):
        _counter_up(self.actor, "hostile_act", 30)
        _counter_up(self.actor, "climax_count", 20)
        self.assertNotIn("異種性愛", self.monster.sexual.experience_types)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("interspecies_mating", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertIn("異種性愛", self.monster.sexual.experience_types)

    def test_mating_event_lands_on_the_monster_not_the_actor(self):
        # design.md D-4 regression, pinning the presently-shipped gap:
        # _handle_sexual_event fires on the cast's surviving targets, so
        # sexual_activity_with_nonhuman credits the Monster, never the actor.
        # A future _handle_sexual_event fix is a deliberate, visible change.
        # The monster's contest is forced to compliance (roll=1) so the
        # target-side event effect actually lands.
        _counter_up(self.actor, "hostile_act", 30)
        _counter_up(self.actor, "climax_count", 20)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("interspecies_mating", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertIn("異種性愛", self.monster.sexual.experience_types)
        self.assertNotIn("異種性愛", self.actor.sexual.experience_types)
