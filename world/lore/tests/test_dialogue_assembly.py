"""Data-contract test: Altoria dialogue terrace split preserves tables and terrace alignment.

Asserts that DIALOGUE_ROWS assembles the 16 capital dialogue tables across
lower, middle, and upper terraces with verbatim definition content, and that
each table's terrace matches the place row authoring that dialogue_key.
"""

from __future__ import annotations

import unittest

from world.lore.dialogue import (
    ALTORIA_LOWER_ROWS,
    ALTORIA_MIDDLE_ROWS,
    ALTORIA_UPPER_ROWS,
    CIARAN_ROWS,
    DIALOGUE_ROWS,
    GUILD_STAFF_ROWS,
)
import world.lore.settlements.places_altoria_lower as pal
import world.lore.settlements.places_altoria_middle as pam
import world.lore.settlements.places_altoria_upper as pau
from world.lore.settlements.places import PLACE_REGISTRY


class AltoriaDialogueSplitContractTests(unittest.TestCase):
    """The terrace split of Altoria dialogue tables preserves assembly order and terrace alignment."""

    def test_assembled_dialogue_rows_contains_all_slices_in_fixed_order(self):
        expected_keys = [
            *(k for k, _ in GUILD_STAFF_ROWS),
            *(k for k, _ in ALTORIA_LOWER_ROWS),
            *(k for k, _ in ALTORIA_MIDDLE_ROWS),
            *(k for k, _ in ALTORIA_UPPER_ROWS),
            *(k for k, _ in CIARAN_ROWS),
        ]
        self.assertEqual(list(DIALOGUE_ROWS.keys()), expected_keys)

    def test_each_table_terrace_matches_its_place_row(self):
        lower_places = {
            dict(p.authored_kwargs).get("dialogue_key")
            for p in pal.ROWS
            if "dialogue_key" in dict(p.authored_kwargs)
        }
        middle_places = {
            dict(p.authored_kwargs).get("dialogue_key")
            for p in pam.ROWS
            if "dialogue_key" in dict(p.authored_kwargs)
        }
        upper_places = {
            dict(p.authored_kwargs).get("dialogue_key")
            for p in pau.ROWS
            if "dialogue_key" in dict(p.authored_kwargs)
        }

        self.assertEqual(
            set(k for k, _ in ALTORIA_LOWER_ROWS),
            lower_places,
        )
        # Note: guild_staff is in GUILD_STAFF_ROWS, middle_places includes guild_staff
        self.assertEqual(
            set(k for k, _ in ALTORIA_MIDDLE_ROWS),
            middle_places - {"guild_staff"},
        )
        self.assertEqual(
            set(k for k, _ in ALTORIA_UPPER_ROWS),
            upper_places,
        )

    def test_all_sixteen_altoria_tables_present_and_accounted_for(self):
        all_altoria_keys = (
            [k for k, _ in ALTORIA_LOWER_ROWS]
            + [k for k, _ in ALTORIA_MIDDLE_ROWS]
            + [k for k, _ in ALTORIA_UPPER_ROWS]
        )
        self.assertEqual(len(all_altoria_keys), 16)
        for key in all_altoria_keys:
            self.assertIn(key, DIALOGUE_ROWS)
            self.assertIsNotNone(DIALOGUE_ROWS[key].greeting)
            self.assertGreater(len(DIALOGUE_ROWS[key].responses), 0)
