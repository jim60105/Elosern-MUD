"""Focused tests for the ownership-aware, item-specific equipment toggle.

Covers shared side-effect-free preflight, singleton slot replacement and
clearing, exact accessory removal, the five-slot cap without automatic
replacement, malformed-storage fail-closed behavior, atomic replacement
rollback, and the free-action guarantee.
"""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.rules.clock import WorldClock
from world.rules.equipment import (
    EquipmentToggleReason,
    preflight_equipment_toggle,
    toggle_equipment,
)
from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot, list_items

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
        presentation=_PRESENTATION,
        equipment_slot=slot,
    )


class _FakeAtomic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise RuntimeError("simulated db commit failure")
        return False


class _ToggleTestCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        registry_snapshot = dict(ITEM_REGISTRY)

        def restore():
            ITEM_REGISTRY.clear()
            ITEM_REGISTRY.update(registry_snapshot)

        self.addCleanup(restore)
        self.entity = self.char1
        self.entity.db.equipment = None
        self.entity.db.inventory = []

    def register(self, *keys_and_slots: tuple[str, EquipmentSlot]) -> None:
        for key, slot in keys_and_slots:
            ITEM_REGISTRY[key] = _fixture_definition(key, slot)

    def hold(self, *keys: str) -> None:
        self.entity.db.inventory = list(keys)

    def state(self) -> dict:
        return {
            "equipment": deepcopy(self.entity.db.equipment),
            "inventory": deepcopy(self.entity.db.inventory),
        }


class TogglePreflightTests(_ToggleTestCase):
    def test_registry_slot_selects_without_client_input(self):
        self.register(("alpha_blade", EquipmentSlot.WEAPON_MAIN))
        self.hold("alpha_blade")
        preflight = preflight_equipment_toggle(self.entity, "alpha_blade")
        self.assertTrue(preflight.allowed)
        self.assertIs(preflight.plan.slot, EquipmentSlot.WEAPON_MAIN)
        self.assertEqual(preflight.plan.after["weapon_main"], "alpha_blade")

    def test_unknown_inspect_only_and_usable_items_reject(self):
        self.hold("meal", "healing_potion", "mystery_key")
        for key, reason in (
            ("mystery_key", EquipmentToggleReason.UNKNOWN_ITEM),
            ("meal", EquipmentToggleReason.NOT_EQUIPMENT),
            ("healing_potion", EquipmentToggleReason.NOT_EQUIPMENT),
        ):
            with self.subTest(key=key):
                preflight = preflight_equipment_toggle(self.entity, key)
                self.assertFalse(preflight.allowed)
                self.assertIs(preflight.reason, reason)

    @covers_requirement(
        "equipment-inventory::equipment-toggle-revalidates-ownership-and-registry-slot"
    )
    def test_unheld_equipment_rejects_without_mutation(self):
        self.register(("alpha_blade", EquipmentSlot.WEAPON_MAIN))
        self.hold("plain_sword")
        before = self.state()
        result = toggle_equipment(self.entity, "alpha_blade")
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, EquipmentToggleReason.ITEM_NOT_HELD)
        self.assertEqual(self.state(), before)

    @covers_requirement(
        "equipment-inventory::equipment-toggle-revalidates-ownership-and-registry-slot"
    )
    def test_presenter_preflight_writes_nothing_at_the_cap(self):
        self.register(
            *(
                (f"ring_{index}", EquipmentSlot.ACCESSORY)
                for index in range(ACCESSORY_MAX_SLOTS + 1)
            )
        )
        self.hold(*(f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS + 1)))
        for index in range(ACCESSORY_MAX_SLOTS):
            toggle_equipment(self.entity, f"ring_{index}")
        before = self.state()
        preflight = preflight_equipment_toggle(self.entity, f"ring_{ACCESSORY_MAX_SLOTS}")
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, EquipmentToggleReason.ACCESSORY_SLOTS_FULL)
        self.assertEqual(self.state(), before)


