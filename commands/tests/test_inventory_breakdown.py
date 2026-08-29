"""Inventory breakdown-header integration tests (expose-stat-breakdown-read-model 3.5).

The v5 header prints the SAME breakdown rows the character panel serializes,
from the same single assembly, followed by the unchanged item lines with
their P3 adjustment prose.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaCommandTest

from commands.economy import CmdInventory
from world.lore.items import ITEM_REGISTRY
from world.rules.equipment import toggle_equipment
from world.rules.status_query import build_character_read_model
from world.rules.status_text import breakdown_text
from world.rules.tests.combat_fixtures import BattlefieldIsolation


class InventoryBreakdownHeaderTests(BattlefieldIsolation, EvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.wallet = 0
        self.char1.db.inventory = ["knight_platemail"]
        result = toggle_equipment(self.char1, "knight_platemail")
        assert result.outcome == "success", result.reason

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_header_equals_the_panel_assembly_and_items_keep_prose(self):
        plate = ITEM_REGISTRY["knight_platemail"].display_name_zh
        output = self.call(CmdInventory(), "")
        expected_header = breakdown_text(build_character_read_model(self.char1))
        self.assertIn(expected_header, output)
        # The breakdown-bearing equipment line keeps its P3 summary.
        self.assertIn(
            "  knight_platemail ×1——攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15",
            output,
        )
        # The header decomposes the plate's gauge cap and defense flat.
        self.assertIn(f"生命：115／115（{plate} ＋15）", expected_header)
        self.assertIn(f"{plate} ＋8）", expected_header)
