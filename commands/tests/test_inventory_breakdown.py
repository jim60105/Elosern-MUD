"""Inventory breakdown-header integration tests (expose-stat-breakdown-read-model 3.5).

The v5 header prints the SAME breakdown rows the character panel serializes,
from the same single assembly, followed by the unchanged item lines with
their P3 adjustment prose. Data-independent
(migrate-commands-tests-off-real-data): the worn gear is a kit slotted item
bound to a runtime-probed rulebook row whose rule is patched with locally
authored adjustment values, so the header decomposition is asserted against
numbers authored in this file, never against shipped gear.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.economy import CmdInventory
from world.lore.items import EquipmentSlot
from world.rules import equipment_effects
from world.rules.equipment import toggle_equipment
from world.rules.status_query import build_character_read_model
from world.rules.status_text import breakdown_text
from world.rules.tests._equipment_rulebook_probes import unique_rule
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import make_item, synthetic_registries

# One borrowed rulebook row (fail-fast unique probe) supplies the modifier
# key the synthetic gear binds to; its rule is replaced with locally authored
# values for the duration of each test.
_PROBE_MODIFIER, _PROBE_RULE = unique_rule(
    "attached_buffs", lambda rule: bool(rule.attached_buffs)
)

# Kit-factory gear bound to the PROBED modifier (the shared kit row binds the
# enum's first member, which is a different rulebook row).
_GEAR = make_item(
    "t_bulwark_vest",
    display_name_zh="岩背合成背心",
    price_table_key="t_ironbite_steel",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_PROBE_MODIFIER,
)
_GEAR_KEY = _GEAR.key
_GEAR_DISPLAY = _GEAR.display_name_zh

# Authored fixture numbers (never shipped values, never derived from the
# production rulebook).
_HP_CAP = 12
_DEFENSE_FLAT = 7

_GEAR_RULE = replace(
    _PROBE_RULE,
    adjustments={"defense": _DEFENSE_FLAT},
    gauge_caps={"hp": _HP_CAP},
    immune=(),
    attached_buffs=(),
)

_SCOPE_LOGICALS = ("races", "static_tiers", "subraces", "items", "prices", "elements")
_SCOPE_EXTRA = {"items": {_GEAR_KEY: _GEAR}}


class InventoryBreakdownHeaderTests(BattlefieldIsolation, EvenniaCommandTest):
    def setUp(self):
        # The gear, race baseline, and read-model reads all resolve through
        # patched catalogs, so the scope opens before super().setUp().
        scope = synthetic_registries(*_SCOPE_LOGICALS, extra=_SCOPE_EXTRA)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        rule_patch = patch.dict(
            equipment_effects.EQUIPMENT_EFFECT_RULES, {_PROBE_MODIFIER: _GEAR_RULE}
        )
        rule_patch.start()
        self.addCleanup(rule_patch.stop)
        super().setUp()
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.db.wallet = 0
        self.char1.db.inventory = [_GEAR_KEY]
        result = toggle_equipment(self.char1, _GEAR_KEY)
        assert result.outcome == "success", result.reason

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_header_equals_the_panel_assembly_and_items_keep_prose(self):
        output = self.call(CmdInventory(), "")
        expected_header = breakdown_text(build_character_read_model(self.char1))
        self.assertIn(expected_header, output)
        # The breakdown-bearing equipment line keeps its P3 summary.
        self.assertIn(
            f"  {_GEAR_KEY} ×1——防禦 +{_DEFENSE_FLAT}｜生命上限 +{_HP_CAP}",
            output,
        )
        # The header decomposes the gear's gauge cap and defense flat, each
        # attributed to the worn item's display name.
        hp_value = self.char1.traits.hp.value
        self.assertIn(
            f"生命：{hp_value}／{hp_value}（{_GEAR_DISPLAY} ＋{_HP_CAP}）",
            expected_header,
        )
        self.assertIn(f"{_GEAR_DISPLAY} ＋{_DEFENSE_FLAT}）", expected_header)
