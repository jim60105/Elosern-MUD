"""Behaviour tests for the eight counter-gated 戰鬥線 acts.

The seed 挑逗 ships unconditionally (covered by ``test_seed_acts.py``); this
module covers the eight rows this change adds: their counter-threshold unlock
gates (including the two compound gates), the asymmetric
``hostile_act_count`` crediting on the actor only, the D-4 worst-case
extension-threshold guarantee for the three ``base_pleasure=30`` acts, the
D-3 actor-side ratio comparison, the sole AREA act, and the
``sexual_events=()``/no-new-modifier-row claim.
"""

from tools.spec_traceability import covers_requirement

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver
from world.rules.rulebook.schema import load_rules
from world.rules.sexual_act_effects import (
    compute_pleasure_gain,
    load_effects_config,
)
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

_COMBAT_MODIFIERS_YAML_PATH = (
    Path(__file__).parents[4] / "world" / "rules" / "rulebook" / "combat_modifiers.yaml"
)

_TIER_1 = ("combat_tease_whisper", "combat_tease_touch")
_TIER_2 = ("combat_charm", "combat_bind_caress", "combat_forced_pleasure")
_TIER_3 = ("combat_forced_climax", "combat_relentless_torment")
_TIER_5 = ("combat_climax_domination",)
_ALL_ACTS = (*_TIER_1, *_TIER_2, *_TIER_3, *_TIER_5)

# The exact unlock table design.md D-1 pins, keyed per act.
_UNLOCK_TABLE = {
    "combat_tease_whisper": {"hostile_act_count": 5},
    "combat_tease_touch": {"hostile_act_count": 5},
    "combat_charm": {"hostile_act_count": 20},
    "combat_bind_caress": {"hostile_act_count": 20},
    "combat_forced_pleasure": {"hostile_act_count": 20},
    "combat_forced_climax": {"hostile_act_count": 40, "climax_count": 30},
    "combat_relentless_torment": {"hostile_act_count": 40, "climax_count": 30},
    "combat_climax_domination": {
        "hostile_act_count": 80,
        "climax_extension_count": 30,
    },
}

# The exact part/base/ratio table design.md D-1 pins. Every row's actor part
# equals its target part — the line's shared-part convention, carried from
# the seed's 腰腹/腰腹 row; the D-1 column "Actor=Target part" reads exactly
# this way (C3's table spelled out "None / part" when an AREA act had no
# actor part, and this table does not).
_PART_TABLE = {
    "combat_tease_whisper": "耳朵",
    "combat_tease_touch": "腰腹",
    "combat_charm": "頸項",
    "combat_bind_caress": "大腿",
    "combat_forced_pleasure": "私處",
    "combat_forced_climax": "私處",
    "combat_relentless_torment": "臀部",
    "combat_climax_domination": "私處",
}
_BASE_TABLE = {
    "combat_tease_whisper": 10,
    "combat_tease_touch": 11,
    "combat_charm": 20,
    "combat_bind_caress": 20,
    "combat_forced_pleasure": 24,
    "combat_forced_climax": 30,
    "combat_relentless_torment": 30,
    "combat_climax_domination": 30,
}
_RATIO_TABLE = {
    "combat_tease_whisper": 0.4,
    "combat_tease_touch": 0.4,
    "combat_charm": 0.4,
    "combat_bind_caress": 0.4,
    "combat_forced_pleasure": 0.4,
    "combat_forced_climax": 0.4,
    "combat_relentless_torment": 0.6,
    "combat_climax_domination": 0.4,
}


