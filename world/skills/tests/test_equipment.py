"""Integration tests for equipment slots and the item-specific toggle."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import (
    EquipmentModifierKey,
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
from world.tests.synthetic_data import synthetic_registries

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
        modifier_key=EquipmentModifierKey.PLAIN_SWORD,
    )


def _items(*definitions: ItemDefinition):
    """Scope the item catalog to the synthetic kit plus these fixtures.

    The fixture rows are invented t_* keys; the shipped catalog never enters
    the scope, so no fixture shadows a shipped item.
    """
    return synthetic_registries(
        "items", extra={"items": {d.key: d for d in definitions}}
    )


_RING_KEYS = tuple(f"t_ring_{index}" for index in range(ACCESSORY_MAX_SLOTS + 1))


class EquipmentHandlerTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="equipment tester")
        entity.db.inventory = []
        return entity

    def _hold(self, entity, *keys: str) -> None:
        entity.db.inventory = list(keys)

    @covers_requirement("equipment-inventory::equipmentslot-defines-four-slots-sized-to-the-sample-cards-own-equipment-shapes")
    @_items(
        _fixture_definition("t_left_blade", EquipmentSlot.WEAPON_MAIN),
        _fixture_definition("t_right_blade", EquipmentSlot.WEAPON_OFF),
    )
    def test_enum_and_dual_wield_slots_are_independent(self):
        self.assertEqual(
            set(EquipmentSlot.__members__),
            {"WEAPON_MAIN", "WEAPON_OFF", "ARMOR", "ACCESSORY"},
        )
        entity = self._entity()
        self._hold(entity, "t_left_blade", "t_right_blade")
        toggle_equipment(entity, "t_left_blade")
        toggle_equipment(entity, "t_right_blade")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "t_left_blade",
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_OFF),
            "t_right_blade",
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
            "weapon_main": "t_iron_fang",
            "weapon_off": None,
            "armor": "t_bark_cloak",
            "accessories": ["t_moon_ring"],
        }
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "t_iron_fang",
        )
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            ["t_moon_ring"],
        )

    @covers_requirement("equipment-inventory::accessory-is-a-bounded-multi-item-slot")
    @_items(
        *(
            _fixture_definition(key, EquipmentSlot.ACCESSORY)
            for key in _RING_KEYS
        )
    )
    def test_five_distinct_accessories_equip_in_deterministic_order(self):
        entity = self._entity()
        self._hold(entity, *_RING_KEYS)
        self.assertEqual(ACCESSORY_MAX_SLOTS, 5)
        for key in _RING_KEYS[:ACCESSORY_MAX_SLOTS]:
            result = toggle_equipment(entity, key)
            self.assertEqual(result.outcome, "success")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            list(_RING_KEYS[:ACCESSORY_MAX_SLOTS]),
        )
        overflow = toggle_equipment(entity, _RING_KEYS[ACCESSORY_MAX_SLOTS])
        self.assertEqual(overflow.outcome, "rejected")
        self.assertEqual(overflow.reason.value, "accessory_slots_full")
        self.assertEqual(
            entity.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            list(_RING_KEYS[:ACCESSORY_MAX_SLOTS]),
        )

    @_items(
        _fixture_definition("t_iron_fang", EquipmentSlot.WEAPON_MAIN),
        _fixture_definition("t_moon_ring", EquipmentSlot.ACCESSORY),
    )
    def test_equipment_survives_database_serialization_round_trip(self):
        entity = self._entity()
        self._hold(entity, "t_iron_fang", "t_moon_ring")
        toggle_equipment(entity, "t_iron_fang")
        toggle_equipment(entity, "t_moon_ring")

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN),
            "t_iron_fang",
        )
        self.assertEqual(
            reloaded.equipment.slot_contents(EquipmentSlot.ACCESSORY),
            ["t_moon_ring"],
        )

    @_items(
        _fixture_definition("t_left_blade", EquipmentSlot.WEAPON_MAIN),
        _fixture_definition("t_right_blade", EquipmentSlot.WEAPON_OFF),
    )
    def test_is_dual_wielding_requires_both_weapon_slots(self):
        entity = self._entity()
        self._hold(entity, "t_left_blade", "t_right_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "t_left_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "t_right_blade")
        self.assertTrue(entity.equipment.is_dual_wielding)
        toggle_equipment(entity, "t_right_blade")
        self.assertFalse(entity.equipment.is_dual_wielding)

    def test_storage_fact_fails_closed_on_malformed_equipment(self):
        entity = self._entity()
        for malformed in (None, "corrupt", ["t_left_blade", "t_right_blade"]):
            with self.subTest(malformed=malformed):
                entity.db.equipment = malformed
                self.assertFalse(dual_wielding_from_storage(entity))
                self.assertFalse(entity.equipment.is_dual_wielding)
