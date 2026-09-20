"""Slice of ``test_item_use``: RegistryProfileGaugeTests."""
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
    GREATER_AMOUNT,
    HEAL_AMOUNT,
    MANA_AMOUNT,
    _ItemUseTestCase,
)


class RegistryProfileGaugeTests(_ItemUseTestCase):
    """Scoped profiles with non-default magnitudes settle through the
    gauge-general path with their own rulebook-declared amounts."""

    def drain_mp(self, missing: int) -> tuple[int, int]:
        maximum = int(self.actor.traits.mp.max)
        self.actor.traits.mp.current = maximum - missing
        return maximum - missing, maximum

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_registry_greater_heal_potion_uses_the_rulebook_magnitude(self):
        greater = GREATER_AMOUNT
        self.assertGreater(greater, HEAL_AMOUNT)
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = max(1, maximum - greater - 5)
        self.actor.db.inventory = [
            "t_dew_of_vigor",
            "t_dew_of_vigor",
        ]
        before_hp = int(self.actor.traits.hp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_dew_of_vigor"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        expected = min(before_hp + greater, maximum)
        self.assertEqual(int(self.actor.traits.hp.current), expected)
        entry = result.event_log.entries[0]
        self.assertEqual(entry.data["amount"], expected - before_hp)
        self.assertEqual(list_items(self.actor), ["t_dew_of_vigor"])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_registry_mana_potion_writes_the_mp_gauge_only(self):
        restore = MANA_AMOUNT
        self.drain_mp(restore + 5)
        self.actor.db.inventory = ["t_mist_vial"]
        before_hp = int(self.actor.traits.hp.current)
        before_mp = int(self.actor.traits.mp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_mist_vial"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.mp.current), before_mp + restore)
        self.assertEqual(int(self.actor.traits.hp.current), before_hp)
        self.assertEqual(list_items(self.actor), [])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_mana_restore_clamps_at_maximum_mp(self):
        restore = MANA_AMOUNT
        self.drain_mp(5)
        self.actor.db.inventory = ["t_mist_vial"]
        maximum = int(self.actor.traits.mp.max)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_mist_vial"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.mp.current), maximum)
        entry = result.event_log.entries[0]
        self.assertEqual(entry.data["amount"], 5)
        self.assertLess(entry.data["amount"], restore)

    @covers_requirement(
        "item-use-resolution::item-use-preflight-is-side-effect-free-and-revalidates-current-conditions"
    )
    def test_full_mp_rejects_with_mp_full(self):
        self.actor.db.inventory = ["t_mist_vial"]
        maximum = int(self.actor.traits.mp.max)
        self.actor.traits.mp.current = maximum
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "t_mist_vial"), in_combat=False
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.MP_FULL)
        self.assertIsNone(preflight.plan)
        self.assert_state_unchanged(before)