def _entity(key="combat catalog owner"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _counter_up(entity, counter, times):
    for _ in range(times):
        getattr(entity.sexual, f"record_{counter}")()


def _neutral_participant(part="私處", sensitivity="普通", shame="無"):
    """Build a duck-typed participant at the multiplier floors for unit tests."""
    return SimpleNamespace(
        sexual=SimpleNamespace(
            sensitivity={part: SimpleNamespace(level=sensitivity)},
            shame=SimpleNamespace(level=shame),
        )
    )


class CombatActRegistrationTests(unittest.TestCase):
    """The eight rows carry exactly the D-1 unlock/part/base/ratio table."""

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_each_act_declares_its_d1_unlock_mapping(self):
        for key, expected in _UNLOCK_TABLE.items():
            with self.subTest(key=key):
                self.assertEqual(dict(SEXUAL_ACT_REGISTRY[key].unlock), expected)

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_every_act_declares_the_actor_only_hostile_counter(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.actor_counters, ("hostile_act_count",))
                self.assertEqual(act.participant_counters, ())

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_every_act_is_resistible(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertTrue(SEXUAL_ACT_REGISTRY[key].resistible)

    def test_every_act_declares_actor_part_equal_to_target_part(self):
        # design.md D-1: the "Actor=Target part" column gives one part used
        # for both sides; every row follows the seed's 腰腹/腰腹 convention.
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                part = _PART_TABLE[key]
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.actor_part, part)
                self.assertEqual(act.target_part, part)
                self.assertIn(part, BODY_PARTS)

    def test_each_act_declares_its_d1_base_pleasure_and_ratio(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                act = SEXUAL_ACT_REGISTRY[key]
                self.assertEqual(act.base_pleasure, _BASE_TABLE[key])
                self.assertEqual(act.actor_pleasure_ratio, _RATIO_TABLE[key])

    @covers_requirement("sexual-catalog-combat::combat-forced-climax-combat-relentless-torment-and-combat-climax-domination-reliably-clear-the-climax-extension-threshold")
    def test_the_three_extension_acts_declare_base_pleasure_30(self):
        for key in ("combat_forced_climax", "combat_relentless_torment", "combat_climax_domination"):
            with self.subTest(key=key):
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].base_pleasure, 30)

    @covers_requirement("sexual-catalog-combat::combat-forced-climax-and-combat-relentless-torment-differ-by-actor-pleasure-ratio-not-by-dominance-freedom-tuning")
    def test_forced_climax_and_relentless_torment_declare_ratio_and_part_pair(self):
        forced = SEXUAL_ACT_REGISTRY["combat_forced_climax"]
        relentless = SEXUAL_ACT_REGISTRY["combat_relentless_torment"]
        self.assertEqual(forced.actor_pleasure_ratio, 0.4)
        self.assertEqual(forced.target_part, "私處")
        self.assertEqual(relentless.actor_pleasure_ratio, 0.6)
        self.assertEqual(relentless.target_part, "臀部")
        self.assertEqual(relentless.base_pleasure, forced.base_pleasure)

    @covers_requirement("sexual-catalog-combat::combat-climax-domination-is-the-sole-area-act-in-this-catalog-line")
    def test_climax_domination_is_the_sole_area_act(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                expected = (
                    TargetSpec.AREA if key == "combat_climax_domination" else TargetSpec.SINGLE
                )
                self.assertIs(SKILL_REGISTRY[key].target_spec, expected)
        act = SEXUAL_ACT_REGISTRY["combat_climax_domination"]
        self.assertEqual(act.actor_part, "私處")
        self.assertEqual(act.target_part, "私處")

    @covers_requirement("sexual-catalog-combat::no-act-added-by-this-change-declares-a-sexual-events-entry")
    def test_every_act_declares_no_sexual_events(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].sexual_events, ())

    @covers_requirement("sexual-catalog-combat::no-act-added-by-this-change-declares-a-sexual-events-entry")
    def test_charm_and_bind_caress_reuse_the_shipped_combat_modifier_row(self):
        # 魅惑/束縛愛撫's accuracy/agility-debuff flavour is delivered by the
        # already-shipped high_arousal_agility_accuracy_penalty row, unchanged
        # by this proposal — pinned so the claim stays structurally verifiable.
        rules = load_rules(_COMBAT_MODIFIERS_YAML_PATH)
        row = next(
            rule for rule in rules if rule.id == "high_arousal_agility_accuracy_penalty"
        )
        self.assertEqual(row.when, {"field": "arousal", "gte": "高度"})
        self.assertEqual(row.then, {"agility": "-20%", "accuracy": -15})


