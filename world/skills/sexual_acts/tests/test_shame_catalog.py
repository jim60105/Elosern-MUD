"""Behaviour tests for the nine counter-gated 羞恥線 acts.

The seed 撩起衣襬 ships unconditionally (covered by ``test_seed_acts.py``);
this module covers the nine rows this change adds: their counter-threshold
unlock gates, the ``self_exposure`` event reuse (and 挑釁凝視's exemption),
the multi-counter credits, the AREA acts' 腰腹 target part, and the
design.md D-2 regression proving 挑釁凝視 actually moves a target's
pleasure through the shipped combat-modifier pipeline's input.
"""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver
from world.rules.rulebook.schema import load_rules
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

_SEXUAL_YAML_PATH = (
    Path(__file__).parents[4] / "world" / "rules" / "rulebook" / "sexual.yaml"
)
# Every rule id sexual.yaml carries today, pinned so the delta spec's "no new
# sexual.yaml row" claim stays structurally verifiable (a future catalog line
# that adds a row must update this pin in the same change).
_EXPECTED_RULE_IDS = (
    "arousal_up_on_stimulus",
    "arousal_up_on_sustained_stimulus",
    "arousal_extreme_stimulus_to_max",
    "arousal_reset_after_climax",
    "wetness_follows_arousal",
    "wetness_up_on_direct_stimulus",
    "wetness_max_on_climax",
    "sensitivity_up_on_frequent_stimulation",
    "climax_gate",
    "climax_phase_critical_point_to_in_progress",
    "climax_phase_ends_to_afterglow",
    "climax_today_increment_on_climax",
    "virginity_once",
    "experience_vaginal_added",
    "experience_masturbation_added",
    "experience_lesbian_added",
    "experience_gay_added",
    "experience_titfuck_added",
    "experience_watched_added",
    "experience_exposure_added",
    "experience_interspecies_added",
    "shame_up_on_exposure_increase",
    "shame_up_on_public_sexual_activity",
    "shame_up_on_watched",
    "exposure_up_on_clothing_damaged",
    "exposure_up_on_self_exposure",
    "sp_cost_on_climax",
    "sp_cost_on_climax_extension",
)

_TIER_1 = (
    "shame_half_expose_chest",
    "shame_half_expose_lower",
    "shame_loosen_collar",
)
_ALL_ACTS = (
    *_TIER_1,
    "shame_full_expose",
    "shame_public_masturbation",
    "shame_provocative_gaze",
    "shame_public_performance",
    "shame_devoted_pose",
    "shame_shameless_declaration",
)
# Every act except the battlefield taunt reuses the seed's self_exposure event.
_REUSING_ACTS = (
    *_TIER_1,
    "shame_full_expose",
    "shame_public_masturbation",
    "shame_public_performance",
    "shame_devoted_pose",
    "shame_shameless_declaration",
)
_AREA_ACTS = (
    "shame_provocative_gaze",
    "shame_public_performance",
    "shame_devoted_pose",
)

# The exact unlock table design.md D-1 pins, keyed per act.
_UNLOCK_TABLE = {
    "shame_half_expose_chest": {"exposure_act_count": 5},
    "shame_half_expose_lower": {"exposure_act_count": 5},
    "shame_loosen_collar": {"exposure_act_count": 5},
    "shame_full_expose": {"exposure_act_count": 20},
    "shame_public_masturbation": {
        "exposure_act_count": 20,
        "masturbation_count": 25,
    },
    "shame_provocative_gaze": {"watched_count": 10},
    "shame_public_performance": {
        "watched_count": 10,
        "exposure_act_count": 20,
    },
    "shame_devoted_pose": {"exposure_act_count": 50},
    "shame_shameless_declaration": {
        "exposure_act_count": 50,
        "watched_count": 30,
    },
}


