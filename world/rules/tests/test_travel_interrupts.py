"""Pure before/after travel interrupt comparisons (wilderness-travel-interrupts).

Every case builds two immutable synthetic fact records with independently
known outcomes, so the comparison mechanism is asserted without pinning any
shipped geography, landmark, district or population row. The paired committed
step (the planner's first-legal-step threshold and the real wilderness capture)
lives with the adapter tests that drive a real traversal.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from world.rules.fatigue import FatigueStage
from world.rules.sight import POLICY as SIGHT_POLICY
from world.rules.travel_interrupts import (
    FLAG_ORDER,
    MovementFacts,
    TravellerFact,
    member_fell_asleep,
    movement_flags,
    nightfall_crossed,
    pace_threshold_reached,
    wilderness_cell,
)
from world.rules.travel_plan import PACE_STOP_STAGES, _STAGE_RANK
from tools.spec_traceability import covers_requirement


def _night_start_tick() -> int:
    """One tick at the first second of the rulebook's night phase."""
    start_hour = next(
        entry[1] for entry in SIGHT_POLICY.phases if entry[0] == "night"
    )
    return start_hour * 3600


def _facts(
    *,
    cell=(5, 5),
    tick=0,
    landmarks=(),
    lit=(),
    distant=(),
    hostiles=(),
    travellers=(),
) -> MovementFacts:
    return MovementFacts(
        cell=cell,
        tick=tick,
        landmarks=frozenset(landmarks),
        lit_districts=frozenset(lit),
        distant_sources=frozenset(distant),
        hostiles=frozenset(hostiles),
        travellers=tuple(travellers),
    )


def _traveller(
    member_id=1,
    stage: FatigueStage | None = FatigueStage.NORMAL,
    asleep: bool | None = False,
) -> TravellerFact:
    return TravellerFact(member_id=member_id, stage=stage, asleep=asleep)


_CAUTIOUS = {"pace": "cautious", "stop_at_night": False}
_STANDARD = {"pace": "standard", "stop_at_night": False}
_FORCED = {"pace": "forced", "stop_at_night": False}
_NIGHT_WALK = {"pace": "forced", "stop_at_night": True}
_CAUTIOUS_NIGHT_WALK = {"pace": "cautious", "stop_at_night": True}


class TransitionTableTests(unittest.TestCase):
    """Every flag raises only for its own positive transition, in stable order."""

    def test_identical_facts_raise_nothing(self):
        before = _facts(travellers=(_traveller(),))
        self.assertEqual(movement_flags(before, before), ())
        self.assertEqual(movement_flags(before, before, walk=_CAUTIOUS), ())

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_each_flag_raises_only_for_its_positive_transition(self):
        night = _night_start_tick()
        cases = {
            "landmark_reached": (
                _facts(cell=(5, 5)),
                _facts(cell=(5, 6), landmarks={"synthetic_district"}),
                None,
            ),
            "district_lit": (
                _facts(lit=()),
                _facts(cell=(5, 6), lit={"synthetic_district"}),
                None,
            ),
            "landmark_sighted": (
                _facts(distant=()),
                _facts(cell=(5, 6), distant={"landmark:synthetic_source"}),
                None,
            ),
            "hostile_in_sight": (
                _facts(hostiles=()),
                _facts(
                    cell=(5, 6),
                    hostiles={"population:synthetic:5:6:ambient:0"},
                ),
                None,
            ),
            "pace_threshold": (
                _facts(travellers=(_traveller(stage=FatigueStage.NORMAL),)),
                _facts(
                    cell=(5, 6),
                    travellers=(_traveller(stage=FatigueStage.LIGHT),),
                ),
                _CAUTIOUS,
            ),
            "nightfall": (
                _facts(tick=night - 1, travellers=(_traveller(),)),
                _facts(tick=night, cell=(5, 6), travellers=(_traveller(),)),
                _NIGHT_WALK,
            ),
            "member_asleep": (
                _facts(travellers=(_traveller(asleep=False),)),
                _facts(
                    cell=(5, 6),
                    travellers=(_traveller(asleep=True),),
                ),
                None,
            ),
        }
        self.assertEqual(set(cases), set(FLAG_ORDER))
        for flag, (before, after, walk) in cases.items():
            with self.subTest(flag=flag):
                self.assertEqual(movement_flags(before, after, walk=walk), (flag,))

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_combined_flags_use_the_documented_stable_order(self):
        night = _night_start_tick()
        before = _facts(
            tick=night - 1,
            lit={"old"},
            travellers=(
                _traveller(member_id=1, stage=FatigueStage.NORMAL),
                _traveller(member_id=2, asleep=False),
            ),
        )
        after = _facts(
            cell=(6, 6),
            tick=night,
            landmarks={"synthetic_district"},
            lit={"old", "new"},
            distant={"landmark:synthetic_source"},
            hostiles={"object:9001"},
            travellers=(
                _traveller(member_id=1, stage=FatigueStage.LIGHT),
                _traveller(member_id=2, asleep=True),
            ),
        )
        self.assertEqual(
            movement_flags(before, after, walk=_CAUTIOUS_NIGHT_WALK),
            FLAG_ORDER,
        )

    def test_a_district_already_lit_before_the_step_does_not_rerase_it(self):
        before = _facts(lit={"synthetic_district"})
        after = _facts(cell=(5, 6), lit={"synthetic_district"})
        self.assertNotIn("district_lit", movement_flags(before, after))

    def test_a_known_distant_source_does_not_rerase_the_sighting(self):
        before = _facts(distant={"landmark:synthetic_source"})
        after = _facts(cell=(5, 6), distant={"landmark:synthetic_source"})
        self.assertNotIn("landmark_sighted", movement_flags(before, after))

    def test_a_hostile_already_in_sight_does_not_rerase_the_flag(self):
        before = _facts(hostiles={"object:9001"})
        after = _facts(cell=(5, 6), hostiles={"object:9001"})
        self.assertNotIn("hostile_in_sight", movement_flags(before, after))

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_prospective_materialization_keeps_one_stable_hostile_identity(self):
        # The ambient slot key is the same before (prospective) and after
        # (materialized); only the natural landmark flag may raise.
        slot = "population:synthetic:5:6:species:0"
        before = _facts(cell=(5, 5), hostiles={slot})
        after = _facts(cell=(5, 6), hostiles={slot}, landmarks={"synthetic"})
        self.assertEqual(movement_flags(before, after), ("landmark_reached",))

    def test_a_landmark_reached_on_a_repeat_visit_still_raises(self):
        # "Including repeat": visiting the landmark again is still an arrival.
        before = _facts(cell=(5, 5), landmarks={"synthetic"})
        after = _facts(cell=(5, 6), landmarks={"synthetic"})
        self.assertIn("landmark_reached", movement_flags(before, after))


