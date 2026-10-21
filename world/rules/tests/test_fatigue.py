"""Synthetic behavior suite for the exact mental-reserve core (mental-reserve).

Covers the policy/state API in ``world/rules/fatigue.py``: exact units and
rates, exclusive stage thresholds, the forced-sleep latch and wake
hysteresis, pure interval/boundary prediction with rational offsets, the
construction baseline, the atomic multi-member writer and its commit-bound
observability. Expected values are independently known arithmetic, never a
copy of the authored rulebook rows; entities and rulebook deviants are
synthetic fixtures.
"""

from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTest
from unittest import TestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules import human_guild_hosts as hosts
from world.rules import fatigue
from world.rules.clock import (
    AdvanceSource,
    WorldClock,
    _restore_advance_registry,
    build_advance_snapshot_registry,
)
from world.rules.fatigue import (
    BoundaryKind,
    FatigueActivity,
    FatigueInterval,
    FatigueRejectReason,
    FatigueRulebookError,
    FatigueState,
    IntervalCompletion,
    SleepPosture,
    TransitionReason,
    actions_allowed,
    fatigue_stage,
    foot_speed_scale,
    initialize_fatigue_state,
    next_fatigue_boundary,
    predict_interval,
    read_fatigue_state,
    settle_fatigue_intervals,
    travel_allowed,
    write_fatigue_state,
)

FULL = 360000
WAKE = 72000
CANONICAL_RULEBOOK = Path(fatigue.__file__).parent / "rulebook" / "fatigue.yaml"
AWAKE = SleepPosture.AWAKE
FORCED = SleepPosture.FORCED
VOLUNTARY = SleepPosture.VOLUNTARY


def _state(reserve: int, posture: SleepPosture = AWAKE) -> FatigueState:
    return FatigueState(reserve_units=reserve, posture=posture)


class _FakeAttributes:
    """Minimal attribute-store double with an optional injected write fault."""

    def __init__(self, values=None, failing_keys=()):
        self.values = dict(values or {})
        self.failing_keys = set(failing_keys)

    def has(self, key, category=None):
        return key in self.values

    def get(self, key, default=None, category=None):
        return self.values.get(key, default)

    def add(self, key, value, category=None):
        if key in self.failing_keys:
            raise RuntimeError(f"injected attribute write fault for {key}")
        self.values[key] = value

    def remove(self, key, category=None):
        self.values.pop(key, None)


class _FakeEntity:
    def __init__(self, key, reserve, posture=AWAKE, failing_keys=()):
        self.key = key
        self.location = None
        self.attributes = _FakeAttributes(
            {
                fatigue.RESERVE_ATTRIBUTE: reserve,
                fatigue.POSTURE_ATTRIBUTE: SleepPosture(posture).value,
            },
            failing_keys,
        )

    def stored(self, key):
        return self.attributes.values[key]


def _deviant(replacements):
    """Load a temporary copy of the canonical rulebook with text replacements."""
    text = CANONICAL_RULEBOOK.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in text:
            raise AssertionError(f"deviant fixture anchor missing: {old!r}")
        text = text.replace(old, new, 1)
    with TemporaryDirectory() as directory:
        path = Path(directory) / "fatigue.yaml"
        path.write_text(text, encoding="utf-8")
        return fatigue.load_policy(path)


