"""Behavior tests for the server-owned dream arousal track and its ending.

Covers the versioned track configuration and its committed progression report,
the six-step traversal of the canonical five bands with exactly one increment
per completed exchange, convergence-gated climax eligibility, prospective-phase
reuse under retries/duplicates/failures, the exchange-mode ladder, the
generation-free phase-aware ending (early exit and offline climax), and the
forbidden-write contract: no live ``SexualState`` trait, counter, or sleep
effect changes.
"""

from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from evennia.utils.test_resources import EvenniaTest

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS
from world.narrative import dream_track
from world.narrative.dream_session import CONVERGENCE_EXCHANGE, MAX_EXCHANGES
from world.narrative.dream_track import (
    CLIMAX_AFTERGLOW,
    CLIMAX_APPROACHING,
    CLIMAX_NOT_REACHED,
    CLIMAX_ONGOING,
    EXCHANGE_DELTAS,
    INITIAL_PLEASURE,
    MAX_PLEASURE,
    MODE_CONVERGENCE,
    MODE_EXCHANGE,
    MODE_SUMMARY,
    TRACK_VERSION,
    DreamTrackRangeError,
    exchange_mode,
    progression_report,
    prospective_state,
    render_ending,
    track_state,
)


class DreamTrackConfigurationTests(unittest.TestCase):
    """The versioned configuration and its committed progression evidence."""

    def test_committed_configuration_has_one_delta_per_exchange(self):
        self.assertEqual(TRACK_VERSION, 1)
        self.assertEqual(INITIAL_PLEASURE, 0)
        self.assertEqual(len(EXCHANGE_DELTAS), MAX_EXCHANGES)
        self.assertTrue(
            all(isinstance(d, int) and not isinstance(d, bool) for d in EXCHANGE_DELTAS)
        )
        self.assertTrue(all(delta > 0 for delta in EXCHANGE_DELTAS))
        self.assertEqual(EXCHANGE_DELTAS, (14, 18, 20, 14, 20, 14))
        self.assertGreaterEqual(sum(EXCHANGE_DELTAS), MAX_PLEASURE)

    def test_progression_report_is_the_committed_evidence(self):
        report = progression_report()
        self.assertEqual(len(report), MAX_EXCHANGES)
        self.assertEqual([row.exchange_number for row in report], [1, 2, 3, 4, 5, 6])
        self.assertEqual([row.pleasure for row in report], [14, 32, 52, 66, 86, 100])
        self.assertEqual(
            [row.level for row in report],
            [AROUSAL_LEVELS[ordinal] for ordinal in (0, 1, 2, 3, 4, 4)],
        )
        self.assertEqual(
            [row.climax_phase for row in report],
            [
                CLIMAX_NOT_REACHED,
                CLIMAX_NOT_REACHED,
                CLIMAX_NOT_REACHED,
                CLIMAX_APPROACHING,
                CLIMAX_ONGOING,
                CLIMAX_ONGOING,
            ],
        )

    def test_six_distinct_exchanges_follow_the_canonical_bands_once_each(self):
        ordinals = [track_state(step).ordinal for step in range(1, MAX_EXCHANGES + 1)]
        self.assertEqual(ordinals, [0, 1, 2, 3, 4, 4])
        self.assertEqual(ordinals, sorted(ordinals))
        previous = INITIAL_PLEASURE
        for step, delta in enumerate(EXCHANGE_DELTAS, start=1):
            state = track_state(step)
            self.assertEqual(state.pleasure - previous, delta)
            previous = state.pleasure
        self.assertEqual(track_state(MAX_EXCHANGES).pleasure, MAX_PLEASURE)
        self.assertEqual(track_state(MAX_EXCHANGES).level, AROUSAL_LEVELS[-1])

    def test_climax_is_eligible_only_from_convergence(self):
        for step in range(CONVERGENCE_EXCHANGE):
            with self.subTest(step=step):
                self.assertNotEqual(track_state(step).climax_phase, CLIMAX_ONGOING)
                self.assertFalse(track_state(step).climax_reached)
        converging = track_state(CONVERGENCE_EXCHANGE)
        self.assertEqual(converging.climax_phase, CLIMAX_ONGOING)
        self.assertTrue(converging.climax_reached)
        self.assertTrue(converging.converging)

    def test_prospective_phase_is_stable_under_retries_and_duplicates(self):
        first = prospective_state(3)
        self.assertEqual(first, prospective_state(3))
        self.assertEqual(first, track_state(4))
        # A duplicate or failed settlement never advances the track: the
        # committed state for the same durable count is byte-identical.
        self.assertEqual(track_state(3), track_state(3))
        self.assertEqual(prospective_state(3), first)

    def test_prospective_lookahead_projects_forward_without_advancing_the_track(self):
        committed = track_state(2)
        lookahead = prospective_state(2)
        # A buggy pass-through returning the committed state would fail here.
        self.assertNotEqual(lookahead, committed)
        self.assertEqual(lookahead, track_state(3))
        self.assertEqual(track_state(2), committed)

    def test_exchange_modes_follow_the_six_exchange_contract(self):
        self.assertEqual(
            [exchange_mode(step) for step in range(MAX_EXCHANGES)],
            [
                MODE_EXCHANGE,
                MODE_EXCHANGE,
                MODE_EXCHANGE,
                MODE_EXCHANGE,
                MODE_CONVERGENCE,
                MODE_SUMMARY,
            ],
        )


