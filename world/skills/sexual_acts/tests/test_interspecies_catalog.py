"""Data-contract test: sexual act catalog contract
Behaviour tests for the seven counter-gated 異種線 acts.

Covers the full line this change registers: the tiered counter-threshold
unlock gates (Tiers 1-4), the symmetric ``interspecies_act_count`` credit
shared with the ``Monster`` target, the parless ``target_part=None`` contract and
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

# The tier groups and their counter topology are retained identity; every
# threshold, body part, base pleasure and ratio is authored data read from the
# shipped declaration (design D-1's table is never duplicated here).
_TIER_1 = ("interspecies_touch", "interspecies_caress")
_TIER_2 = ("interspecies_entangle", "interspecies_receive")
_TIER_3 = ("interspecies_mating",)
_TIER_4 = ("interspecies_domination", "interspecies_resonance")
_ALL_ACTS = (*_TIER_1, *_TIER_2, *_TIER_3, *_TIER_4)


def _unlock(act_key: str) -> dict[str, int]:
    """The act's declared unlock mapping (its authored thresholds)."""
    return dict(SEXUAL_ACT_REGISTRY[act_key].unlock)


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
    """The seven rows carry a valid authored unlock/part/ratio/event shape."""

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_each_act_declares_a_valid_positive_unlock_mapping(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                unlock = _unlock(key)
                self.assertTrue(unlock)
                for counter, threshold in unlock.items():
                    self.assertIs(type(threshold), int, counter)
                    self.assertGreater(threshold, 0, counter)
        # The tiered counter pairing stays exactly as the spec enumerates it.
        for key in (*_TIER_1, *_TIER_2):
            self.assertEqual(set(_unlock(key)), {"hostile_act_count"})
        self.assertEqual(
            set(_unlock(_TIER_3[0])), {"hostile_act_count", "climax_count"}
        )
        for key in _TIER_4:
            self.assertEqual(set(_unlock(key)), {"interspecies_act_count"})

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_every_act_declares_single_spec_symmetric_counters_and_resistibility(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                skill = SKILL_REGISTRY[key]
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertIs(skill.target_spec, TargetSpec.SINGLE)
                self.assertEqual(act.actor_counters, ("interspecies_act_count",))
                self.assertEqual(act.participant_counters, ("interspecies_act_count",))
                self.assertTrue(act.resistible)

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_every_act_declares_no_target_part(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertIsNone(SEXUAL_ACT_REGISTRY[key].target_part)

    @covers_requirement("sexual-catalog-interspecies::every-act-declares-target-part-none-never-a-body-parts-member")
    def test_every_actor_part_is_a_body_parts_member(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertIn(SEXUAL_ACT_REGISTRY[key].actor_part, BODY_PARTS)

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
    def test_every_act_declares_a_positive_base_and_a_bounded_ratio(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertIn(act.actor_part, BODY_PARTS)
                self.assertIs(type(act.base_pleasure), int)
                self.assertGreater(act.base_pleasure, 0)
                self.assertGreaterEqual(act.actor_pleasure_ratio, 0)
                self.assertLessEqual(act.actor_pleasure_ratio, 1)

    @covers_requirement("sexual-catalog-interspecies::interspecies-receive-declares-the-highest-actor-pleasure-ratio-among-this-change-s-seven-acts")
    def test_receive_ratio_exceeds_every_sibling_act_ratio(self):
        receive_ratio = SEXUAL_ACT_REGISTRY["interspecies_receive"].actor_pleasure_ratio
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
        threshold = _unlock("interspecies_touch")["hostile_act_count"]
        _counter_up(entity, "hostile_act", threshold - 1)
        self.assertNotIn("interspecies_touch", entity.skills.owned_keys())
        entity.sexual.record_hostile_act()
        self.assertIn("interspecies_touch", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_mating_requires_both_hostile_and_climax_counts(self):
        entity = _entity()
        hostile = _unlock("interspecies_mating")["hostile_act_count"]
        climax = _unlock("interspecies_mating")["climax_count"]
        _counter_up(entity, "hostile_act", hostile)
        _counter_up(entity, "climax_count", climax - 1)
        self.assertNotIn("interspecies_mating", entity.skills.owned_keys())
        entity.sexual.record_climax_count()
        self.assertIn("interspecies_mating", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_tier4_act_is_gated_by_interspecies_count_alone(self):
        entity = _entity()
        _counter_up(
            entity,
            "interspecies_act",
            _unlock("interspecies_domination")["interspecies_act_count"],
        )
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
    def test_cast_credits_interspecies_count_on_both_participants(self):
        _counter_up(
            self.actor, "hostile_act", _unlock("interspecies_touch")["hostile_act_count"]
        )
        self.assertEqual(self.actor.sexual.interspecies_act_count, 0)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 0)
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast("interspecies_touch", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.interspecies_act_count, 1)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 1)

    @covers_requirement("sexual-catalog-interspecies::seven-tier-1-4-interspecies-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-interspecies-act-count-thresholds")
    def test_same_species_target_keeps_the_shipped_crediting_behavior(self):
        # The shipped targeting path permits a non-Monster target: the
        # symmetric-crediting change neither adds nor changes any species
        # validation rule, and the crediting handler has no species
        # condition, so the human target is credited exactly what the
        # shipped handler credits every other participant. The resist
        # contest is forced to compliance (roll=1) so the target-side
        # assertion stays deterministic.
        other = create_object(
            PlayerCharacter, key="same species target", location=self.room1
        )
        other.race = "human"
        other.apply_race_baseline()
        _counter_up(
            self.actor, "hostile_act", _unlock("interspecies_touch")["hostile_act_count"]
        )
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast("interspecies_touch", [other])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.interspecies_act_count, 1)
        self.assertEqual(other.sexual.interspecies_act_count, 1)

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
        _counter_up(
            self.actor, "hostile_act", _unlock("interspecies_touch")["hostile_act_count"]
        )
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast("interspecies_touch", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertGreater(self.monster.sexual.pleasure.base, 0)

    @covers_requirement("sexual-catalog-interspecies::interspecies-mating-is-the-sole-emitter-of-sexual-activity-with-nonhuman")
    def test_mating_cast_emits_the_nonhuman_event(self):
        unlock = _unlock("interspecies_mating")
        _counter_up(self.actor, "hostile_act", unlock["hostile_act_count"])
        _counter_up(self.actor, "climax_count", unlock["climax_count"])
        self.assertNotIn("異種性愛", self.monster.sexual.experience_types)
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast("interspecies_mating", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertIn("異種性愛", self.monster.sexual.experience_types)

    def test_mating_event_reaches_every_participant(self):
        # sexual-intercourse-acts D-3: _handle_sexual_event fires on
        # participants(actor, targets), so sexual_activity_with_nonhuman
        # credits both the Monster and the acting entity — closing the
        # recipient asymmetry the original catalog design documented
        # (interspecies design.md D-4). The monster's contest is forced to
        # compliance (roll=1) so the target-side event effect actually lands.
        unlock = _unlock("interspecies_mating")
        _counter_up(self.actor, "hostile_act", unlock["hostile_act_count"])
        _counter_up(self.actor, "climax_count", unlock["climax_count"])
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast("interspecies_mating", [self.monster])
        self.assertEqual(result.outcome, "success")
        self.assertIn("異種性愛", self.monster.sexual.experience_types)
        self.assertIn("異種性愛", self.actor.sexual.experience_types)
