"""Equipment adjustment prose tests (P3, tasks 3.4/4.4).

Pins the exact D4 vocabulary contract: segments joined by 「｜」 in the
fixed field-declaration order, signed integers with the U+2212 minus,
percent fields as ±N%, gauge fields as <gauge>上限 ±N, immunity via
registered display names, zero-valued numeric fields omitted, and every
number sourced verbatim from the rulebook.
"""

from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.equipment_effects import equipment_adjustment_text, worn_item_keys


class EquipmentAdjustmentTextTests(unittest.TestCase):
    def test_knight_platemail_tradeoff_is_exact(self):
        self.assertEqual(
            equipment_adjustment_text("knight_platemail"),
            "攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15",
        )

    def test_fearless_brooch_immunity_only(self):
        self.assertEqual(
            equipment_adjustment_text("fearless_brooch"),
            "免疫恐懼",
        )

    def test_purified_pendant_flat_plus_immunity(self):
        self.assertEqual(
            equipment_adjustment_text("purified_pendant"),
            "防禦 +2｜免疫中毒",
        )

    def test_plain_sword_flat(self):
        self.assertEqual(equipment_adjustment_text("plain_sword"), "攻擊 +2")

    def test_chainmail_defense_and_agility_percent(self):
        self.assertEqual(
            equipment_adjustment_text("chainmail"),
            "防禦 +5｜敏捷 −5%",
        )

    def test_non_equipment_and_unknown_items_render_empty(self):
        self.assertEqual(equipment_adjustment_text("healing_potion"), "")
        self.assertEqual(equipment_adjustment_text("no_such_key"), "")

    def test_zero_adjustment_field_is_omitted(self):
        # storage_pouch carries an explicit empty entry.
        self.assertEqual(equipment_adjustment_text("storage_pouch"), "")

    @covers_requirement(
        "equipment-effects::equipment-adjustments-render-as-deterministic-prose"
    )
    def test_sister_vestments_render_only_d4_vocabulary(self):
        # pleasure_gain / exposure_bias belong to P4 presentation and are
        # deliberately absent from the P3 prose vocabulary.
        self.assertEqual(equipment_adjustment_text("sister_vestments"), "治療 +10%")


class WornItemKeysTests(unittest.TestCase):
    def _entity(self, equipment):
        from types import SimpleNamespace

        return SimpleNamespace(db=SimpleNamespace(equipment=equipment))

    def test_singletons_and_accessories_collect(self):
        entity = self._entity(
            {
                "weapon_main": "plain_sword",
                "weapon_off": None,
                "armor": "chainmail",
                "accessories": ["purified_pendant"],
            }
        )
        self.assertEqual(
            worn_item_keys(entity),
            {"plain_sword", "chainmail", "purified_pendant"},
        )

    def test_malformed_collects_nothing(self):
        entity = self._entity({"weapon_main": 1})
        self.assertEqual(worn_item_keys(entity), frozenset())

    def test_none_collects_nothing(self):
        from types import SimpleNamespace

        entity = SimpleNamespace(db=SimpleNamespace(equipment=None))
        self.assertEqual(worn_item_keys(entity), frozenset())


class EquipmentLookCardTests(EvenniaTestCase):
    """The shared 看 / explore.look appearance seam renders the item card."""

    def test_registry_mirror_object_renders_summary_and_prose(self):
        entity = create_object(PlayerCharacter, key="mirror target")
        entity.race = "human"
        entity.apply_race_baseline()
        from world.rules.equipment import materialize_registry_object

        mirror = materialize_registry_object(entity, "knight_platemail")
        card = entity.at_look(mirror)
        self.assertIn("騎士全套板甲", card)
        self.assertIn("攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15", card)

    def test_non_registry_object_keeps_the_plain_desc(self):
        entity = create_object(PlayerCharacter, key="plain target")
        entity.race = "human"
        entity.apply_race_baseline()
        plain = create_object("typeclasses.objects.Object", key="普通木箱")
        card = entity.at_look(plain)
        self.assertIn("普通木箱", card)


if __name__ == "__main__":
    unittest.main()