def _entity(key="shame catalog owner"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _counter_up(entity, counter, times):
    for _ in range(times):
        getattr(entity.sexual, f"record_{counter}")()


class ShameActRegistrationTests(unittest.TestCase):
    """The nine rows carry exactly the D-1 unlock/event/part table."""

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_each_act_declares_its_d1_unlock_mapping(self):
        for key, expected in _UNLOCK_TABLE.items():
            with self.subTest(key=key):
                self.assertEqual(dict(SEXUAL_ACT_REGISTRY[key].unlock), expected)

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_every_act_declares_no_actor_part(self):
        for key in _ALL_ACTS:
            with self.subTest(key=key):
                self.assertIsNone(SEXUAL_ACT_REGISTRY[key].actor_part)

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_every_reusing_act_declares_self_exposure_only(self):
        for key in _REUSING_ACTS:
            with self.subTest(key=key):
                expected = (
                    ("self_exposure", "masturbation_climax")
                    if key == "shame_public_masturbation"
                    else ("self_exposure",)
                )
                self.assertEqual(SEXUAL_ACT_REGISTRY[key].sexual_events, expected)

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_provocative_gaze_declares_no_sexual_event(self):
        self.assertEqual(SEXUAL_ACT_REGISTRY["shame_provocative_gaze"].sexual_events, ())

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_sexual_yaml_gains_no_rule_row_from_this_change(self):
        rules = load_rules(_SEXUAL_YAML_PATH)
        self.assertEqual(
            tuple(rule.id for rule in rules),
            _EXPECTED_RULE_IDS,
        )

    @covers_requirement("sexual-catalog-shame::shame-public-masturbation-credits-three-counters-and-emits-two-events")
    def test_public_masturbation_declares_three_counters_and_two_events(self):
        act = SEXUAL_ACT_REGISTRY["shame_public_masturbation"]
        self.assertEqual(
            act.actor_counters,
            ("exposure_act_count", "masturbation_count", "watched_count"),
        )
        self.assertEqual(act.sexual_events, ("self_exposure", "masturbation_climax"))

    @covers_requirement("sexual-catalog-shame::shame-public-performance-credits-both-watched-count-and-exposure-act-count-on-the-actor")
    def test_public_performance_declares_actor_only_counters(self):
        act = SEXUAL_ACT_REGISTRY["shame_public_performance"]
        self.assertEqual(act.actor_counters, ("watched_count", "exposure_act_count"))
        self.assertEqual(act.participant_counters, ())

    @covers_requirement("sexual-catalog-shame::shame-provocative-gaze-credits-hostile-act-count-on-the-actor-only-never-on-a-target")
    def test_provocative_gaze_declares_actor_only_hostile_counter(self):
        act = SEXUAL_ACT_REGISTRY["shame_provocative_gaze"]
        self.assertEqual(act.actor_counters, ("hostile_act_count",))
        self.assertEqual(act.participant_counters, ())

    @covers_requirement("sexual-catalog-shame::the-three-area-acts-declare-target-part-as-a-body-parts-member-never-none")
    def test_every_area_act_declares_the_waist_target_part(self):
        for key in _AREA_ACTS:
            with self.subTest(key=key):
                self.assertEqual(SKILL_REGISTRY[key].target_spec, TargetSpec.AREA)
                part = SEXUAL_ACT_REGISTRY[key].target_part
                self.assertEqual(part, "腰腹")
                self.assertIn(part, BODY_PARTS)


class ShameUnlockTests(EvenniaTestCase):
    """The counter-threshold gates read through SkillHandler.owned_keys()."""

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_tier1_act_locked_below_threshold_and_unlocked_at_it(self):
        entity = _entity()
        _counter_up(entity, "exposure_act", 4)
        self.assertNotIn("shame_half_expose_chest", entity.skills.owned_keys())
        entity.sexual.record_exposure_act()
        self.assertIn("shame_half_expose_chest", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_public_masturbation_requires_both_exposure_and_masturbation(self):
        entity = _entity()
        _counter_up(entity, "exposure_act", 20)
        _counter_up(entity, "masturbation", 24)
        self.assertNotIn("shame_public_masturbation", entity.skills.owned_keys())
        entity.sexual.record_masturbation()
        self.assertIn("shame_public_masturbation", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_provocative_gaze_is_gated_by_watched_count_alone(self):
        entity = _entity()
        _counter_up(entity, "watched", 10)
        self.assertEqual(entity.sexual.exposure_act_count, 0)
        self.assertIn("shame_provocative_gaze", entity.skills.owned_keys())

    @covers_requirement("sexual-catalog-shame::nine-tier-1-4-shame-acts-are-registered-gated-by-exposure-act-count-and-or-watched-count-thresholds")
    def test_shameless_declaration_requires_both_exposure_and_watched(self):
        entity = _entity()
        _counter_up(entity, "exposure_act", 50)
        _counter_up(entity, "watched", 29)
        self.assertNotIn("shame_shameless_declaration", entity.skills.owned_keys())
        entity.sexual.record_watched()
        self.assertIn("shame_shameless_declaration", entity.skills.owned_keys())


class ShameCastTests(EvenniaTest):
    """Casting the gated acts through ActionResolver credits what D-1 declares."""

    def setUp(self):
        super().setUp()
        # Every cast of a resistible act resolves one contest per target; the
        # resist config validates against the quest registry, which only test
        # setup populates (same requirement sexual-resist-cast-wiring's own
        # test changes add).
        register_catalog()
        self.actor = create_object(
            PlayerCharacter, key="shame catalog caster", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="shame catalog target", location=self.room1
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

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_tier1_act_raises_the_actors_own_exposure_by_one(self):
        entity = _entity()
        entity.location = self.room1
        _counter_up(entity, "exposure_act", 5)
        self.assertEqual(entity.sexual.exposure.value, 0)
        result = ActionResolver.resolve(
            ActionRequest(
                entity,
                "shame_half_expose_chest",
                [],
                RoomActionContext(entity.location, {}),
            )
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity.sexual.exposure.value, 1)

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_every_reusing_act_raises_the_actors_own_exposure_by_one(self):
        # One fresh entity per act keeps every cast at the exposure vocabulary
        # floor (極低, value 0), so "increases by exactly one" never clamps
        # against the five-level cap. SELF acts fire self_exposure on the
        # actor; the two AREA acts fire it on their targets instead (design.md
        # D-6) and are covered by the following test.
        thresholds = {
            "shame_half_expose_chest": {"exposure_act": 5},
            "shame_half_expose_lower": {"exposure_act": 5},
            "shame_loosen_collar": {"exposure_act": 5},
            "shame_full_expose": {"exposure_act": 20},
            "shame_public_masturbation": {
                "exposure_act": 20,
                "masturbation": 25,
            },
            "shame_shameless_declaration": {
                "exposure_act": 50,
                "watched": 30,
            },
        }
        for key, counters in thresholds.items():
            with self.subTest(key=key):
                entity = _entity(key=f"exposure caster {key}")
                entity.location = self.room1
                for counter, times in counters.items():
                    _counter_up(entity, counter, times)
                self.assertEqual(entity.sexual.exposure.value, 0)
                result = ActionResolver.resolve(
                    ActionRequest(
                        entity,
                        key,
                        [],
                        RoomActionContext(entity.location, {}),
                    )
                )
                self.assertEqual(result.outcome, "success")
                self.assertEqual(entity.sexual.exposure.value, 1)

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_area_reusing_act_raises_every_participants_exposure(self):
        # sexual-intercourse-acts D-3: the landed event handler fires on
        # participants(actor, targets), so an AREA cast's self_exposure event
        # raises the acting entity's exposure as well as each target's — the
        # actor of a public performance is publicly exposed too.
        thresholds = {
            "shame_public_performance": {
                "watched": 10,
                "exposure_act": 20,
            },
            "shame_devoted_pose": {"exposure_act": 50},
        }
        for key, counters in thresholds.items():
            with self.subTest(key=key):
                entity = _entity(key=f"area exposure caster {key}")
                entity.location = self.room1
                target = create_object(
                    PlayerCharacter,
                    key=f"area exposure target {key}",
                    location=self.room1,
                )
                target.race = "human"
                target.apply_race_baseline()
                for counter, times in counters.items():
                    _counter_up(entity, counter, times)
                self.assertEqual(entity.sexual.exposure.value, 0)
                self.assertEqual(target.sexual.exposure.value, 0)
                with patch("world.rules.action.roll_d100", return_value=1):
                    result = ActionResolver.resolve(
                        ActionRequest(
                            entity,
                            key,
                            [target],
                            RoomActionContext(entity.location, {}),
                        )
                    )
                self.assertEqual(result.outcome, "success")
                self.assertEqual(target.sexual.exposure.value, 1)
                self.assertEqual(entity.sexual.exposure.value, 1)

    @covers_requirement("sexual-catalog-shame::every-act-except-shame-provocative-gaze-reuses-the-self-exposure-event-no-new-sexual-yaml-row-is-added")
    def test_provocative_gaze_does_not_raise_the_actors_own_exposure(self):
        _counter_up(self.actor, "watched", 10)
        self.assertEqual(self.actor.sexual.exposure.value, 0)
        result = self._cast("shame_provocative_gaze", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure.value, 0)

    @covers_requirement("sexual-catalog-shame::shame-public-masturbation-credits-three-counters-and-emits-two-events")
    def test_public_masturbation_increments_all_three_counters_by_exactly_one(self):
        _counter_up(self.actor, "exposure_act", 20)
        _counter_up(self.actor, "masturbation", 25)
        result = self._cast("shame_public_masturbation", [])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.exposure_act_count, 21)
        self.assertEqual(self.actor.sexual.masturbation_count, 26)
        self.assertEqual(self.actor.sexual.watched_count, 1)

    @covers_requirement("sexual-catalog-shame::shame-public-performance-credits-both-watched-count-and-exposure-act-count-on-the-actor")
    def test_public_performance_increments_both_actor_counters_only(self):
        _counter_up(self.actor, "watched", 10)
        _counter_up(self.actor, "exposure_act", 20)
        result = self._cast("shame_public_performance", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.watched_count, 11)
        self.assertEqual(self.actor.sexual.exposure_act_count, 21)
        for counter in (
            "watched_count",
            "exposure_act_count",
            "masturbation_count",
            "hostile_act_count",
        ):
            self.assertEqual(getattr(self.target.sexual, counter), 0)

    @covers_requirement("sexual-catalog-shame::shame-provocative-gaze-credits-hostile-act-count-on-the-actor-only-never-on-a-target")
    def test_provocative_gaze_credits_hostile_act_count_on_the_actor_only(self):
        _counter_up(self.actor, "watched", 10)
        self.assertEqual(self.actor.sexual.hostile_act_count, 0)
        self.assertEqual(self.target.sexual.hostile_act_count, 0)
        result = self._cast("shame_provocative_gaze", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.hostile_act_count, 1)
        self.assertEqual(self.target.sexual.hostile_act_count, 0)

    def test_provocative_gaze_raises_a_targets_pleasure(self):
        # design.md D-2 regression: 挑釁凝視's "accuracy debuff" is delivered
        # by the shipped high_arousal_agility_accuracy_penalty combat-modifier
        # row once a target's pleasure crosses the 高度 band. The
        # modifier's own firing is probabilistic and owned by
        # combat_modifiers.yaml's suite; what this test pins is that the
        # act's cast actually moves the target's pleasure (2 participants →
        # crowd multiplier 1.1; a neutral target receives
        # round(14 × 1.0 × 1.0 × 1.0 × 1.1) = 15). The target's resist contest
        # is forced to compliance (roll=1; two floor humans share equal
        # contest scores) so the target-side pleasure assertion stays
        # deterministic under the shipped resist gate.
        _counter_up(self.actor, "watched", 10)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("shame_provocative_gaze", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.pleasure.base, 15)
        # D-4 holds for the actor too: round(14 × 0.4 × 1.1) = 6.
        self.assertEqual(self.actor.sexual.pleasure.base, 6)
