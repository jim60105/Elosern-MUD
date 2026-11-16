"""Mechanism tests for the per-subrace start-location validator.

Every subrace registry here is synthetic: the validator is exercised against
fixtures built from the shared kit, never against shipped subrace keys.
"""

from __future__ import annotations

import unittest

from world.lore.start_locations import SubraceStartLocation, validate_start_locations
from world.tests.synthetic_data import make_subrace


def _subraces(*keys: str) -> dict[str, object]:
    return {key: make_subrace(key) for key in keys}


class ValidateStartLocationsTests(unittest.TestCase):
    def test_one_well_formed_row_per_subrace_is_accepted(self):
        subraces = _subraces("t_dawnfolk", "t_tidefolk")
        registry = {
            "t_dawnfolk": SubraceStartLocation("t_dawnfolk", "t_ember_vale"),
            "t_tidefolk": SubraceStartLocation("t_tidefolk", "t_salt_reach"),
        }

        self.assertIsNone(validate_start_locations(registry, subraces))

    def test_a_subrace_without_a_row_is_rejected_by_name(self):
        subraces = _subraces("t_dawnfolk", "t_tidefolk")
        registry = {
            "t_dawnfolk": SubraceStartLocation("t_dawnfolk", "t_ember_vale"),
        }

        with self.assertRaisesRegex(ValueError, "without a start location.*t_tidefolk"):
            validate_start_locations(registry, subraces)

    def test_a_row_for_an_unknown_subrace_is_rejected_by_name(self):
        subraces = _subraces("t_dawnfolk")
        registry = {
            "t_dawnfolk": SubraceStartLocation("t_dawnfolk", "t_ember_vale"),
            "t_ghostfolk": SubraceStartLocation("t_ghostfolk", "t_ember_vale"),
        }

        with self.assertRaisesRegex(ValueError, "'t_ghostfolk' names an unknown subrace"):
            validate_start_locations(registry, subraces)

    def test_a_row_whose_key_and_subrace_differ_is_rejected(self):
        subraces = _subraces("t_dawnfolk", "t_tidefolk")
        registry = {
            "t_dawnfolk": SubraceStartLocation("t_tidefolk", "t_ember_vale"),
            "t_tidefolk": SubraceStartLocation("t_tidefolk", "t_salt_reach"),
        }

        with self.assertRaisesRegex(
            ValueError, "'t_dawnfolk' declares mismatched subrace 't_tidefolk'"
        ):
            validate_start_locations(registry, subraces)

    def test_an_empty_or_non_string_anchor_key_is_rejected(self):
        subraces = _subraces("t_dawnfolk")
        for anchor in ("", None, 7):
            with self.subTest(anchor=anchor):
                registry = {"t_dawnfolk": SubraceStartLocation("t_dawnfolk", anchor)}
                with self.assertRaisesRegex(
                    ValueError, "'t_dawnfolk' must name a non-empty anchor key"
                ):
                    validate_start_locations(registry, subraces)

    def test_a_value_that_is_not_a_start_location_is_rejected(self):
        subraces = _subraces("t_dawnfolk")
        registry = {"t_dawnfolk": ("t_dawnfolk", "t_ember_vale")}

        with self.assertRaisesRegex(
            ValueError, "'t_dawnfolk' must be a SubraceStartLocation"
        ):
            validate_start_locations(registry, subraces)


if __name__ == "__main__":
    unittest.main()