class PaceThresholdTests(unittest.TestCase):
    """The move side mirrors the planner's first-legal-step threshold table."""

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_threshold_table_matches_the_planner_thresholds(self):
        for pace in ("cautious", "standard", "forced"):
            threshold = PACE_STOP_STAGES.get(pace)
            for stage in FatigueStage:
                with self.subTest(pace=pace, stage=stage):
                    after = _facts(travellers=(_traveller(stage=stage),))
                    expected = (
                        threshold is not None
                        and _STAGE_RANK[stage] >= _STAGE_RANK[threshold]
                    )
                    self.assertEqual(
                        "pace_threshold"
                        in movement_flags(_facts(), after, walk={"pace": pace,
                                                                 "stop_at_night": False}),
                        expected,
                    )

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_an_already_at_threshold_member_raises_on_the_legal_step(self):
        after = _facts(travellers=(_traveller(stage=FatigueStage.MODERATE),))
        self.assertTrue(
            pace_threshold_reached(_facts(), after, "standard"),
            "a traveller already at the threshold still stops the first step",
        )

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_forced_pace_never_raises_the_threshold(self):
        after = _facts(travellers=(_traveller(stage=FatigueStage.FORCED_SLEEP),))
        self.assertNotIn(
            "pace_threshold",
            movement_flags(_facts(), after, walk=_FORCED),
        )

    def test_without_walk_the_threshold_and_night_flags_never_raise(self):
        night = _night_start_tick()
        before = _facts(tick=night - 1, travellers=(_traveller(),))
        after = _facts(
            cell=(5, 6),
            tick=night,
            travellers=(_traveller(stage=FatigueStage.SEVERE),),
        )
        self.assertEqual(movement_flags(before, after), ())

    def test_a_member_without_fatigue_state_never_raises_the_threshold(self):
        after = _facts(travellers=(_traveller(stage=None, asleep=None),))
        self.assertNotIn(
            "pace_threshold",
            movement_flags(_facts(), after, walk=_CAUTIOUS),
        )


class NightfallTests(unittest.TestCase):
    """Night entry is an absolute hour-boundary crossing of a charged interval."""

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_a_positive_interval_crossing_into_night_raises(self):
        night = _night_start_tick()
        self.assertTrue(
            nightfall_crossed(_facts(tick=night - 1), _facts(tick=night))
        )
        self.assertIn(
            "nightfall",
            movement_flags(
                _facts(tick=night - 10), _facts(tick=night + 5), walk=_NIGHT_WALK
            ),
        )

    def test_an_interval_inside_night_does_not_raise(self):
        night = _night_start_tick()
        self.assertFalse(
            nightfall_crossed(_facts(tick=night), _facts(tick=night + 3600))
        )

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_flight_waived_zero_charge_step_cannot_cross_time(self):
        night = _night_start_tick()
        before = _facts(tick=night - 1)
        self.assertFalse(nightfall_crossed(before, before))
        self.assertEqual(
            movement_flags(before, before, walk=_NIGHT_WALK), ()
        )

    def test_a_daylight_interval_that_stays_daylight_does_not_raise(self):
        self.assertFalse(nightfall_crossed(_facts(tick=0), _facts(tick=60)))


