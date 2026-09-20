"""Slice of ``test_defeat_aftermath_violation``: RollbackReplayTests.
"""
import unittest
from dataclasses import replace as dataclass_replace
from unittest.mock import patch
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
import world.rules.defeat_aftermath as defeat_aftermath_module
import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.rules import clock as clock_module
from world.rules import combat_session as combat_session_module
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    forfeit,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    load_defeat_aftermath_sections,
    register_violation_hook,
    run_violation_sequence,
)
from world.rules.clock import WorldClock
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.state_derived_roll import derived_roll
from tools.spec_traceability import covers_requirement
from .._combat_session_helpers import BattlefieldIsolation, _player


from ._support import (
    EventSourceIsolation,
    ViolationBase,
    _aftermath_entries,
    _kinds,
)


class RollbackReplayTests(EventSourceIsolation, ViolationBase):
    """State-derived dice: a rolled-back retry re-derives the sequence."""

    def setUp(self):
        super().setUp()
        self.isolate_event_sources()

    @covers_requirement(
        "defeat-aftermath-violation-sequence::sequence-dice-are-state-derived-pure-values",
    )
    def test_rolled_back_settlement_rederives_the_identical_sequence(self):
        self._equalize_scores()
        self._arouse(13)
        # Force every contest to land through the shipped score formula (the
        # monster towers over the victim), so both cap attempts execute with
        # their real state-derived rolls and the injection aligns.
        self.monster.traits.agility.base = 500
        self.monster.traits.atk_phys.base = 500
        player_pleasure_before = self.player.sexual.pleasure.value
        monster_pleasure_before = self.monster.sexual.pleasure.value
        real_roll = defeat_aftermath_violation_module.derived_roll
        calls = []

        def recording_roll(session_id, violator_key, victim_key, attempt_index, purpose):
            value = real_roll(
                session_id, violator_key, victim_key, attempt_index, purpose
            )
            calls.append(
                (session_id, violator_key, victim_key, attempt_index, purpose, value)
            )
            return value

        advancing = patch.object(
            defeat_aftermath_violation_module,
            "_advance_attempt_clock",
            side_effect=[None, RuntimeError("injected")],
        )
        with (
            patch.object(
                defeat_aftermath_violation_module,
                "derived_roll",
                side_effect=recording_roll,
            ),
            advancing,
            self.assertRaises(RuntimeError),
        ):
            self._defeat()
        # The aborted run consumed both cap attempts' rolls: attempt 1's
        # deltas and entry were already applied when its advance failed.
        first_run_calls = list(calls)
        self.assertEqual(len(first_run_calls), 2)
        # Every write is absent: sexual state, counters, floor, session.
        self.assertEqual(self.player.sexual.pleasure.value, player_pleasure_before)
        self.assertEqual(self.monster.sexual.pleasure.value, monster_pleasure_before)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        self.assertEqual(self.monster.sexual.hostile_act_count, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        # The retry re-derives the identical roll for the same durable state
        # and completes the whole sequence exactly once.
        with patch.object(
            defeat_aftermath_violation_module, "derived_roll", side_effect=recording_roll
        ):
            # The durable session is still active after the rollback, so the
            # retry is a bare re-settlement (no re-engage, no extra round).
            result = forfeit(self.player)
        self.assertEqual(calls[len(first_run_calls):], first_run_calls)
        self.assertEqual(_kinds(_aftermath_entries(result)).count("violation_act"), 2)
        self.assertEqual(self.player.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(self.clock.tick, 6 + 2 * 120 + 8)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::sequence-dice-are-state-derived-pure-values",
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
    )
    def test_rolled_back_mixed_pool_rederives_the_identical_selection(self):
        companion = self._companion("replayed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        # The monster towers over both victims: every contest lands through
        # the shipped formula, so the real state-derived target draws and
        # resist rolls both execute.
        self.monster.traits.agility.base = 500
        self.monster.traits.atk_phys.base = 500
        engage(self.player, self.monster)
        self._knock_out(companion)
        real_roll = defeat_aftermath_violation_module.derived_roll
        calls = []

        def recording_roll(*args):
            value = real_roll(*args)
            calls.append((*args, value))
            return value

        advancing = patch.object(
            defeat_aftermath_violation_module,
            "_advance_attempt_clock",
            side_effect=[None, RuntimeError("injected")],
        )
        with (
            patch.object(
                defeat_aftermath_violation_module,
                "derived_roll",
                side_effect=recording_roll,
            ),
            advancing,
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        first_run_calls = list(calls)
        # Each executed attempt consumed exactly one target draw and one
        # resist roll; the first advance succeeded, the second failed.
        self.assertEqual(len(first_run_calls), 4)
        self.assertEqual(
            [call[4] for call in first_run_calls],
            ["target", "resist", "target", "resist"],
        )
        # The retry re-derives the identical draws (same victims, same
        # contests) for the same durable state and completes exactly once.
        with patch.object(
            defeat_aftermath_violation_module, "derived_roll", side_effect=recording_roll
        ):
            result = forfeit(self.player)
        self.assertEqual(calls[len(first_run_calls):], first_run_calls)
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertEqual(len(acts), 2)
        # Per-victim consistency: each body's counters equal the acts that
        # targeted it; the violator credited once per attempt overall.
        for victim in (self.player, companion):
            targeted = sum(
                1 for entry in acts if entry.target == str(victim.key)
            )
            self.assertEqual(victim.sexual.hostile_act_count, targeted)
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
