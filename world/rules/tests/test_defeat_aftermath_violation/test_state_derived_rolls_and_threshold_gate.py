"""Slice of ``test_defeat_aftermath_violation``: StateDerivedRollTests, ThresholdGateTests.
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
    _kinds,
)


class StateDerivedRollTests(unittest.TestCase):
    """The pure derivation: deterministic, key-sensitive, d100-bounded."""

    def test_repeated_calls_with_identical_keys_are_identical(self):
        first = derived_roll("hostile:1:100", "7", "3", 0, "resist")
        second = derived_roll("hostile:1:100", "7", "3", 0, "resist")
        self.assertEqual(first, second)

    def test_every_key_field_shifts_the_roll(self):
        base_args = ("hostile:1:100", "7", "3", 0, "resist")
        base = derived_roll(*base_args)
        shifted = 0
        for field in range(5):
            variants = set()
            for delta in range(1, 9):
                args = list(base_args)
                args[field] = (
                    delta if field == 3 else f"{args[field]}#{delta}"
                )
                variants.add(derived_roll(*args))
            if base not in variants and len(variants) > 1:
                shifted += 1
        # Every field materially participates in the digest: mutating it
        # moves the roll for this sample of keys (one benign collision on a
        # mutated value would still leave len(variants) > 1).
        self.assertEqual(shifted, 5)

    def test_rolls_stay_in_the_d100_range(self):
        for index in range(200):
            value = derived_roll("hostile:1:100", str(index), "3", index, "resist")
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 100)

    def test_distribution_over_the_key_space_is_bounded(self):
        samples = 4000
        buckets = [0] * 101
        for index in range(samples):
            buckets[
                derived_roll("hostile:1:100", str(index), "3", index, "resist")
            ] += 1
        observed = buckets[1:]
        expected = samples / 100
        # A keyed hash is not a casino die; the design pins only uniformity
        # across the key space within generous bounds (D-V4 risk note).
        self.assertGreater(min(observed), expected * 0.4)
        self.assertLess(max(observed), expected * 1.7)

    def test_malformed_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            derived_roll("", "7", "3", 0, "resist")
        for bad in ("|hostile", "hostile|"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    derived_roll(bad, "7", "3", 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", bad, "3", 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", "7", bad, 0, "resist")
                with self.assertRaises(ValueError):
                    derived_roll("hostile:1:100", "7", "3", 0, bad)
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100|7", "7", "3", 0, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "", 0, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", -1, "resist")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", 0, "")
        with self.assertRaises(ValueError):
            derived_roll("hostile:1:100", "7", "3", True, "resist")


class ThresholdGateTests(ViolationBase):
    """Victory arousal and the archetype threshold gate (D-V2)."""

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_below_threshold_winner_gains_the_delta_but_never_violates(self):
        result = self._defeat()
        entries = _aftermath_entries(result)
        self.assertNotIn("violation_attempt", _kinds(entries))
        # The goblin row's victory delta landed even without a sequence.
        self.assertEqual(self.monster.sexual.pleasure.value, 2)
        # The player's sexual state is untouched on the PG path.
        self.assertEqual(self.player.sexual.pleasure.value, 0)
        self.assertEqual(self.player.sexual.hostile_act_count, 0)
        self.assertEqual(self.player.sexual.interspecies_act_count, 0)

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
    )
    def test_mid_fight_arousal_carries_into_the_victory_gate(self):
        # One pleasure point below the 微興奮 band floor: only the victory
        # delta pushes the goblin over its threshold (the design's emergent
        # chain — the player's own casts provoke the violation).
        self._arouse(13)
        result = self._defeat()
        self.assertIn("violation_attempt", _kinds(_aftermath_entries(result)))

    @covers_requirement(
        "defeat-aftermath-violation-sequence::living-defeat-winners-gain-archetype-victory-arousal",
    )
    def test_pleasure_overflow_clamps_without_wrapping(self):
        self._arouse(99)
        result = self._defeat()
        self.assertEqual(self.monster.sexual.pleasure.value, 100)
        self.assertEqual(self.monster.sexual.arousal.level, "極限")
        self.assertIn("violation_attempt", _kinds(_aftermath_entries(result)))

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_missing_archetype_row_is_inert_and_logs_once(self):
        self.monster.key = "defeat goblin"
        self._arouse(90)
        with patch.object(defeat_aftermath_violation_module, "log_warn") as warn:
            result = self._defeat()
        self.assertNotIn("violation_attempt", _kinds(_aftermath_entries(result)))
        warnings = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_violation_archetype_missing"
        ]
        self.assertEqual(len(warnings), 1)
        context = warnings[0].kwargs["context"]
        self.assertEqual(context["archetype"], "defeat goblin")
        self.assertIn("tick", context)