class MemberAsleepTests(unittest.TestCase):
    """Only an observed awake -> voluntary/forced transition counts."""

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_awake_to_voluntary_raises(self):
        self.assertTrue(
            member_fell_asleep(
                _facts(travellers=(_traveller(asleep=False),)),
                _facts(travellers=(_traveller(asleep=True),)),
            )
        )

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_awake_to_forced_raises(self):
        before = _facts(travellers=(_traveller(stage=FatigueStage.NORMAL),))
        after = _facts(
            travellers=(
                _traveller(stage=FatigueStage.FORCED_SLEEP, asleep=True),
            )
        )
        self.assertIn("member_asleep", movement_flags(before, after))

    def test_an_already_sleeping_member_does_not_rerase_it(self):
        self.assertFalse(
            member_fell_asleep(
                _facts(travellers=(_traveller(asleep=True),)),
                _facts(travellers=(_traveller(asleep=True),)),
            )
        )

    def test_an_absent_before_traveller_is_never_read_as_awake(self):
        self.assertFalse(
            member_fell_asleep(
                _facts(travellers=()),
                _facts(travellers=(_traveller(member_id=2, asleep=True),)),
            )
        )

    def test_an_unreadable_before_posture_is_never_read_as_awake(self):
        self.assertFalse(
            member_fell_asleep(
                _facts(travellers=(_traveller(asleep=None),)),
                _facts(travellers=(_traveller(asleep=True),)),
            )
        )


class CellTests(unittest.TestCase):
    """Only a wilderness terrain room contributes a wilderness cell."""

    def test_a_grid_room_coordinate_never_becomes_a_wilderness_cell(self):
        grid_like = SimpleNamespace(coordinates=(3, 4))
        self.assertIsNone(wilderness_cell(grid_like))


class CollectorDispositionTests(unittest.TestCase):
    """Capture/comparison failures log and leave the empty-flag disposition."""

    def setUp(self):
        self.actor = SimpleNamespace(pk=17)
        self.location = SimpleNamespace(pk=21)

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_capture_failure_logs_and_leaves_no_flags(self):
        from world.rules.movement_settlement import capture_movement_observation

        with mock.patch(
            "world.rules.travel_interrupts._source_present_members",
            return_value=(),
        ), mock.patch(
            "world.rules.travel_interrupts.read_movement_facts",
            side_effect=RuntimeError("synthetic capture failure"),
        ), mock.patch(
            "world.rules.movement_settlement.log_warn"
        ) as log_warn:
            with capture_movement_observation(self.actor) as observation:
                observation.capture_before(
                    self.actor,
                    self.location,
                    wilderness_source_coordinates=None,
                    knowledge_owner=self.actor,
                )
        self.assertEqual(observation.flags, ())
        self.assertIn("travel_interrupts_failed", log_warn.call_args.args)
        context = log_warn.call_args.kwargs["context"]
        self.assertEqual(context["char"], 17)
        self.assertEqual(context["step"], "before")

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_comparison_failure_logs_and_leaves_no_flags(self):
        from world.rules.movement_settlement import capture_movement_observation

        facts = _facts(cell=(5, 5))
        with mock.patch(
            "world.rules.travel_interrupts._source_present_members",
            return_value=(),
        ), mock.patch(
            "world.rules.travel_interrupts.read_movement_facts",
            return_value=facts,
        ), mock.patch(
            "world.rules.movement_settlement.log_warn"
        ) as log_warn, mock.patch(
            "world.rules.travel_interrupts.movement_flags",
            side_effect=RuntimeError("synthetic comparison failure"),
        ), mock.patch(
            "world.rules.travel_interrupts.wilderness_cell",
            return_value=(5, 6),
        ):
            with capture_movement_observation(self.actor) as observation:
                observation.capture_before(
                    self.actor,
                    self.location,
                    wilderness_source_coordinates=None,
                    knowledge_owner=self.actor,
                )
                observation.capture_after(self.actor, knowledge_owner=self.actor)
        self.assertEqual(observation.flags, ())
        self.assertIn("travel_interrupts_failed", log_warn.call_args.args)
        self.assertEqual(log_warn.call_args.kwargs["context"]["step"], "after")

    def test_a_nested_other_actor_cannot_replace_the_collector(self):
        from world.rules.movement_settlement import (
            _observation_for,
            capture_movement_observation,
        )

        other = SimpleNamespace(pk=18)
        with capture_movement_observation(self.actor) as observation:
            self.assertIs(_observation_for(self.actor), observation)
            self.assertIsNone(_observation_for(other))

    def test_a_non_wilderness_destination_yields_no_wilderness_disposition(self):
        from world.rules.movement_settlement import capture_movement_observation

        with capture_movement_observation(self.actor) as observation:
            observation.capture_after(self.actor, knowledge_owner=self.actor)
        self.assertFalse(observation.wilderness)
        self.assertEqual(observation.flags, ())


if __name__ == "__main__":
    unittest.main()