class PolicyContractTests(TestCase):
    """The authored policy is closed, exact and fail-closed."""

    def test_shipped_policy_carries_the_exact_units_rates_and_bands(self):
        policy = fatigue.get_policy()
        self.assertEqual(policy.units_per_percent, 3600)
        self.assertEqual(policy.max_units, FULL)
        self.assertEqual(policy.wake_units, WAKE)
        self.assertEqual(
            dict(policy.rates),
            {
                FatigueActivity.AWAKE: -4,
                FatigueActivity.FOOT_TRAVEL: -8,
                FatigueActivity.AWAKE_COMBAT: -12,
                FatigueActivity.SLEEP: 12,
            },
        )
        self.assertEqual(
            [(band.stage.value, band.minimum_units, band.maximum_units)
             for band in policy.bands],
            [
                ("normal", 252000, FULL),
                ("light", 144000, 251999),
                ("moderate", 72000, 143999),
                ("severe", 1, 71999),
            ],
        )

    def test_bands_tile_the_whole_reserve_range_without_gaps_or_overlaps(self):
        bands = fatigue.get_policy().bands
        self.assertEqual(bands[0].maximum_units, FULL)
        self.assertEqual(bands[-1].minimum_units, 1)
        for higher, lower in zip(bands, bands[1:]):
            self.assertEqual(lower.maximum_units, higher.minimum_units - 1)

    def test_missing_rulebook_fails_closed(self):
        with self.assertRaises(FatigueRulebookError):
            fatigue.load_policy(Path("/nonexistent/fatigue.yaml"))

    def test_reserve_scale_must_match_one_hundred_percentage_points(self):
        with self.assertRaises(FatigueRulebookError):
            _deviant([("  value: 3600\n", "  value: 1000\n")])

    def test_non_contiguous_stage_band_fails_closed(self):
        with self.assertRaises(FatigueRulebookError):
            _deviant([("  maximum_units: 251999\n", "  maximum_units: 251998\n")])

    def test_unknown_activity_fails_closed(self):
        with self.assertRaises(FatigueRulebookError):
            _deviant([("  activity: foot_travel\n", "  activity: sprinting\n")])

    def test_wake_threshold_must_be_the_moderate_band_floor(self):
        with self.assertRaises(FatigueRulebookError):
            _deviant([("  value: 72000\n", "  value: 70000\n")])

    def test_foot_speed_scale_above_one_fails_closed(self):
        with self.assertRaises(FatigueRulebookError):
            _deviant([("  foot_speed_numerator: 90\n", "  foot_speed_numerator: 110\n")])


class StageAndScaleTests(TestCase):
    """Exclusive threshold truth and the exact travel scale."""

    def test_stage_boundary_truth(self):
        expected = (
            (252000, "normal"),
            (251999, "light"),
            (144000, "light"),
            (143999, "moderate"),
            (72000, "moderate"),
            (71999, "severe"),
            (1, "severe"),
        )
        for reserve, stage in expected:
            with self.subTest(reserve=reserve):
                self.assertEqual(fatigue_stage(_state(reserve)).value, stage)

    def test_zero_reserve_awake_is_worst_stage_and_forced_replaces_it(self):
        self.assertEqual(fatigue_stage(_state(0)).value, "severe")
        self.assertEqual(fatigue_stage(_state(0, FORCED)).value, "forced_sleep")
        self.assertEqual(fatigue_stage(_state(300000, VOLUNTARY)).value, "sleeping")

    def test_foot_speed_scale_applies_the_next_consumed_band_at_a_floor(self):
        self.assertEqual(foot_speed_scale(_state(FULL)), Fraction(1))
        self.assertEqual(foot_speed_scale(_state(252001)), Fraction(1))
        # 252000 is still the normal stage, but the next unit consumed is light.
        self.assertEqual(foot_speed_scale(_state(252000)), Fraction(9, 10))
        self.assertEqual(foot_speed_scale(_state(144000)), Fraction(3, 4))
        self.assertEqual(foot_speed_scale(_state(143999)), Fraction(3, 4))
        self.assertEqual(foot_speed_scale(_state(72000)), Fraction(1, 2))
        self.assertEqual(foot_speed_scale(_state(71999)), Fraction(1, 2))

    def test_sleeping_postures_forbid_travel_and_actions_but_not_targeting(self):
        for posture in (VOLUNTARY, FORCED):
            state = _state(WAKE, posture)
            self.assertFalse(travel_allowed(state))
            self.assertFalse(actions_allowed(state))
            with self.assertRaises(fatigue.FatigueStateError) as caught:
                foot_speed_scale(state)
            self.assertIs(caught.exception.reason, FatigueRejectReason.TRAVEL_FORBIDDEN)
        self.assertTrue(travel_allowed(_state(1)))
        self.assertTrue(actions_allowed(_state(1)))


