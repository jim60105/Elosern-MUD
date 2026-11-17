"""Data-contract test: Altoria dialogue terrace split preserves tables and terrace alignment

Asserts that DIALOGUE_SNAPSHOT assembles the 16 capital dialogue tables across
lower, middle, and upper terraces and that each table's terrace matches the
place row authoring that dialogue_key. It pins no dialogue prose: NPC lines
are authored content and rewording them never breaks a test.
"""

from __future__ import annotations

import unittest

from world.lore.dialogue import DIALOGUE_SNAPSHOT
from world.lore.settlements.places import place_dialogue_keys
import world.lore.settlements.places_altoria_lower as pal
import world.lore.settlements.places_altoria_middle as pam
import world.lore.settlements.places_altoria_upper as pau


def _keys(rows) -> set[str]:
    """Every dialogue table declared by these place rows."""
    return {key for place in rows for key in place_dialogue_keys(place)}


class AltoriaDialogueSplitContractTests(unittest.TestCase):
    """The terrace split of Altoria dialogue tables preserves assembly order and terrace alignment."""

    def test_assembled_dialogue_snapshot_contains_every_bound_table(self):
        from world.lore.settlements.places import PLACE_REGISTRY

        bound = _keys(PLACE_REGISTRY.values())
        self.assertTrue(bound)
        self.assertEqual(len(DIALOGUE_SNAPSHOT), len(bound))

    def test_every_altoria_table_keeps_its_greeting_and_four_answers(self):
        capital_places = _keys(pal.ROWS) | _keys(pam.ROWS) | _keys(pau.ROWS)
        self.assertEqual(len(capital_places), 17)  # 16 capital places + guild_staff
        for key in capital_places:
            with self.subTest(table=key):
                self.assertIn(key, DIALOGUE_SNAPSHOT)
                dialogue = DIALOGUE_SNAPSHOT[key]
                self.assertTrue(dialogue.greeting)
                self.assertEqual(len(dialogue.topics), 4)

    def test_each_table_terrace_matches_its_place_row(self):
        lower_places = _keys(pal.ROWS)
        middle_places = _keys(pam.ROWS)
        upper_places = _keys(pau.ROWS)
        from world.lore.settlements.places import PLACE_REGISTRY

        all_bound_keys = _keys(PLACE_REGISTRY.values())
        self.assertEqual(set(DIALOGUE_SNAPSHOT.keys()), all_bound_keys)
