"""Command-level tests for the ``lore`` knowledge-codex command.

Drives ``lore`` end to end: the grouped discovered-only listing, single-entry
card rendering, the byte-identical fixed not-found line shared by unknown
categories, unknown keys, and undiscovered entries, the unavailable
diagnostic for a corrupt record, and the never-leak rule for entries the
player has not revealed.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from commands.lore import CmdLore
from world.rules.lore_knowledge import record_lore_reveal


class LoreCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="lore room")
        self.char1.location = self.room

    def _reveal(self, category, key):
        record_lore_reveal(self.char1, category, key)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_listing_shows_only_discovered_groups(self):
        self._reveal("race", "elf")
        self._reveal("region", "eastern_plains")
        output = self.call(CmdLore(), "")
        self.assertIn("── 知識圖鑑 ──", output)
        self.assertIn("◆ 種族", output)
        self.assertIn("elf", output)
        self.assertIn("◆ 地域", output)
        self.assertIn("eastern_plains", output)
        self.assertNotIn("human", output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_empty_codex_shows_the_empty_line(self):
        output = self.call(CmdLore(), "")
        self.assertEqual(output, "你的知識圖鑑還是空的。")

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_viewing_a_discovered_entry_renders_its_card(self):
        self._reveal("race", "elf")
        output = self.call(CmdLore(), "race elf")
        self.assertIn("◆ elf ◆", output)
        self.assertIn("壽命數百年的精靈族", output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_unknown_and_undiscovered_targets_share_the_same_fixed_line(self):
        self._reveal("race", "elf")
        for args in (
            "race human",  # known registry entry, not revealed
            "bogus elf",  # unknown category
            "race bogus",  # unknown key
            "race",  # incomplete target
        ):
            with self.subTest(args=args):
                output = self.call(CmdLore(), args)
                self.assertEqual(output, "圖鑑中查無此知識。")

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_viewing_an_unrevealed_entry_never_leaks_its_card(self):
        self._reveal("region", "eastern_plains")
        output = self.call(CmdLore(), "race human")
        self.assertEqual(output, "圖鑑中查無此知識。")
        self.assertNotIn("人類", output)

    @covers_requirement("lore-knowledge::the-lore-command-shows-discovered-knowledge-only")
    def test_corrupt_record_shows_the_unavailable_diagnostic(self):
        self.char1.db.lore_discovered = {"not-a-set"}
        output = self.call(CmdLore(), "")
        self.assertEqual(output, "你的知識圖鑑暫時無法閱讀。")


if __name__ == "__main__":
    unittest.main()
