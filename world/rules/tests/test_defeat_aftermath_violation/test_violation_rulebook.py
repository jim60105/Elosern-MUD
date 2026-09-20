"""Slice of ``test_defeat_aftermath_violation``: ViolationRulebookTests.
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


class ViolationRulebookTests(unittest.TestCase):
    """The ``violation`` section's fail-closed loader validation (D-V2)."""

    VALID_HEADER = (
        "pg_lines:\n  - '你醒了。'\nweak_debuff:\n  buff_key: defeat_weak\n"
        "recovery:\n  regen_scale: 0.5\n  max_recovery_seconds: 21600\n"
        "  wake_fraction: 0.05\n"
        # The DA6-owned digest section: every owned section must be present
        # and valid for any single section's mutation to be the only failure.
        "digest:\n"
        "  rows:\n"
        "    - id: residue\n"
        "      when:\n"
        "        sensitivity_level: [高, 極高, 敏感異常]\n"
        "        outcome.climax_count: {min: 1}\n"
        "      outcome: residue\n"
        "      buff: aftermath_residue\n"
        "    - id: humiliated\n"
        "      when:\n"
        "        sensitivity_level: [普通]\n"
        "        shame_level: [強烈, 成癮]\n"
        "        outcome.zero_landed: true\n"
        "      outcome: humiliated\n"
        "      buff: aftermath_humiliated\n"
        "    - id: none\n"
        "      when: {}\n"
        "      outcome: none\n"
        "      buff: null\n"
    )

    def setUp(self):
        self._paths = []

    def tearDown(self):
        import os

        for path in self._paths:
            os.unlink(path)

    def _load(self, section_text):
        """Write one YAML body with the given violation section and load it."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(self.VALID_HEADER + section_text)
            path = handle.name
        self._paths.append(path)
        return load_defeat_aftermath_sections(Path(path))

    @staticmethod
    def _row(**overrides):
        fields = {
            "victory_pleasure_delta": "2",
            "threshold_ordinal": "1",
            "attempt_cap": "2",
            "attempt_duration_seconds": "120",
            "landed_deltas": "{victim_pleasure: 16, aggressor_pleasure: 10}",
            "resisted_deltas": "{victim_pleasure: 4, aggressor_pleasure: 3}",
            "credited_counters": "[hostile_act_count, interspecies_act_count]",
        }
        fields.update(overrides)
        return "".join(f"      {key}: {value}\n" for key, value in fields.items())

    def _section(self, wake_line="  violated_wake_line: '測試喚醒。'\n", row=None):
        return (
            "violation:\n"
            + wake_line
            + "  archetypes:\n"
            + "    哥布林:\n"
            + (row if row is not None else self._row())
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_valid_section_loads_immutable_rows(self):
        rulebook = self._load(self._section())
        row = rulebook.violation.rows["哥布林"]
        self.assertEqual(row.victory_pleasure_delta, 2)
        self.assertEqual(row.threshold_ordinal, 1)
        self.assertEqual(row.attempt_cap, 2)
        self.assertEqual(
            row.credited_counters, ("hostile_act_count", "interspecies_act_count")
        )

    @covers_requirement(
        "defeat-aftermath-violation-sequence::violation-sequence-runs-per-archetype-threshold-with-an-archetype-attempt-cap",
    )
    def test_non_lore_species_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section().replace("哥布林", "goblin"))

    def test_shame_key_is_rejected(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(row=self._row(threshold_ordinal="1\n      shame: 輕微"))
            )

    def test_unknown_row_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(row=self._row(threshold_ordinal="1\n      baseline: {}"))
            )

    def test_direction_bound_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(
                    row=self._row(credited_counters="[hostile_act_count, watched_count]")
                )
            )

    def test_unknown_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(credited_counters="[not_a_counter]")))

    def test_duplicate_credit_counter_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section(
                    row=self._row(credited_counters="[hostile_act_count, hostile_act_count]")
                )
            )

    def test_threshold_ordinal_out_of_vocabulary_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(threshold_ordinal="5")))

    def test_unknown_delta_key_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(landed_deltas="{victim_shame: 1}")))

    def test_empty_deltas_fail_closed(self):
        with self.assertRaises(ValueError):
            self._load(self._section(row=self._row(landed_deltas="{}")))

    def test_missing_wake_line_fails_closed(self):
        with self.assertRaises(ValueError):
            self._load(
                self._section().replace("  violated_wake_line: '測試喚醒。'\n", "")
            )
