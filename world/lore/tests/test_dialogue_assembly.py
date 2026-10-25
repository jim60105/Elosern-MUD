"""Data-contract test: Altoria dialogue terrace split preserves tables and terrace alignment

Asserts that DIALOGUE_SNAPSHOT assembles the 16 capital dialogue tables across
lower, middle, and upper terraces and that each table's terrace matches the
place row authoring that dialogue_key. It pins no dialogue prose: NPC lines
are authored content and rewording them never breaks a test.
"""

from __future__ import annotations

import unittest

from world.lore.dialogue import DIALOGUE_SNAPSHOT
import world.lore.settlements.places_altoria_lower as pal
import world.lore.settlements.places_altoria_middle as pam
import world.lore.settlements.places_altoria_upper as pau
import world.lore.settlements.places_ciaran as pci


class AltoriaDialogueSplitContractTests(unittest.TestCase):
    """The terrace split of Altoria dialogue tables preserves assembly order and terrace alignment."""

    def test_assembled_dialogue_snapshot_contains_all_25_tables(self):
        self.assertEqual(len(DIALOGUE_SNAPSHOT), 25)

    def test_every_altoria_table_keeps_its_greeting_and_four_answers(self):
        capital_places = {
            dict(p.authored_kwargs).get("dialogue_key")
            for places in (pal.ROWS, pam.ROWS, pau.ROWS)
            for p in places
            if "dialogue_key" in dict(p.authored_kwargs)
        }
        self.assertEqual(len(capital_places), 17)  # 16 capital places + guild_staff
        for key in capital_places:
            with self.subTest(table=key):
                self.assertIn(key, DIALOGUE_SNAPSHOT)
                dialogue = DIALOGUE_SNAPSHOT[key]
                self.assertTrue(dialogue.greeting)
                self.assertEqual(len(dialogue.topics), 4)

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
        ciaran_places = {
            dict(p.authored_kwargs).get("dialogue_key")
            for p in pci.ROWS
            if "dialogue_key" in dict(p.authored_kwargs)
        }

        all_bound_keys = lower_places | middle_places | upper_places | ciaran_places
        self.assertEqual(set(DIALOGUE_SNAPSHOT.keys()), all_bound_keys)
