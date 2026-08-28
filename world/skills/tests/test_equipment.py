"""Integration tests for equipment slots and the item-specific toggle."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.rules.equipment import toggle_equipment
from world.skills.equipment import (
    ACCESSORY_MAX_SLOTS,
    EquipmentSlot,
    dual_wielding_from_storage,
)

_PRESENTATION = ItemPresentation(
    kind=ItemKind.ACCESSORY,
    icon_key=ItemIconKey.ACCESSORY,
    rarity=ItemRarity.COMMON,
    summary_zh="測試用的裝備。",
)


def _fixture_definition(key: str, slot: EquipmentSlot) -> ItemDefinition:
    return ItemDefinition(
        key=key,
        display_name_zh="測試裝備",
        price_table_key=key,
        sellable=False,
        presentation=replace(_PRESENTATION, kind=ItemKind.WEAPON if slot is EquipmentSlot.WEAPON_MAIN else _PRESENTATION.kind),
        equipment_slot=slot,
    )


class EquipmentHandlerTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="equipment tester")
        entity.db.inventory = []
        snapshot = dict(ITEM_REGISTRY)

        def restore():
            ITEM_REGISTRY.clear()
            ITEM_REGISTRY.update(snapshot)

        self.addCleanup(restore)
        return entity

    def _register(self, *definitions: ItemDefinition) -> None:
        for definition in definitions:
            ITEM_REGISTRY[definition.key] = definition

    def _hold(self, entity, *keys: str) -> None:
        entity.db.inventory = list(keys)

    @covers_requirement("equipment-inventory::equipmentslot-defines-four-slots-sized-to-the-sample-cards-own-equipment-shapes")
    def test_enum_and_dual_wield_slots_are_independent(self):
        self.assertEqual(
            set(EquipmentSlot.__members__),
            {"WEAPON_MAIN", "WEAPON_OFF", "ARMOR", "ACCESSORY"},
        )
        self._register(
            _fixture_definition("left_blade", EquipmentSlot.WEAPON_MAIN),
            _fixture_definition("right_blade", EquipmentSlot.WEAPON_OFF),
        )
        entity = self._entity()
        self._hold(entity, "left_blade", "right_blade")
        toggle_equipment(entity, "left_blade")
        toggle_equipment(entity, "right_blade")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "left_blade",
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_OFF),
            "right_blade",
        )

    @covers_requirement("equipment-inventory::equipmenthandler-is-mounted-directly-as-entity-equipment")
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

    @covers_requirement("equipment-inventory::accessory-is-a-bounded-multi-item-slot")
    def test_five_distinct_accessories_equip_in_deterministic_order(self):
        self._register(
            *(
                _fixture_definition(f"ring_{index}", EquipmentSlot.ACCESSORY)
                for index in range(ACCESSORY_MAX_SLOTS + 1)
            )
        )
        entity = self._entity()
        self._hold(
            entity,
            *(f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS + 1)),
        )
        self.assertEqual(ACCESSORY_MAX_SLOTS, 5)
        for index in range(ACCESSORY_MAX_SLOTS):
            result = toggle_equipment(entity, f"ring_{index}")
            self.assertEqual(result.outcome, "success")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            [f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS)],
        )
        overflow = toggle_equipment(entity, f"ring_{ACCESSORY_MAX_SLOTS}")
        self.assertEqual(overflow.outcome, "rejected")
        self.assertEqual(overflow.reason.value, "accessory_slots_full")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            [f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS)],
        )

    def test_equipment_survives_database_serialization_round_trip(self):
        self._register(
            _fixture_definition("light_sword", EquipmentSlot.WEAPON_MAIN),
            _fixture_definition("crescent_earring", EquipmentSlot.ACCESSORY),
        )
        entity = self._entity()
        self._hold(entity, "light_sword", "crescent_earring")
        toggle_equipment(entity, "light_sword")
        toggle_equipment(entity, "crescent_earring")

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "light_sword",
        )
        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            ["crescent_earring"],
        )

    def test_is_dual_wielding_requires_both_weapon_slots(self):
        self._register(
            _fixture_definition("left_blade", EquipmentSlot.WEAPON_MAIN),
            _fixture_definition("right_blade", EquipmentSlot.WEAPON_OFF),
        )
        entity = self._entity()
        self._hold(entity, "left_blade", "right_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "left_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "right_blade")
        self.assertTrue(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "right_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)

    def test_storage_fact_fails_closed_on_malformed_equipment(self):
        entity = self._entity()
        for malformed in (None, "corrupt", ["left_blade", "right_blade"]):
            with self.subTest(malformed=malformed):
                entity.db.equipment = malformed
                self.assertFalse(dual_wielding_from_storage(entity))
                self.assertFalse(entity.equipment.is_dual_wielding)
