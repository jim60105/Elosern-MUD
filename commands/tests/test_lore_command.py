"""Command tests for the player-facing ``lore`` knowledge-codex command.

Drives ``lore`` end to end on the synthetic kit: the grouped discovered-only
listing, single-entry card rendering, the byte-identical fixed not-found line
shared by unknown categories, unknown keys, and undiscovered entries, the
unavailable diagnostic for a corrupt record, and the never-leak rule for
entries the player has not revealed. Races and regions resolve exclusively
from the patched kit catalogs (plus one file-local synthetic race), so a
shipped-data rework cannot break this suite.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from commands.lore import CmdLore
from world.rules.lore_knowledge import record_lore_reveal
from world.tests.synthetic_data import (
    SYNTH_REGIONS,
    make_race,
    synthetic_registries,
)

# File-local synthetic race: the card/never-leak fixtures carry this file's
# own invented prose, so assertions establish mechanics without echoing the
# shared kit or any shipped row.
_HIDDEN_RACE = make_race("t_hidden_folk", description="不願被圖鑑記錄的合成族。")
_HIDDEN_RACE_KEY = _HIDDEN_RACE.key
_HIDDEN_RACE_DESCRIPTION = _HIDDEN_RACE.description

_KIT_RACE_KEY = "t_duskmari"
_KIT_REGION_KEY = next(iter(SYNTH_REGIONS))


class LoreCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        scope = synthetic_registries(
            "races", "regions", extra={"races": {_HIDDEN_RACE_KEY: _HIDDEN_RACE}}
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.room = create_object(Room, key="lore room")
        self.char1.location = self.room

    def _reveal(self, category, key):
        record_lore_reveal(self.char1, category, key)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_listing_shows_only_discovered_groups(self):
        self._reveal("race", _KIT_RACE_KEY)
        self._reveal("region", _KIT_REGION_KEY)
        output = self.call(CmdLore(), "")
        self.assertIn("── 知識圖鑑 ──", output)
        self.assertIn("◆ 種族", output)
        self.assertIn(_KIT_RACE_KEY, output)
        self.assertIn("◆ 地域", output)
        self.assertIn(_KIT_REGION_KEY, output)
        # A registry race the player never revealed stays out of the listing.
        self.assertNotIn(_HIDDEN_RACE_KEY, output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_empty_codex_shows_the_empty_line(self):
        output = self.call(CmdLore(), "")
        self.assertEqual(output, "你的知識圖鑑還是空的。")

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_viewing_a_discovered_entry_renders_its_card(self):
        self._reveal("race", _HIDDEN_RACE_KEY)
        output = self.call(CmdLore(), f"race {_HIDDEN_RACE_KEY}")
        self.assertIn(f"◆ {_HIDDEN_RACE_KEY} ◆", output)
        self.assertIn(_HIDDEN_RACE_DESCRIPTION, output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_unknown_and_undiscovered_targets_share_the_same_fixed_line(self):
        self._reveal("race", _KIT_RACE_KEY)
        for args in (
            f"race {_HIDDEN_RACE_KEY}",  # known registry entry, not revealed
            "bogus elf",  # unknown category
            "race bogus",  # unknown key
            "race",  # incomplete target
        ):
            with self.subTest(args=args):
                output = self.call(CmdLore(), args)
                self.assertEqual(output, "圖鑑中查無此知識。")

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_viewing_an_unrevealed_entry_never_leaks_its_card(self):
        self._reveal("region", _KIT_REGION_KEY)
        output = self.call(CmdLore(), f"race {_HIDDEN_RACE_KEY}")
        self.assertEqual(output, "圖鑑中查無此知識。")
        self.assertNotIn(_HIDDEN_RACE_DESCRIPTION, output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_corrupt_record_shows_the_unavailable_diagnostic(self):
        self.char1.db.lore_discovered = {"not-a-set"}
        output = self.call(CmdLore(), "")
        self.assertEqual(output, "你的知識圖鑑暫時無法閱讀。")


if __name__ == "__main__":
    unittest.main()