class SingletonToggleTests(_ToggleTestCase):
    @covers_requirement(
        "equipment-inventory::singleton-equipment-toggles-and-replaces-atomically"
    )
    def test_each_singleton_slot_equips_and_clears(self):
        self.register(
            ("main_a", EquipmentSlot.WEAPON_MAIN),
            ("off_a", EquipmentSlot.WEAPON_OFF),
            ("armor_a", EquipmentSlot.ARMOR),
        )
        self.hold("main_a", "off_a", "armor_a")
        cases = {
            "main_a": "weapon_main",
            "off_a": "weapon_off",
            "armor_a": "armor",
        }
        for key, storage_key in cases.items():
            with self.subTest(key=key):
                equipped = toggle_equipment(self.entity, key)
                self.assertEqual(equipped.outcome, "success")
                self.assertEqual(self.entity.db.equipment[storage_key], key)
                self.assertIn(key, list_items(self.entity))
                cleared = toggle_equipment(self.entity, key)
                self.assertEqual(cleared.outcome, "success")
                self.assertIsNone(self.entity.db.equipment[storage_key])
                self.assertIn(key, list_items(self.entity))

    @covers_requirement(
        "equipment-inventory::singleton-equipment-toggles-and-replaces-atomically"
    )
    def test_new_singleton_replaces_the_occupant_which_stays_held(self):
        self.register(
            ("main_a", EquipmentSlot.WEAPON_MAIN),
            ("main_b", EquipmentSlot.WEAPON_MAIN),
        )
        self.hold("main_a", "main_b")
        toggle_equipment(self.entity, "main_a")
        result = toggle_equipment(self.entity, "main_b")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.replaced_key, "main_a")
        self.assertEqual(self.entity.db.equipment["weapon_main"], "main_b")
        self.assertIn("main_a", list_items(self.entity))

    @covers_requirement(
        "equipment-inventory::singleton-equipment-toggles-and-replaces-atomically"
    )
    def test_replacement_write_failure_restores_the_mapping(self):
        self.register(
            ("main_a", EquipmentSlot.WEAPON_MAIN),
            ("main_b", EquipmentSlot.WEAPON_MAIN),
        )
        self.hold("main_a", "main_b")
        toggle_equipment(self.entity, "main_a")
        before = self.state()
        with patch(
            "world.rules.equipment.transaction.atomic",
            return_value=_FakeAtomic(),
        ):
            with self.assertRaises(RuntimeError):
                toggle_equipment(self.entity, "main_b")
        self.assertEqual(self.entity.db.equipment, before["equipment"])
        self.assertEqual(self.entity.db.inventory, before["inventory"])


class AccessoryToggleTests(_ToggleTestCase):
    def setUp(self):
        super().setUp()
        self.register(
            *(
                (f"ring_{index}", EquipmentSlot.ACCESSORY)
                for index in range(ACCESSORY_MAX_SLOTS + 1)
            )
        )
        self.hold(*(f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS + 1)))

    @covers_requirement(
        "equipment-inventory::accessory-toggle-removes-only-the-selected-item"
    )
    def test_named_removal_preserves_later_items(self):
        for index in (0, 1, 2):
            toggle_equipment(self.entity, f"ring_{index}")
        self.assertEqual(
            self.entity.db.equipment["accessories"],
            ["ring_0", "ring_1", "ring_2"],
        )
        result = toggle_equipment(self.entity, "ring_1")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.entity.db.equipment["accessories"], ["ring_0", "ring_2"]
        )

    @covers_requirement(
        "equipment-inventory::accessory-toggle-removes-only-the-selected-item"
    )
    def test_sixth_accessory_rejects_without_replacement(self):
        for index in range(ACCESSORY_MAX_SLOTS):
            toggle_equipment(self.entity, f"ring_{index}")
        before = self.state()
        result = toggle_equipment(self.entity, f"ring_{ACCESSORY_MAX_SLOTS}")
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, EquipmentToggleReason.ACCESSORY_SLOTS_FULL)
        self.assertEqual(self.state(), before)
        self.assertEqual(
            self.entity.db.equipment["accessories"],
            [f"ring_{index}" for index in range(ACCESSORY_MAX_SLOTS)],
        )

    @covers_requirement(
        "equipment-inventory::accessory-toggle-removes-only-the-selected-item"
    )
    def test_aggregated_tile_reactivation_removes_not_duplicates(self):
        toggle_equipment(self.entity, "ring_0")
        result = toggle_equipment(self.entity, "ring_0")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.entity.db.equipment["accessories"], [])

    def test_stored_duplicate_occurrences_fail_closed(self):
        self.entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": ["ring_0", "ring_0"],
        }
        result = toggle_equipment(self.entity, "ring_1")
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, EquipmentToggleReason.MALFORMED_STORAGE)

    def test_malformed_storage_shapes_fail_closed(self):
        cases = {
            "extra-slot": {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [],
                "mount": "saddle",
            },
            "non-string-accessory": {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [7],
            },
            "not-a-mapping": "corrupt",
        }
        for name, storage in cases.items():
            with self.subTest(case=name):
                self.entity.db.equipment = storage
                result = toggle_equipment(self.entity, "ring_0")
                self.assertEqual(result.outcome, "rejected")
                self.assertIs(
                    result.reason, EquipmentToggleReason.MALFORMED_STORAGE
                )


