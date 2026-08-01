"""Integration tests for flat item-key inventory helpers."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.imports.loader import instantiate_character
from world.imports.tests.helpers import example_record
from world.rules.equipment import add_item, remove_item
from world.skills.equipment import (
    EquipmentSlot,
    list_items,
)


class InventoryTests(EvenniaTest):
    def test_helpers_tolerate_none_and_remove_one_match(self):
        entity = create_object(PlayerCharacter, key="inventory tester")
        entity.db.inventory = None
        add_item(entity, "healing_potion")
        add_item(entity, "iron_ore")
        add_item(entity, "iron_ore")
        self.assertEqual(
            list_items(entity),
            ["healing_potion", "iron_ore", "iron_ore"],
        )
        remove_item(entity, "iron_ore")
        self.assertEqual(list_items(entity), ["healing_potion", "iron_ore"])

    def test_imported_inventory_and_private_handler_storage_are_reflected(self):
        record = example_record()
        record["inventory"] = ["healing_potion"]
        entity = instantiate_character(record, PlayerCharacter)
        self.assertEqual(list_items(entity), ["healing_potion"])
        self.assertEqual(
            entity.skills.owned_keys(),
            [*record["skills"], *record["passives"], "flee", "basic_attack"],
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            [],
        )
