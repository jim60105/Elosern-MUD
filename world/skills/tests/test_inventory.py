"""Integration tests for flat item-key inventory helpers."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.imports.loader import instantiate_character
from world.imports.tests.helpers import example_record
from world.rules.equipment import add_item, remove_item
from world.skills import handler
from world.skills.equipment import (
    EquipmentSlot,
    list_items,
)
from world.tests.synthetic_data import SYNTH_ACTS, synthetic_registries

# The one initially-unlocked synthetic act: the patched catalogue's only
# row with an empty unlock gate (counter-gated rows never appear here).
_SEED_ACT_KEYS = sorted(key for key, act in SYNTH_ACTS.items() if not act.unlock)


class InventoryTests(EvenniaTestCase):
    @covers_requirement("equipment-inventory::inventory-remains-a-flat-list-of-item-key-strings-behind-one-deterministic-planning-boundary")
    def test_helpers_tolerate_none_and_remove_one_match(self):
        entity = create_object(PlayerCharacter, key="inventory tester")
        entity.db.inventory = None
        add_item(entity, "t_ember_spray")
        add_item(entity, "t_huskapple")
        add_item(entity, "t_huskapple")
        self.assertEqual(
            list_items(entity),
            ["t_ember_spray", "t_huskapple", "t_huskapple"],
        )
        remove_item(entity, "t_huskapple")
        self.assertEqual(list_items(entity), ["t_ember_spray", "t_huskapple"])

    def test_imported_inventory_and_private_handler_storage_are_reflected(self):
        record = example_record()
        record["race"] = "t_duskmari"
        record["subrace"] = "t_duskmari_evensong"
        record["skills"] = ["t_cinder_cleave"]
        record["passives"] = ["t_steady_stride"]
        record["inventory"] = ["t_ember_spray"]
        with synthetic_registries(
            "races", "subraces", "static_tiers", "skills", "items", "elements", "sexual_acts"
        ):
            from world.lore.elements import ELEMENT_REGISTRY as PATCHED_ELEMENTS

            record["affinity_elements"] = [next(iter(PATCHED_ELEMENTS))]
            entity = instantiate_character(record, PlayerCharacter)
            self.assertEqual(list_items(entity), ["t_ember_spray"])
            self.assertEqual(
                entity.skills.owned_keys(),
                [
                    *record["skills"],
                    *record["passives"],
                    *handler.INNATE_SKILL_ORDER,
                    *_SEED_ACT_KEYS,
                ],
            )
            self.assertEqual(
                entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
                [],
            )
