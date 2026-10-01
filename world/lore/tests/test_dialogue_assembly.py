"""Data-contract test: Altoria dialogue terrace split preserves tables and terrace alignment

Asserts that DIALOGUE_ROWS assembles the 16 capital dialogue tables across
lower, middle, and upper terraces with verbatim definition content, and that
each table's terrace matches the place row authoring that dialogue_key.
"""

from __future__ import annotations

import hashlib
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

# Pre-split verbatim content digests captured from git HEAD pre-split altoria.py
# (SHA-256 over greeting + each (keyword, response) encoded in UTF-8).
PRE_SPLIT_DIGESTS: dict[str, str] = {
    "altoria_general_store": "12e8dab12b21c083",
    "altoria_forge": "d34e8f4f24baf4d7",
    "altoria_eatery": "33fbc36df41b5833",
    "altoria_tailor": "20aea742041622e2",
    "altoria_jeweller": "bc87a7864500c1b3",
    "altoria_alchemist": "3f92eac40743c4a8",
    "altoria_temple": "a3b39988b57aa2c5",
    "altoria_sanctum": "5f164183d7e44635",
    "altoria_tavern": "c6aec9c77b7861ad",
    "altoria_lodging": "d528835a01aed31a",
    "altoria_bathhouse": "6f9e74ca17d15029",
    "altoria_guardhouse": "4c5018dde8f2e0d5",
    "altoria_noble_watch": "880307a2812924d7",
    "altoria_drill_yard": "60c13b83e5eb18b5",
    "altoria_academy": "b682b500d10b0acf",
    "altoria_merchant_hall": "cee45638ad184b18",
}


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
        # Note: guild staff table is in GUILD_STAFF_ROWS
        guild_keys = {k for k, _ in GUILD_STAFF_ROWS}
        self.assertEqual(
            set(k for k, _ in ALTORIA_MIDDLE_ROWS),
            middle_places - guild_keys,
        )
        self.assertEqual(
            set(k for k, _ in ALTORIA_UPPER_ROWS),
            upper_places,
        )

    def test_all_sixteen_altoria_tables_match_presplit_content_digests(self):
        all_altoria_keys = (
            [k for k, _ in ALTORIA_LOWER_ROWS]
            + [k for k, _ in ALTORIA_MIDDLE_ROWS]
            + [k for k, _ in ALTORIA_UPPER_ROWS]
        )
        self.assertEqual(len(all_altoria_keys), 16)
        for key in all_altoria_keys:
            self.assertIn(key, DIALOGUE_ROWS)
            definition = DIALOGUE_ROWS[key]
            h = hashlib.sha256()
            h.update(definition.greeting.encode("utf-8"))
            for r in definition.responses:
                h.update(r.keyword.encode("utf-8"))
                h.update(r.response.encode("utf-8"))
            digest = h.hexdigest()[:16]
            self.assertEqual(
                digest,
                PRE_SPLIT_DIGESTS[key],
                f"dialogue table {key} content drifted from pre-split baseline",
            )
            self.assertEqual(len(definition.responses), 4)
