"""Slice of ``test_item_use``: ItemUsePreflightTests."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
from typing import Any
from dataclasses import replace
from unittest.mock import patch
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.lore.items import (
    ItemDefinition,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.rules.clock import EventSourceRegistration, WorldClock, _EVENT_SOURCES
from world.rules.equipment import materialize_registry_object, registry_key_for_object
from world.rules.equipment import (
    EquipmentToggleReason,
    toggle_equipment,
)
from world.rules.buffs import apply_buff, entity_active_buffs
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    StatusApplyEffect,
    StatusRemoveEffect,
)
from world.skills.equipment import list_items
from world.tests.synthetic_data import make_item
from world.rules.tests._combat_session_helpers import (
    live_item_effect_profiles,
    live_item_registry,
    open_synthetic_scope,
)
from world.rules.items import (
    ItemUseReason,
    ItemUseRequest,
    preflight_item_use,
    resolve_item_use,
    use_item,
)
from world.rules.items import ItemTouchedJournal
from world.rules import item_effects as _item_effects_module
from world.rules.tests._equipment_rulebook_probes import immune_to_key, rule_for

from ._support import (
    HEAL_AMOUNT,
    _ItemUseTestCase,
    _fixture_item,
)


class ItemUsePreflightTests(_ItemUseTestCase):
    def test_full_hp_rejects_with_hp_full(self):
        self.actor.db.inventory = ["t_moss_tonic"]
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.HP_FULL)
        self.assertIsNone(preflight.plan)
        self.assert_state_unchanged(before)

    @covers_requirement(
        "lore-item-catalog::an-item-declaring-no-mechanics-is-inert"
    )
    def test_inert_item_refuses_mechanics_and_remains_intact(self):
        inert_item = make_item(
            "t_inert_sample",
            display_name_zh="合成無機制物件",
            price_table_key="t_mossmeals",
        )
        self.register_fixture(inert_item)
        self.hurt(10)
        self.actor.db.inventory = ["t_inert_sample"]
        before = self.canonical_state()

        # Scenario 1: Using an inert item is refused by name, no gauge changes, item stays in inventory
        settlement = use_item(self.actor, "t_inert_sample")
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.NOT_USABLE)
        self.assert_state_unchanged(before)

        # Preflight also reports NOT_USABLE directly
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_inert_sample"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.NOT_USABLE)
        self.assert_state_unchanged(before)

        # Scenario 2: Equipping an inert item is refused by name, equipment state unchanged
        toggle_result = toggle_equipment(self.actor, "t_inert_sample")
        self.assertEqual(toggle_result.outcome, "rejected")
        self.assertIs(toggle_result.reason, EquipmentToggleReason.NOT_EQUIPMENT)
        self.assert_state_unchanged(before)

        # Scenario 3: An inert item is still a first-class inventory object
        self.assertEqual(inert_item.display_name_zh, "合成無機制物件")
        self.assertTrue(inert_item.presentation.summary_zh)
        self.assertIsNone(inert_item.use_mechanics)
        self.assertIsNone(inert_item.equipment_slot)

    def test_missing_ownership_rejects_without_effect(self):
        self.hurt(10)
        self.actor.db.inventory = ["t_huskapple"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.ITEM_NOT_HELD)
        self.assert_state_unchanged(before)

    def test_eligible_preflight_writes_nothing(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertTrue(preflight.allowed)
        self.assertIsNotNone(preflight.plan)
        (step,) = preflight.plan.steps
        self.assertEqual(step.amount, HEAL_AMOUNT)
        self.assert_state_unchanged(before)

    def test_visual_metadata_cannot_make_an_item_usable(self):
        material = live_item_registry()["t_huskapple"]
        inspect_only = replace(
            material,
            presentation=replace(material.presentation, kind=ItemKind.POTION),
        )
        self.register_fixture(inspect_only)
        self.hurt(10)
        self.actor.db.inventory = ["t_huskapple"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_huskapple"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.NOT_USABLE)
        self.assert_state_unchanged(before)

    def test_unknown_item_rejects(self):
        self.hurt(10)
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "no_such_item"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.UNKNOWN_ITEM)

    def test_combat_permission_governs_combat_mode(self):
        self.register_fixture(
            _fixture_item("t_quiet_tonic", consumable=True, combat_allowed=False)
        )
        self.hurt(10)
        self.actor.db.inventory = ["t_quiet_tonic"]
        rejected = preflight_item_use(
            ItemUseRequest(self.actor, "t_quiet_tonic"), in_combat=True
        )
        self.assertIs(rejected.reason, ItemUseReason.COMBAT_NOT_ALLOWED)
        allowed = preflight_item_use(
            ItemUseRequest(self.actor, "t_quiet_tonic"), in_combat=False
        )
        self.assertTrue(allowed.allowed)

    def test_malformed_inventory_fails_closed(self):
        self.hurt(10)
        self.actor.db.inventory = [42]
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.MALFORMED_INVENTORY)

    def test_malformed_hp_storage_fails_closed(self):
        self.actor.db.inventory = ["t_moss_tonic"]
        traits = self.actor.attributes.get("traits", category="traits")
        traits["hp"] = {"trait_type": "gauge"}
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.MALFORMED_TRAITS)
