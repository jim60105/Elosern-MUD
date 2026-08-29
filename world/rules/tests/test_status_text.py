"""Text-client breakdown parity tests (expose-stat-breakdown-read-model 2.3/3.5).

The renderer is pinned two ways: pure formatting tests over synthetic
read-model rows, and live tests proving the self-look block equals the
character panel's single assembly while every third-party observation stays
byte-identical to the five-row displayed block.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import ITEM_REGISTRY
from world.rules.displayed_stats import display_stat_block
from world.rules.equipment import toggle_equipment
from world.rules.status_query import (
    StatBreakdownRow,
    StatLayer,
    build_character_read_model,
)
from world.rules.status_text import breakdown_text

PLATE = ITEM_REGISTRY["knight_platemail"].display_name_zh


class _Model:
    def __init__(self, rows):
        self.breakdown = rows


class FormattingTests(unittest.TestCase):
    """Pure segment formatting: signs, kinds, gauges, fractional amounts."""

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_rows_render_totals_with_named_segments(self):
        rows = [
            StatBreakdownRow("hp", 100, 120, 115, [StatLayer("equipment", PLATE, "flat", 15)]),
            StatBreakdownRow("mp", 100, 100, 100, []),
            StatBreakdownRow("atk_phys", 3, 1, 1, []),
            StatBreakdownRow(
                "agility",
                20,
                18.0,
                18.0,
                [
                    StatLayer("skill", "arte", "mult", 1.1),
                    StatLayer("condition", "poison", "pct", -10),
                    StatLayer("equipment", PLATE, "pct", -10),
                ],
            ),
            StatBreakdownRow(
                "defense",
                4,
                12.0,
                12.0,
                [
                    StatLayer("equipment", PLATE, "flat", 8),
                    StatLayer("condition", "grace", "flat", -2.5),
                ],
            ),
        ]
        lines = breakdown_text(_Model(rows)).splitlines()
        self.assertEqual(lines[0], f"生命：120／115（{PLATE} ＋15）")
        self.assertEqual(lines[1], "魔力：100／100")
        self.assertEqual(lines[2], "攻擊：1")
        self.assertEqual(
            lines[3], f"敏捷：18（arte ×1.1｜poison −10%｜{PLATE} −10%）"
        )
        self.assertEqual(lines[4], f"防禦：12（{PLATE} ＋8｜grace −2.5）")

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_integer_looking_floats_print_bare(self):
        row = StatBreakdownRow("atk_phys", 3, 5.0, 5.0, [])
        self.assertEqual(breakdown_text(_Model([row])), "攻擊：5")

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_multiplier_factors_carry_no_sign_prefix(self):
        row = StatBreakdownRow(
            "atk_phys", 3, 4, 4, [StatLayer("skill", "arte", "mult", 0.6)]
        )
        self.assertEqual(breakdown_text(_Model([row])), "攻擊：4（arte ×0.6）")

    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_gauge_rows_use_the_remainder_slash_maximum_form(self):
        row = StatBreakdownRow("sp", 100, 68, 100, [])
        self.assertEqual(breakdown_text(_Model([row])), "耐力：68／100")


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.hp.rate = 0
    player.db.equipment = None
    player.db.inventory = []
    return player


def _wear(entity, *item_keys: str):
    entity.db.inventory = list(item_keys)
    for item_key in item_keys:
        result = toggle_equipment(entity, item_key)
        assert result.outcome == "success", (item_key, result.reason)
    return entity


class SelfLookParityTests(EvenniaTestCase):
    """The self-look block equals the panel's single assembly."""

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    @covers_requirement("character-breakdown-view::text-client-renders-layers-and-compact-surfaces-stay-totals-only")
    def test_self_look_renders_the_breakdown_rows(self):
        player = _player("self-look 旅人")
        _wear(player, "knight_platemail")
        block = display_stat_block(player, looker=player)
        self.assertEqual(block, breakdown_text(build_character_read_model(player)))
        self.assertIn(f"生命：115／115（{PLATE} ＋15）", block)
        self.assertIn(f"{PLATE} ＋8）", block)  # the defense row's layer

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_third_party_look_is_byte_identical(self):
        player = _player("被看者")
        observer = _player("觀看者")
        _wear(player, "knight_platemail")
        plain = display_stat_block(player)
        self.assertEqual(display_stat_block(player, looker=observer), plain)
        self.assertEqual(display_stat_block(player, looker=None), plain)
        # Five third-party rows, never breakdown segments.
        self.assertEqual(len(plain.splitlines()), 5)
        self.assertNotIn("（", plain)

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_self_look_degrades_to_the_five_rows_when_unanswerable(self):
        player = _player("降級旅人")
        with patch(
            "world.rules.status_query.build_character_read_model",
            side_effect=RuntimeError("synthetic failure"),
        ):
            block = display_stat_block(player, looker=player)
        self.assertEqual(len(block.splitlines()), 5)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_self_look_mutates_nothing(self):
        player = _player("純檢視旅人")
        _wear(player, "knight_platemail")
        before = dict(player.attributes.get("traits", default=None, category="traits"))
        before_vars = sorted(vars(player).keys())
        display_stat_block(player, looker=player)
        self.assertEqual(
            dict(player.attributes.get("traits", default=None, category="traits")),
            before,
        )
        self.assertEqual(sorted(vars(player).keys()), before_vars)


if __name__ == "__main__":
    unittest.main()