class ToggleFreeActionTests(_ToggleTestCase):
    @covers_requirement(
        "equipment-inventory::equipment-toggling-consumes-neither-a-combat-turn-nor-world-time"
    )
    def test_toggle_touches_no_clock_and_only_equipment_state(self):
        self.register(("main_a", EquipmentSlot.WEAPON_MAIN))
        self.hold("main_a")
        clock = WorldClock()
        traits_before = deepcopy(
            self.entity.attributes.get("traits", category="traits")
        )
        result = toggle_equipment(self.entity, "main_a")
        self.assertEqual(result.outcome, "success")
        self.assertEqual(clock.tick, 0)
        self.assertEqual(self.entity.db.equipment["weapon_main"], "main_a")
        self.assertEqual(
            self.entity.attributes.get("traits", category="traits"),
            traits_before,
        )


class CrossSlotNormalizationTests(_ToggleTestCase):
    """Registry slot agreement and one occurrence per key across slots."""

    def setUp(self):
        super().setUp()
        self.register(
            ("twin_blade", EquipmentSlot.WEAPON_MAIN),
            ("plate_mail", EquipmentSlot.ARMOR),
            ("loop_ring", EquipmentSlot.ACCESSORY),
        )
        self.hold("twin_blade", "plate_mail", "loop_ring")

    def _rejects_malformed(self, storage: dict, key: str) -> None:
        self.entity.db.equipment = storage
        before = self.state()
        result = toggle_equipment(self.entity, key)
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, EquipmentToggleReason.MALFORMED_STORAGE)
        self.assertEqual(self.state(), before)

    def test_same_key_in_two_singleton_slots_fails_closed(self):
        self._rejects_malformed(
            {
                "weapon_main": "twin_blade",
                "weapon_off": "twin_blade",
                "armor": None,
                "accessories": [],
            },
            "twin_blade",
        )

    def test_singleton_and_accessory_duplicate_fails_closed(self):
        self._rejects_malformed(
            {
                "weapon_main": "twin_blade",
                "weapon_off": None,
                "armor": None,
                "accessories": ["twin_blade"],
            },
            "loop_ring",
        )

    def test_slot_mismatch_and_unknown_keys_fail_closed(self):
        cases = {
            "main-hand-item-in-off-hand": {
                "weapon_main": None,
                "weapon_off": "twin_blade",
                "armor": None,
                "accessories": [],
            },
            "accessory-in-singleton-slot": {
                "weapon_main": None,
                "weapon_off": None,
                "armor": "loop_ring",
                "accessories": [],
            },
            "unknown-key-in-slot": {
                "weapon_main": "ghost_item",
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
            "non-equipment-in-accessories": {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": ["plate_mail"],
            },
        }
        for name, storage in cases.items():
            with self.subTest(case=name):
                self._rejects_malformed(storage, "loop_ring")
