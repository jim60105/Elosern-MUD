"""Integration tests for equipment slots."""

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.equipment import equip_item, unequip_item
from world.skills.equipment import (
    ACCESSORY_MAX_SLOTS,
    EquipmentSlot,
)


class EquipmentHandlerTests(EvenniaTest):
    def _entity(self):
        return create_object(PlayerCharacter, key="equipment tester")

    def test_enum_and_dual_wield_slots_are_independent(self):
        self.assertEqual(
            set(EquipmentSlot.__members__),
            {"WEAPON_MAIN", "WEAPON_OFF", "ARMOR", "ACCESSORY"},
        )
        entity = self._entity()
        equip_item(entity, EquipmentSlot.WEAPON_MAIN, "left_blade")
        equip_item(entity, EquipmentSlot.WEAPON_OFF, "right_blade")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "left_blade",
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_OFF),
            "right_blade",
        )

    def test_handler_tolerates_empty_storage_and_is_read_only(self):
        entity = self._entity()
        for empty in (None, {}):
            entity.db.equipment = empty
            self.assertIsNone(
                entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN)
            )
            self.assertEqual(
                entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
                [],
            )
        with self.assertRaises(AttributeError):
            entity.equipment = {}

    def test_direct_private_storage_is_reflected(self):
        entity = self._entity()
        entity.db.equipment = {
            "weapon_main": "light_sword",
            "weapon_off": None,
            "armor": "elf_traditional_garb",
            "accessories": ["crescent_earring"],
        }
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "light_sword",
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            ["crescent_earring"],
        )

    def test_accessories_are_capped_and_unequip_returns_last(self):
        entity = self._entity()
        for index in range(ACCESSORY_MAX_SLOTS):
            equip_item(entity, EquipmentSlot.ACCESSORY, f"ring_{index}")
        self.assertEqual(
            len(entity.equipment.slot_contents(EquipmentSlot.ACCESSORY)),
            ACCESSORY_MAX_SLOTS,
        )
        with self.assertRaises(ValueError):
            equip_item(entity, EquipmentSlot.ACCESSORY, "one_too_many")
        self.assertEqual(
            unequip_item(entity, EquipmentSlot.ACCESSORY),
            f"ring_{ACCESSORY_MAX_SLOTS - 1}",
        )

    def test_equipment_survives_database_serialization_round_trip(self):
        entity = self._entity()
        equip_item(entity, EquipmentSlot.WEAPON_MAIN, "light_sword")
        equip_item(entity, EquipmentSlot.ACCESSORY, "crescent_earring")

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "light_sword",
        )
        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            ["crescent_earring"],
        )