class DreamTrackRangeTests(unittest.TestCase):
    def test_out_of_budget_counts_are_rejected(self):
        for bad in (-1, MAX_EXCHANGES + 1, True, "2", 2.0, None):
            with self.subTest(bad=bad):
                with self.assertRaises(DreamTrackRangeError):
                    track_state(bad)

    def test_prospective_state_requires_a_next_exchange(self):
        with self.assertRaises(DreamTrackRangeError):
            prospective_state(MAX_EXCHANGES)
        with self.assertRaises(DreamTrackRangeError):
            exchange_mode(MAX_EXCHANGES)


class DreamEndingTests(unittest.TestCase):
    def test_early_exit_fades_without_forcing_climax(self):
        ending = render_ending(2)
        self.assertFalse(ending.climax_reached)
        self.assertEqual(ending.phase, track_state(2).climax_phase)
        self.assertEqual(ending.phase, CLIMAX_NOT_REACHED)
        self.assertTrue(ending.fades)
        self.assertTrue(ending.awakens)

    def test_climax_ending_renders_the_post_climax_phase(self):
        ending = render_ending(CONVERGENCE_EXCHANGE)
        self.assertTrue(ending.climax_reached)
        self.assertEqual(ending.phase, CLIMAX_AFTERGLOW)
        self.assertEqual(ending.phase, CLIMAX_PHASE_LEVELS[3])
        self.assertTrue(ending.fades)
        self.assertTrue(ending.awakens)

    def test_ending_is_deterministic_and_versioned(self):
        self.assertEqual(render_ending(3), render_ending(3))
        self.assertEqual(render_ending(3).version, TRACK_VERSION)
        self.assertEqual(render_ending(3).completed, 3)

    def test_module_references_no_generative_layer_or_state_handler(self):
        source = Path(dream_track.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from world.ai", source)
        self.assertNotIn("import world.ai", source)
        self.assertNotIn("sexual_state.handler", source)
        self.assertNotIn("import SexualState", source)


class DreamTrackForbiddenWriteTests(EvenniaTest):
    """The track and the ending write no live character effect."""

    _MUTATORS = (
        "record_climax",
        "stage_climax_extension",
        "record_masturbation",
        "record_toy_use",
        "record_exposure_act",
        "record_watched",
        "record_duo_act",
        "record_group_act",
        "record_hostile_act",
        "record_restraint",
        "record_interspecies_act",
        "record_climax_count",
        "record_climax_extension",
        "saturate_sensitivity",
        "clamp_shame_to",
        "restore_purity",
        "add_experience_type",
        "mark_submission",
    )

    def _live_snapshot(self, entity):
        return (
            deepcopy(entity.attributes.get("sexual_traits", default=None, category="traits")),
            entity.sexual.pleasure.base,
            entity.sexual.climax_phase.level,
            entity.sexual.climax_today,
            entity.sexual.climax_count,
            entity.sexual.virgin,
            entity.sexual.experience_types,
            entity.sexual.submission_marks,
        )

    def test_completed_climax_leaves_live_effects_at_baseline(self):
        char = self.char1
        # Materialize a live handler with distinctive pre-existing state.
        char.sexual.pleasure.base = 60
        char.sexual.record_climax_count()
        before = self._live_snapshot(char)

        from world.rules.sexual_state.handler import SexualState

        spies = {
            name: Mock(side_effect=AssertionError(f"{name} must never be called"))
            for name in self._MUTATORS
        }
        with patch.multiple(SexualState, **spies):
            for step in range(MAX_EXCHANGES + 1):
                track_state(step)
                if step < MAX_EXCHANGES:
                    prospective_state(step)
                    exchange_mode(step)
                render_ending(step)
            for spy in spies.values():
                spy.assert_not_called()

        self.assertEqual(self._live_snapshot(char), before)

    def test_live_state_is_untouched_from_the_untouched_baseline(self):
        char = self.char2
        # Materialize the live handler deterministically, then snapshot it.
        self.assertIsNotNone(char.sexual.pleasure)
        pristine = self._live_snapshot(char)
        for step in range(MAX_EXCHANGES + 1):
            track_state(step)
            render_ending(step)
        self.assertEqual(self._live_snapshot(char), pristine)
        self.assertTrue(char.sexual.virgin)
        self.assertEqual(char.sexual.climax_today, 0)

    def test_offline_endings_require_no_model_call(self):
        # A generation-free renderer takes no client and performs no I/O: the
        # ending at every count is available while every service is offline.
        for step in range(MAX_EXCHANGES + 1):
            with self.subTest(step=step):
                ending = render_ending(step)
                self.assertTrue(ending.awakens)
        self.assertEqual(render_ending(MAX_EXCHANGES).phase, CLIMAX_AFTERGLOW)
