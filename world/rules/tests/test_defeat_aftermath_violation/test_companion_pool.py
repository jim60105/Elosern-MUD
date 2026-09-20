"""Slice of ``test_defeat_aftermath_violation``: CompanionPoolTests.
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
    ViolationBase,
    _aftermath_entries,
    _aftermath_logs,
    _kinds,
)


class CompanionPoolTests(ViolationBase):
    """The full violation pool: companion victims, exclusion, and wakes."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
        "defeat-aftermath-violation-sequence::each-attempt-rolls-the-shipped-resist-contest-with-the-victim-defending",
    )
    def test_knocked_out_companion_takes_her_own_writes_and_credits(self):
        companion = self._companion("violated companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Pool = [player, companion]; both target draws pick slot 1 (the
        # companion) and both contests land.
        with self._patch_purpose_rolls([1, 1], [1, 1]):
            result = forfeit(self.player)
        entries = _aftermath_entries(result)
        self.assertEqual(_kinds(entries).count("violation_attempt"), 2)
        self.assertEqual(_kinds(entries).count("violation_act"), 2)
        for entry in entries:
            if entry.kind in ("violation_attempt", "violation_act"):
                self.assertEqual(entry.target, str(companion.key))
        # Her own deltas and counters, never proxied through the player.
        self.assertEqual(companion.sexual.pleasure.value, 2 * 16)
        self.assertEqual(companion.sexual.hostile_act_count, 2)
        self.assertEqual(companion.sexual.interspecies_act_count, 2)
        # Symmetric crediting: the violator credits exactly once per attempt.
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 2)
        self.assertEqual(self.monster.sexual.pleasure.value, 13 + 2 + 2 * 10)
        # The player was never targeted and stays untouched.
        self.assertEqual(self.player.sexual.pleasure.value, 0)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        # Attempts landed only on her: the player's wake prose stays PG.
        settle = next(entry for entry in entries if entry.kind == "defeat_settle")
        self.assertEqual(settle.data["wake"], DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0])
        # Two executed attempts spend their declared durations; the recovery
        # solve then walks HP 1 to the 5% wake target (no round seconds).
        self.assertEqual(self.clock.tick, 2 * 120 + 8)
        self.assertEqual(self.player.traits.hp.current, 5)

    def test_fled_companion_is_excluded_before_the_draw(self):
        fled_companion = self._companion("zulu companion")
        knocked = self._companion("alpha companion")
        self._equalize_scores(knocked)
        self._arouse(13)
        engage(self.player, self.monster)
        self._flee(fled_companion)
        self._knock_out(knocked)
        # Pool = [player, knocked]: the fled companion is filtered out
        # before the draw, so slot 1 resolves to the knocked-out companion
        # even though the fled companion's key sorts first.
        with self._patch_purpose_rolls([1, 1], [1, 100]):
            result = forfeit(self.player)
        entries = _aftermath_entries(result)
        self.assertEqual(_kinds(entries).count("violation_act"), 1)
        self.assertEqual(
            [entry.target for entry in entries if entry.kind == "violation_act"],
            [str(knocked.key)],
        )
        # Landed deltas (16) plus the resisted attempt's shrunk delta (4).
        self.assertEqual(knocked.sexual.pleasure.value, 16 + 4)
        self.assertEqual(knocked.sexual.hostile_act_count, 1)
        # The fled companion's records are untouched: never selected.
        self.assertEqual(fled_companion.sexual.pleasure.value, 0)
        self.assertEqual(fled_companion.sexual.hostile_act_count, 0)
        self.assertEqual(fled_companion.sexual.interspecies_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-attempts-select-victims-from-the-target-pool",
    )
    def test_all_allies_fled_settles_like_the_solo_baseline(self):
        companion = self._companion("departed companion")
        self._equalize_scores()
        self._arouse(13)
        engage(self.player, self.monster)
        self._flee(companion)
        with self._patch_purpose_rolls([1, 1], [1, 1]) as rolls:
            result = forfeit(self.player)
        kinds = _kinds(_aftermath_entries(result))
        self.assertEqual(
            kinds,
            [
                "defeat_settle",
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_act",
                "weak_granted",
                "recovery_advance",
                "digest_outcome",
            ],
        )
        # A solo pool never touches the target dice: the pinned baseline's
        # derivation call shape (resist draws only) is preserved.
        for call in rolls.call_args_list:
            self.assertEqual(call.args[4], "resist")
        # Every attempt targeted the player; the fled companion is untouched.
        for entry in _aftermath_entries(result):
            if entry.kind in ("violation_attempt", "violation_act"):
                self.assertEqual(entry.target, str(self.player.key))
        self.assertEqual(companion.sexual.pleasure.value, 0)
        self.assertEqual(companion.sexual.hostile_act_count, 0)

    def test_mixed_two_victim_sequence_credits_the_violator_once_per_attempt(self):
        companion = self._companion("mixed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Attempt 0 draws slot 1 (the companion), attempt 1 slot 0 (the
        # player); both contests land.
        with patch.object(defeat_aftermath_violation_module, "log_info") as info:
            with self._patch_purpose_rolls([1, 0], [1, 1]):
                with self.captureOnCommitCallbacks(execute=True):
                    result = forfeit(self.player)
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertEqual(
            [entry.target for entry in acts],
            [str(companion.key), str(self.player.key)],
        )
        # One credit per attempt against the violator — never one per victim
        # per attempt (the double-credit risk D-P2 names).
        self.assertEqual(self.monster.sexual.hostile_act_count, 2)
        self.assertEqual(self.monster.sexual.interspecies_act_count, 2)
        self.assertEqual(companion.sexual.hostile_act_count, 1)
        self.assertEqual(self.player.sexual.hostile_act_count, 1)
        # Boundary telemetry: victims counts distinct selected participants.
        boundary = [
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_violation"
        ]
        self.assertEqual(len(boundary), 1)
        self.assertEqual(boundary[0]["victims"], 2)
        self.assertEqual(boundary[0]["attempts"], 2)
        self.assertEqual(boundary[0]["landed"], 2)

    def test_unselected_pool_companion_gets_no_outcome_and_no_wake_line(self):
        companion = self._companion("overlooked companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        captured = {}
        real_writer = defeat_aftermath_module.run_defeat_aftermath

        def spy(actor, record, battlefield):
            outcome = real_writer(actor, record, battlefield)
            captured["outcomes"] = outcome.violation
            return outcome

        with (
            self._patch_purpose_rolls([0, 0], [1, 1]),
            patch.object(
                defeat_aftermath_module, "run_defeat_aftermath", side_effect=spy
            ),
        ):
            result = forfeit(self.player)
        # Both attempts drew slot 0 (the player): the companion is absent
        # from the outcome mapping (D-P3) and gets no wake observation.
        self.assertEqual(set(captured["outcomes"]), {str(self.player.key)})
        self.assertNotIn("companion_wake", _kinds(_aftermath_entries(result)))
        self.assertEqual(companion.sexual.pleasure.value, 0)
        self.assertEqual(companion.sexual.hostile_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::knocked-out-companions-wake-with-their-own-digest-observation",
    )
    def test_companion_wake_observation_is_rendered_with_matching_counts(self):
        companion = self._companion("waking companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        with self._patch_purpose_rolls([1, 1], [1, 1]):
            result = forfeit(self.player)
        (log,) = _aftermath_logs(result)
        wakes = [entry for entry in log.entries if entry.kind == "companion_wake"]
        self.assertEqual(len(wakes), 1)
        wake = wakes[0]
        self.assertEqual(wake.actor, str(companion.key))
        self.assertEqual(
            wake.data,
            {
                "selected": 2,
                "landed": 2,
                "resisted": 0,
                "climax": 0,
                "zero_landed": False,
            },
        )
        # The counts equal the EventLog's own entry counts for her.
        self.assertEqual(
            wake.data["selected"],
            sum(
                1
                for entry in log.entries
                if entry.kind == "violation_attempt"
                and entry.target == str(companion.key)
            ),
        )
        self.assertEqual(
            wake.data["landed"],
            sum(
                1
                for entry in log.entries
                if entry.kind == "violation_act"
                and entry.target == str(companion.key)
            ),
        )
        # The observation renders exactly once, naming her.
        lines = render_plain_text(log).splitlines()
        rendered = [
            line
            for entry, line in zip(log.entries, lines)
            if entry.kind == "companion_wake"
        ]
        self.assertEqual(len(rendered), 1)
        self.assertIn(str(companion.key), rendered[0])

    def test_companion_violation_entries_render_their_companion_templates(self):
        from world.rules.player_messages import DEFEAT_AFTERMATH_TEMPLATES

        companion = self._companion("observed companion")
        self._equalize_scores(companion)
        self._arouse(13)
        engage(self.player, self.monster)
        self._knock_out(companion)
        # Attempt 0 lands on her; attempt 1 is resisted by her (and is the
        # violator's last under the stop rule).
        with self._patch_purpose_rolls([1, 1], [1, 100]):
            result = forfeit(self.player)
        (log,) = _aftermath_logs(result)
        entries = [
            entry for entry in log.entries if entry.kind.startswith("violation_")
        ]
        self.assertEqual(
            [entry.kind for entry in entries],
            [
                "violation_attempt",
                "violation_act",
                "violation_attempt",
                "violation_resisted",
            ],
        )
        for entry in entries:
            self.assertEqual(entry.target, str(companion.key))
        self.assertEqual(
            [entry.text_template for entry in entries],
            [
                DEFEAT_AFTERMATH_TEMPLATES["violation_attempt_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_act_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_attempt_companion"],
                DEFEAT_AFTERMATH_TEMPLATES["violation_resisted_companion"],
            ],
        )
        lines = render_plain_text(log).splitlines()
        rendered = [
            line
            for entry, line in zip(log.entries, lines)
            if entry.kind.startswith("violation_")
        ]
        for line in rendered:
            self.assertIn(str(companion.key), line)

    def test_pool_order_is_canonical_across_paths(self):
        zulu = self._companion("zulu companion")  # created first: lower pk
        alpha = self._companion("alpha companion")  # created second: higher pk
        standing = self._companion("standing companion")
        engage(self.player, self.monster)
        self._knock_out(zulu)
        self._knock_out(alpha)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        pool_live = defeat_aftermath_module._violation_pool(
            self.player, record, battlefield
        )
        pool_degraded = defeat_aftermath_module._violation_pool(
            self.player, record, None
        )
        # Canonical order (player first, companions by ascending pk) is
        # identical from both paths even though the keys sort differently.
        self.assertEqual(pool_live, pool_degraded)
        self.assertEqual(
            [str(entity.key) for entity in pool_live],
            [str(self.player.key), "zulu companion", "alpha companion"],
        )
        # A conscious companion is never a pool member.
        self.assertNotIn(
            str(standing.key), [str(entity.key) for entity in pool_live]
        )