class ExactRateTests(TestCase):
    """Rates, clamping, split equivalence and calibration."""

    def _end(self, state, activity, seconds, **kwargs):
        return predict_interval(state, activity, seconds, **kwargs).end

    def test_full_day_calibration(self):
        after_walk = self._end(_state(FULL), FatigueActivity.FOOT_TRAVEL, 6 * 3600)
        self.assertEqual(after_walk.reserve_units, 187200)  # 52 percent
        after_awake = self._end(after_walk, FatigueActivity.AWAKE, 10 * 3600)
        self.assertEqual(after_awake.reserve_units, 43200)  # 12 percent
        after_sleep = self._end(
            _state(43200, VOLUNTARY), FatigueActivity.SLEEP, 8 * 3600
        )
        self.assertEqual(after_sleep.reserve_units, FULL)
        self.assertEqual(after_sleep.reserve_units * 100 // FULL, 100)

    def test_split_and_unsplit_intervals_are_identical(self):
        unsplit = self._end(_state(FULL), FatigueActivity.AWAKE, 3)
        one = self._end(_state(FULL), FatigueActivity.AWAKE, 1)
        split = self._end(one, FatigueActivity.AWAKE, 2)
        self.assertEqual(unsplit.reserve_units, FULL - 12)
        self.assertEqual(split, unsplit)
        sleep_unsplit = self._end(_state(70000, FORCED), FatigueActivity.SLEEP, 3)
        sleep_one = self._end(_state(70000, FORCED), FatigueActivity.SLEEP, 1)
        sleep_split = self._end(sleep_one, FatigueActivity.SLEEP, 2)
        self.assertEqual(sleep_split, sleep_unsplit)

    def test_sleep_saturates_identically_in_parts(self):
        unsplit = self._end(_state(FULL - 12, VOLUNTARY), FatigueActivity.SLEEP, 2)
        one = self._end(_state(FULL - 12, VOLUNTARY), FatigueActivity.SLEEP, 1)
        split = self._end(one, FatigueActivity.SLEEP, 1)
        self.assertEqual(unsplit.reserve_units, FULL)
        self.assertEqual(split.reserve_units, FULL)

    def test_continuous_walking_has_no_daily_quota_or_midnight_reset(self):
        # 45,000 s at 8 units/s is exactly twelve and a half hours of reserve.
        prediction = predict_interval(
            _state(FULL),
            FatigueActivity.FOOT_TRAVEL,
            45000,
            completion=IntervalCompletion.INDIVISIBLE,
        )
        self.assertEqual(prediction.end.reserve_units, 0)
        self.assertIs(prediction.end.posture, FORCED)
        self.assertIs(prediction.transition, TransitionReason.DEPLETION)

    def test_terrain_never_adds_a_multiplier_because_only_time_matters(self):
        # Equal seconds of the same activity are equal reserve cost.
        first = self._end(_state(FULL), FatigueActivity.FOOT_TRAVEL, 900)
        second = self._end(_state(FULL), FatigueActivity.FOOT_TRAVEL, 900)
        self.assertEqual(first, second)

    def test_true_and_out_of_range_values_are_rejected_before_mutation(self):
        entity = _FakeEntity("t_probe", FULL)
        for reserve in (True, 1.5, "1", -1, FULL + 1):
            with self.subTest(reserve=reserve):
                with self.assertRaises(fatigue.FatigueStateError):
                    write_fatigue_state(entity, reserve, AWAKE)
                self.assertEqual(entity.stored(fatigue.RESERVE_ATTRIBUTE), FULL)
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            write_fatigue_state(entity, FULL, "sleepwalking")
        self.assertIs(caught.exception.reason, FatigueRejectReason.UNKNOWN_POSTURE)
        self.assertEqual(entity.stored(fatigue.POSTURE_ATTRIBUTE), "awake")


class BoundaryAndPredictionTests(TestCase):
    """Pure, exact and write-free prediction for rules consumers."""

    def test_full_walk_boundary_is_exactly_13500_seconds(self):
        boundary = next_fatigue_boundary(
            _state(FULL), FatigueActivity.FOOT_TRAVEL
        )
        self.assertEqual(boundary.offset_seconds, Fraction(13500))
        self.assertIs(boundary.kind, BoundaryKind.THRESHOLD)
        self.assertEqual(boundary.reserve_units, 252000)

    def test_fractional_boundary_offsets_stay_exact(self):
        # One unit above the normal floor at 8 units/s is one eighth of a second.
        boundary = next_fatigue_boundary(
            _state(252001), FatigueActivity.FOOT_TRAVEL
        )
        self.assertEqual(boundary.offset_seconds, Fraction(1, 8))
        self.assertEqual(boundary.reserve_units, 252000)
        depletion = next_fatigue_boundary(_state(1), FatigueActivity.FOOT_TRAVEL)
        self.assertEqual(depletion.offset_seconds, Fraction(1, 8))
        self.assertIs(depletion.kind, BoundaryKind.DEPLETION)

    def test_interactive_advance_takes_the_first_whole_second_at_the_boundary(self):
        prediction = predict_interval(
            _state(252001), FatigueActivity.FOOT_TRAVEL, 100
        )
        self.assertEqual(prediction.applicable_seconds, 1)
        self.assertEqual(prediction.seconds, 100)

    def test_piecewise_prediction_covers_25987_5_metres_in_six_hours(self):
        speed = Fraction(4500, 3600)  # 4.5 km/h in metres per second
        state = _state(FULL)
        remaining = 6 * 3600
        distance = Fraction(0)
        while remaining:
            prediction = predict_interval(
                state, FatigueActivity.FOOT_TRAVEL, remaining
            )
            accepted = prediction.applicable_seconds
            self.assertGreater(accepted, 0)
            distance += speed * foot_speed_scale(state) * accepted
            state = predict_interval(
                state, FatigueActivity.FOOT_TRAVEL, accepted
            ).end
            remaining -= accepted
        self.assertEqual(distance, Fraction(259875, 10))
        self.assertEqual(state.reserve_units, 187200)
        self.assertEqual(fatigue_stage(state).value, "light")

    def test_forced_sleeper_wakes_after_6000_seconds_outside_combat(self):
        boundary = next_fatigue_boundary(
            _state(0, FORCED), FatigueActivity.SLEEP
        )
        self.assertEqual(boundary.offset_seconds, Fraction(6000))
        self.assertIs(boundary.kind, BoundaryKind.WAKE)
        prediction = predict_interval(
            _state(0, FORCED), FatigueActivity.SLEEP, 6000
        )
        self.assertEqual(prediction.end.reserve_units, WAKE)
        self.assertIs(prediction.end.posture, AWAKE)
        self.assertIs(prediction.transition, TransitionReason.WAKE)
        self.assertEqual(fatigue_stage(prediction.end).value, "moderate")

    def test_voluntary_sleep_has_no_natural_wake_boundary(self):
        self.assertIsNone(
            next_fatigue_boundary(_state(1000, VOLUNTARY), FatigueActivity.SLEEP)
        )

    def test_forced_sleep_latches_until_the_exact_wake_threshold(self):
        for reserve in (1, 71999):
            state = _state(reserve, FORCED)
            prediction = predict_interval(state, FatigueActivity.SLEEP, 0)
            self.assertIs(prediction.end.posture, FORCED)
        at_threshold = predict_interval(
            _state(WAKE, FORCED), FatigueActivity.SLEEP, 0
        )
        self.assertIs(at_threshold.end.posture, AWAKE)
        self.assertIs(at_threshold.transition, TransitionReason.WAKE)

    def test_live_combat_and_terminal_settlement_suppress_natural_wake(self):
        for kwargs in (
            {"in_combat": True},
            {"completion": IntervalCompletion.TERMINAL_COMBAT},
        ):
            prediction = predict_interval(
                _state(71999, FORCED), FatigueActivity.SLEEP, 1, **kwargs
            )
            self.assertIs(prediction.end.posture, FORCED)
            self.assertIsNot(prediction.transition, TransitionReason.WAKE)

    def test_forced_sleeper_above_the_threshold_releases_immediately(self):
        for reserve in (WAKE, WAKE + 4, FULL):
            prediction = predict_interval(
                _state(reserve, FORCED), FatigueActivity.SLEEP, 0
            )
            self.assertIs(prediction.end.posture, AWAKE)

    def test_prediction_reports_depletion_before_arrival_without_writing(self):
        entity = _FakeEntity("t_route", FULL)
        start = read_fatigue_state(entity)
        before = dict(entity.attributes.values)
        prediction = predict_interval(
            start, FatigueActivity.FOOT_TRAVEL, 50000
        )
        self.assertIs(prediction.transition, TransitionReason.DEPLETION)
        self.assertEqual(prediction.end.reserve_units, 0)
        self.assertIs(prediction.end.posture, FORCED)
        # The next boundary from full reserve is the 70 percent floor; the
        # depletion itself is at 45,000 s, still before the requested arrival.
        self.assertEqual(prediction.boundary.offset_seconds, Fraction(13500))
        depletion = next_fatigue_boundary(_state(1000), FatigueActivity.FOOT_TRAVEL)
        self.assertEqual(depletion.offset_seconds, Fraction(125))
        self.assertIs(depletion.kind, BoundaryKind.DEPLETION)
        self.assertEqual(entity.attributes.values, before)

    def test_prediction_and_reads_emit_no_log_event(self):
        entity = _FakeEntity("t_quiet", FULL)
        with patch("world.rules.fatigue.log_info") as logged:
            state = read_fatigue_state(entity)
            predict_interval(state, FatigueActivity.AWAKE, 10000)
            next_fatigue_boundary(state, FatigueActivity.AWAKE)
            fatigue_stage(state)
            foot_speed_scale(state)
        logged.assert_not_called()

    def test_activity_and_posture_must_agree(self):
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            predict_interval(_state(FULL), FatigueActivity.SLEEP, 1)
        self.assertIs(
            caught.exception.reason, FatigueRejectReason.ACTIVITY_POSTURE_MISMATCH
        )
        with self.assertRaises(fatigue.FatigueStateError):
            predict_interval(_state(0, FORCED), FatigueActivity.AWAKE, 1)

    def test_invalid_seconds_and_completion_are_rejected(self):
        for seconds in (True, -1, 1.5):
            with self.subTest(seconds=seconds):
                with self.assertRaises(fatigue.FatigueStateError):
                    predict_interval(_state(FULL), FatigueActivity.AWAKE, seconds)
        with self.assertRaises(fatigue.FatigueStateError):
            predict_interval(
                _state(FULL), FatigueActivity.AWAKE, 1, completion="interruptible"
            )


class ConstructionTests(EvenniaTest):
    """Construction baseline, repeat synchronization, corruption and reload."""

    def test_new_construction_is_full_and_awake_and_reloads(self):
        character = create_object(PlayerCharacter, key="t_fresh_body")
        self.assertEqual(
            read_fatigue_state(character),
            FatigueState(reserve_units=FULL, posture=AWAKE),
        )
        character.flush_cached_instance(character)
        flush_cache()
        reloaded = PlayerCharacter.objects.get(id=character.id)
        self.assertEqual(
            read_fatigue_state(reloaded),
            FatigueState(reserve_units=FULL, posture=AWAKE),
        )

    def test_repeat_synchronization_preserves_valid_fatigue(self):
        character = create_object(PlayerCharacter, key="t_tired_body")
        character.attributes.add(fatigue.RESERVE_ATTRIBUTE, 120000)
        self.assertFalse(initialize_fatigue_state(character))
        self.assertFalse(initialize_fatigue_state(character))
        self.assertEqual(read_fatigue_state(character).reserve_units, 120000)
        self.assertIs(read_fatigue_state(character).posture, AWAKE)

    def test_malformed_state_is_never_repaired_and_reads_fail(self):
        character = create_object(PlayerCharacter, key="t_corrupt_body")
        character.attributes.add(fatigue.RESERVE_ATTRIBUTE, "oops")
        self.assertFalse(initialize_fatigue_state(character))
        self.assertEqual(
            character.attributes.get(fatigue.RESERVE_ATTRIBUTE), "oops"
        )
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            read_fatigue_state(character)
        self.assertIs(caught.exception.reason, FatigueRejectReason.INVALID_TYPE)

    def test_restoring_sp_never_refills_or_shares_reserve(self):
        first = create_object(PlayerCharacter, key="t_first_body")
        second = create_object(PlayerCharacter, key="t_second_body")
        write_fatigue_state(second, 100000, AWAKE)
        for entity, maximum in ((first, 20), (second, 20)):
            entity.traits.add(
                "sp", trait_type="gauge", base=maximum, min=0, max=maximum
            )
            entity.traits.sp.current = 1
        first.traits.sp.current = first.traits.sp.max
        second.traits.sp.current = second.traits.sp.max
        self.assertEqual(read_fatigue_state(first).reserve_units, FULL)
        self.assertEqual(read_fatigue_state(second).reserve_units, 100000)
        self.assertEqual(first.traits.sp.current, 20)
        self.assertEqual(second.traits.sp.current, 20)

    def test_forced_sleeper_reload_keeps_posture_and_wake_eligibility(self):
        character = create_object(PlayerCharacter, key="t_reloaded_sleeper")
        character.attributes.add(fatigue.RESERVE_ATTRIBUTE, 71999)
        character.attributes.add(fatigue.POSTURE_ATTRIBUTE, "forced")
        character.flush_cached_instance(character)
        flush_cache()
        reloaded = PlayerCharacter.objects.get(id=character.id)
        state = read_fatigue_state(reloaded)
        self.assertEqual(state.reserve_units, 71999)
        self.assertIs(state.posture, FORCED)
        awake = predict_interval(state, FatigueActivity.SLEEP, 1)
        self.assertIs(awake.end.posture, AWAKE)
        in_battle = predict_interval(state, FatigueActivity.SLEEP, 1, in_combat=True)
        self.assertIs(in_battle.end.posture, FORCED)

    def test_missing_state_is_reported_and_never_materialized(self):
        character = create_object(PlayerCharacter, key="t_legacy_body")
        character.attributes.remove(fatigue.RESERVE_ATTRIBUTE)
        character.attributes.remove(fatigue.POSTURE_ATTRIBUTE)
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            read_fatigue_state(character)
        self.assertIs(caught.exception.reason, FatigueRejectReason.MISSING)
        self.assertFalse(character.attributes.has(fatigue.RESERVE_ATTRIBUTE))
        self.assertFalse(character.attributes.has(fatigue.POSTURE_ATTRIBUTE))

    def test_authored_synchronization_establishes_absent_state_only(self):
        host = create_object(NPC, key="t_sync_host")
        host.attributes.remove(fatigue.RESERVE_ATTRIBUTE)
        host.attributes.remove(fatigue.POSTURE_ATTRIBUTE)
        people = {"t_sync_person": object()}
        with (
            patch.object(hosts, "validate_adventurers"),
            patch.object(hosts, "find_persistent_adventurer", return_value=host),
        ):
            (synced,) = hosts.sync_persistent_adventurers(
                people=people, profiles={}, qualifications=()
            )
            self.assertEqual(
                read_fatigue_state(synced),
                FatigueState(reserve_units=FULL, posture=AWAKE),
            )
            synced.attributes.add(fatigue.RESERVE_ATTRIBUTE, 120000)
            (again,) = hosts.sync_persistent_adventurers(
                people=people, profiles={}, qualifications=()
            )
            self.assertEqual(read_fatigue_state(again).reserve_units, 120000)
            again.attributes.add(fatigue.RESERVE_ATTRIBUTE, "oops")
            (corrupt,) = hosts.sync_persistent_adventurers(
                people=people, profiles={}, qualifications=()
            )
            self.assertEqual(
                corrupt.attributes.get(fatigue.RESERVE_ATTRIBUTE), "oops"
            )


class SettlementTests(EvenniaTest):
    """The sole fatigue writer: validation, atomicity, rollback and events."""

    def test_two_members_settle_their_own_declared_activity(self):
        walker = create_object(PlayerCharacter, key="t_walker", location=self.room1)
        thinker = create_object(PlayerCharacter, key="t_thinker", location=self.room1)
        sleeper = create_object(PlayerCharacter, key="t_sleeper")
        sleeper.attributes.add(fatigue.RESERVE_ATTRIBUTE, 0)
        sleeper.attributes.add(fatigue.POSTURE_ATTRIBUTE, "forced")
        intervals = (
            FatigueInterval(
                walker, FatigueActivity.FOOT_TRAVEL, 600, read_fatigue_state(walker)
            ),
            FatigueInterval(
                thinker, FatigueActivity.AWAKE, 600, read_fatigue_state(thinker)
            ),
            FatigueInterval(
                sleeper, FatigueActivity.SLEEP, 600, read_fatigue_state(sleeper)
            ),
        )
        with patch("world.rules.fatigue.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                settlement = settle_fatigue_intervals(
                    intervals,
                    context={"commander": "t_commander", "tick": 42, "session": "t_s"},
                )
        self.assertEqual(
            [commit.end.reserve_units for commit in settlement.commits],
            [FULL - 4800, FULL - 2400, 7200],
        )
        self.assertEqual(read_fatigue_state(walker).reserve_units, FULL - 4800)
        self.assertEqual(read_fatigue_state(thinker).reserve_units, FULL - 2400)
        self.assertEqual(read_fatigue_state(sleeper).reserve_units, 7200)
        self.assertIs(read_fatigue_state(sleeper).posture, FORCED)
        self.assertEqual(logged.call_count, 3)
        event = logged.call_args_list[0]
        self.assertEqual(event.args[0], "fatigue_transition")
        self.assertEqual(event.kwargs["context"]["char"], "t_walker")
        self.assertEqual(event.kwargs["context"]["room"], self.room1.key)
        self.assertEqual(event.kwargs["context"]["commander"], "t_commander")
        self.assertEqual(event.kwargs["context"]["tick"], 42)
        self.assertEqual(event.kwargs["context"]["session"], "t_s")
        self.assertEqual(event.kwargs["context"]["reason"], "reserve_change")

    def test_stale_start_is_rejected_before_any_write(self):
        first = _FakeEntity("t_first", FULL)
        second = _FakeEntity("t_second", FULL)
        stale = FatigueState(reserve_units=FULL - 4, posture=AWAKE)
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            settle_fatigue_intervals(
                (
                    FatigueInterval(
                        first, FatigueActivity.AWAKE, 10, read_fatigue_state(first)
                    ),
                    FatigueInterval(second, FatigueActivity.AWAKE, 10, stale),
                )
            )
        self.assertIs(caught.exception.reason, FatigueRejectReason.STALE_START)
        self.assertEqual(first.stored(fatigue.RESERVE_ATTRIBUTE), FULL)
        self.assertEqual(second.stored(fatigue.RESERVE_ATTRIBUTE), FULL)

    def test_every_member_is_validated_before_the_first_write(self):
        first = _FakeEntity("t_first", FULL)
        second = _FakeEntity("t_second", FULL)
        second.attributes.values[fatigue.RESERVE_ATTRIBUTE] = "oops"
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            settle_fatigue_intervals(
                (
                    FatigueInterval(
                        first, FatigueActivity.AWAKE, 10, read_fatigue_state(first)
                    ),
                    FatigueInterval(
                        second, FatigueActivity.AWAKE, 10, _state(FULL)
                    ),
                )
            )
        self.assertIs(caught.exception.reason, FatigueRejectReason.INVALID_TYPE)
        self.assertEqual(first.stored(fatigue.RESERVE_ATTRIBUTE), FULL)

    def test_duplicate_member_is_rejected(self):
        first = _FakeEntity("t_first", FULL)
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            settle_fatigue_intervals(
                (
                    FatigueInterval(
                        first, FatigueActivity.AWAKE, 10, read_fatigue_state(first)
                    ),
                    FatigueInterval(
                        first, FatigueActivity.AWAKE, 10, read_fatigue_state(first)
                    ),
                )
            )
        self.assertIs(caught.exception.reason, FatigueRejectReason.DUPLICATE_MEMBER)

    def test_interruptible_interval_may_not_cross_a_boundary(self):
        body = _FakeEntity("t_body", FULL)
        with self.assertRaises(fatigue.FatigueStateError) as caught:
            settle_fatigue_intervals(
                (
                    FatigueInterval(
                        body,
                        FatigueActivity.FOOT_TRAVEL,
                        20000,
                        read_fatigue_state(body),
                    ),
                )
            )
        self.assertIs(
            caught.exception.reason, FatigueRejectReason.INTERRUPTIBLE_OVERRUN
        )
        self.assertEqual(body.stored(fatigue.RESERVE_ATTRIBUTE), FULL)

    def test_indivisible_completion_commits_the_whole_interval(self):
        body = _FakeEntity("t_body", FULL)
        prediction = predict_interval(
            read_fatigue_state(body),
            FatigueActivity.FOOT_TRAVEL,
            50000,
            completion=IntervalCompletion.INDIVISIBLE,
        )
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    body,
                    FatigueActivity.FOOT_TRAVEL,
                    50000,
                    read_fatigue_state(body),
                    IntervalCompletion.INDIVISIBLE,
                ),
            )
        )
        self.assertEqual(settlement.commits[0].end, prediction.end)
        self.assertEqual(settlement.commits[0].end.reserve_units, 0)
        self.assertIs(settlement.commits[0].end.posture, FORCED)

    def test_unchanged_settlement_emits_no_event(self):
        body = _FakeEntity("t_body", FULL)
        with patch("world.rules.fatigue.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                settlement = settle_fatigue_intervals(
                    (
                        FatigueInterval(
                            body, FatigueActivity.AWAKE, 0, read_fatigue_state(body)
                        ),
                    )
                )
        self.assertEqual(settlement.commits[0].end.reserve_units, FULL)
        logged.assert_not_called()

    def test_fault_after_the_second_member_write_restores_every_member(self):
        first = create_object(PlayerCharacter, key="t_first", location=self.room1)
        second = create_object(PlayerCharacter, key="t_second", location=self.room1)
        second.attributes.add(fatigue.RESERVE_ATTRIBUTE, 300000)
        before = (read_fatigue_state(first), read_fatigue_state(second))
        real_write = fatigue.write_fatigue_state
        written = []

        def faulty(entity, reserve_units, posture, policy=None):
            state = real_write(entity, reserve_units, posture, policy)
            written.append(entity)
            if len(written) == 2:
                raise RuntimeError("injected second-member write failure")
            return state

        with patch("world.rules.fatigue.write_fatigue_state", side_effect=faulty):
            with patch("world.rules.fatigue.log_info") as logged:
                with self.captureOnCommitCallbacks(execute=True):
                    with self.assertRaises(RuntimeError):
                        settle_fatigue_intervals(
                            (
                                FatigueInterval(
                                    first,
                                    FatigueActivity.AWAKE,
                                    600,
                                    read_fatigue_state(first),
                                ),
                                FatigueInterval(
                                    second,
                                    FatigueActivity.FOOT_TRAVEL,
                                    600,
                                    read_fatigue_state(second),
                                ),
                            )
                        )
        logged.assert_not_called()
        self.assertEqual(len(written), 2)
        self.assertEqual(
            (read_fatigue_state(first), read_fatigue_state(second)), before
        )
        first.flush_cached_instance(first)
        second.flush_cached_instance(second)
        flush_cache()
        self.assertEqual(
            (
                read_fatigue_state(PlayerCharacter.objects.get(id=first.id)),
                read_fatigue_state(PlayerCharacter.objects.get(id=second.id)),
            ),
            before,
        )

    def test_enclosing_advance_snapshot_owns_fatigue_state(self):
        first = create_object(PlayerCharacter, key="t_first", location=self.room1)
        second = create_object(PlayerCharacter, key="t_second", location=self.room1)
        before = (read_fatigue_state(first), read_fatigue_state(second))
        registry = build_advance_snapshot_registry(
            WorldClock(), 600, AdvanceSource.COMMAND, (first, second)
        )
        for entity in (first, second):
            attributes = registry[id(entity)].attributes
            self.assertIn((fatigue.RESERVE_ATTRIBUTE, None), attributes)
            self.assertIn((fatigue.POSTURE_ATTRIBUTE, None), attributes)
        settle_fatigue_intervals(
            (
                FatigueInterval(
                    first, FatigueActivity.AWAKE, 600, read_fatigue_state(first)
                ),
                FatigueInterval(
                    second, FatigueActivity.FOOT_TRAVEL, 600, read_fatigue_state(second)
                ),
            )
        )
        self.assertNotEqual(read_fatigue_state(first), before[0])
        _restore_advance_registry(registry, (first, second))
        self.assertEqual(
            (read_fatigue_state(first), read_fatigue_state(second)), before
        )