class CombatUnlockTests(EvenniaTest):
    """The counter-threshold gates read through SkillHandler.owned_keys()."""

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_tier1_act_locked_below_threshold_and_unlocked_at_it(self):
        entity = _entity()
        _counter_up(entity, "hostile_act", 4)
        self.assertNotIn("combat_tease_whisper", entity.skills.owned_keys())
        entity.sexual.record_hostile_act()
        self.assertIn("combat_tease_whisper", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_forced_climax_requires_both_hostile_and_climax_counts(self):
        entity = _entity()
        _counter_up(entity, "hostile_act", 40)
        _counter_up(entity, "climax_count", 29)
        self.assertNotIn("combat_forced_climax", entity.skills.owned_keys())
        entity.sexual.record_climax_count()
        self.assertIn("combat_forced_climax", entity.skills.owned_keys())
        # Reverse case: the compound counter satisfied, hostile_act_count one
        # below its threshold — still locked.
        reverse = _entity()
        _counter_up(reverse, "hostile_act", 39)
        _counter_up(reverse, "climax_count", 30)
        self.assertNotIn("combat_forced_climax", reverse.skills.owned_keys())

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_climax_domination_requires_both_hostile_and_extension_counts(self):
        entity = _entity()
        _counter_up(entity, "hostile_act", 80)
        _counter_up(entity, "climax_extension", 29)
        self.assertNotIn("combat_climax_domination", entity.skills.owned_keys())
        entity.sexual.record_climax_extension()
        self.assertIn("combat_climax_domination", entity.skills.owned_keys())
        # Reverse case: extension count satisfied, hostile_act_count one below
        # its threshold — still locked.
        reverse = _entity()
        _counter_up(reverse, "hostile_act", 79)
        _counter_up(reverse, "climax_extension", 30)
        self.assertNotIn("combat_climax_domination", reverse.skills.owned_keys())


class CombatCastTests(EvenniaTest):
    """Casting the gated acts through ActionResolver credits what D-1 declares."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = create_object(
            PlayerCharacter, key="combat catalog caster", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="combat catalog target", location=self.room1
        )
        self.target.race = "human"
        self.target.apply_race_baseline()

    def _cast(self, act_key, targets):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-catalog-combat::eight-tier-1-2-3-5-combat-acts-are-registered-gated-by-hostile-act-count-and-or-climax-count-and-or-climax-extension-count-thresholds")
    def test_tease_whisper_credits_hostile_act_count_on_the_actor_only(self):
        # The act's own unlock gate is hostile_act_count itself, so the actor
        # must be raised to the threshold before casting (the spec scenario's
        # "both starting at 0" is not reachable for the actor by construction
        # of this line's gates); the pin that matters is the target's counter
        # never moving.
        _counter_up(self.actor, "hostile_act", 5)
        self.assertEqual(self.target.sexual.hostile_act_count, 0)
        result = self._cast("combat_tease_whisper", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.hostile_act_count, 6)
        self.assertEqual(self.target.sexual.hostile_act_count, 0)

    @covers_requirement("sexual-catalog-combat::combat-forced-climax-combat-relentless-torment-and-combat-climax-domination-reliably-clear-the-climax-extension-threshold")
    def test_forced_climax_worst_case_target_gain_clears_the_threshold(self):
        # D-4 worst case through the live pipeline: a target at 普通
        # sensitivity (floor, never trained) and 強烈 shame (the lowest
        # multiplier below 成癮's 1.6 outlier) receives
        # round(30 × 1.0 × 1.0 × 0.65 × 1.1) = 21 >= 20.
        # combat_forced_climax is resistible=True, so the resist gate runs a
        # d100 contest per target; force roll=1 (a guaranteed comply for two
        # floor fixtures) to keep the target-side assertion deterministic
        # (sexual-resist-cast-wiring design D-3a).
        _counter_up(self.actor, "hostile_act", 40)
        _counter_up(self.actor, "climax_count", 30)
        self.target.sexual.shame.value = "強烈"
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("combat_forced_climax", [self.target])
        self.assertEqual(result.outcome, "success")
        threshold = load_effects_config().climax_extension_threshold
        self.assertGreaterEqual(self.target.sexual.pleasure.base, threshold)
        self.assertEqual(self.target.sexual.pleasure.base, 21)

    @covers_requirement("sexual-catalog-combat::combat-climax-domination-is-the-sole-area-act-in-this-catalog-line")
    def test_climax_domination_credits_the_actor_and_raises_each_targets_pleasure(self):
        # The AREA act applies its pleasure effect to every target present and
        # keeps the line's asymmetric crediting: the actor's hostile_act_count
        # grows, targets' counters never move. resistible=True means each
        # target runs a resist contest; force compliant rolls so the
        # target-side pleasure assertions stay deterministic.
        _counter_up(self.actor, "hostile_act", 80)
        _counter_up(self.actor, "climax_extension", 30)
        other = create_object(
            PlayerCharacter, key="combat catalog second target", location=self.room1
        )
        other.race = "human"
        other.apply_race_baseline()
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("combat_climax_domination", [self.target, other])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.hostile_act_count, 81)
        for entity in (self.target, other):
            with self.subTest(entity=entity.key):
                self.assertEqual(entity.sexual.hostile_act_count, 0)
                self.assertGreater(entity.sexual.pleasure.base, 0)


class CombatPleasureMathTests(unittest.TestCase):
    """The pure D-3/D-4 arithmetic, evaluated at matched inputs."""

    @covers_requirement("sexual-catalog-combat::combat-forced-climax-combat-relentless-torment-and-combat-climax-domination-reliably-clear-the-climax-extension-threshold")
    def test_worst_case_target_gain_clears_the_extension_threshold(self):
        # 普通 sensitivity (1.0, the floor), 強烈 shame (0.65, the lowest value
        # below 成癮's 1.6 outlier), participant_count == 2 (crowd 1.1):
        # round(30 × 1.0 × 1.0 × 0.65 × 1.1) = 21 >= 20.
        participant = _neutral_participant(part="私處", sensitivity="普通", shame="強烈")
        gain = compute_pleasure_gain(participant, "私處", 30, 1.0, 2)
        threshold = load_effects_config().climax_extension_threshold
        self.assertGreaterEqual(gain, threshold)
        self.assertEqual(gain, 21)

    @covers_requirement("sexual-catalog-combat::combat-forced-climax-and-combat-relentless-torment-differ-by-actor-pleasure-ratio-not-by-dominance-freedom-tuning")
    def test_relentless_torment_costs_the_actor_more_at_matched_inputs(self):
        # Identical sensitivity, shame, and participant count for both acts:
        # only the ratio differs (0.4 vs 0.6 at base 30), so
        # round(30 × 0.4 × 1.1) = 13 < round(30 × 0.6 × 1.1) = 20.
        participant = _neutral_participant(part="私處")
        forced = compute_pleasure_gain(participant, "私處", 30, 0.4, 2)
        relentless = compute_pleasure_gain(participant, "私處", 30, 0.6, 2)
        self.assertGreater(relentless, forced)
        self.assertEqual(forced, 13)
        self.assertEqual(relentless, 20)
