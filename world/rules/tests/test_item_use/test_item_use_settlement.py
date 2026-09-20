"""Slice of ``test_item_use``: ExplorationItemUseTests, ItemUseSettlementTests."""
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
    ITEM_USE_SECONDS,
    _ItemUseTestCase,
    _TONIC_KEY,
    _fixture_item,
)


class ItemUseSettlementTests(_ItemUseTestCase):
    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_consumable_healing_removes_exactly_one_unit(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic", "t_moss_tonic"]
        before_hp = int(self.actor.traits.hp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.hp.current), before_hp + HEAL_AMOUNT)
        self.assertEqual(list_items(self.actor), ["t_moss_tonic"])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_materialized_consumable_removes_one_mirror(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic", "t_moss_tonic"]
        materialize_registry_object(self.actor, "t_moss_tonic")
        materialize_registry_object(self.actor, "t_moss_tonic")
        mirrors = [o.id for o in self.actor.contents if registry_key_for_object(o) == "t_moss_tonic"]
        self.assertEqual(len(mirrors), 2)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        remaining = [o.id for o in self.actor.contents if registry_key_for_object(o) == "t_moss_tonic"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(list_items(self.actor), ["t_moss_tonic"])
        self.assertTrue(ObjectDB.objects.filter(pk=remaining[0]).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_key_only_consumable_fabricates_and_removes_nothing(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        unrelated = materialize_registry_object(self.actor, "t_huskapple")
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), [])
        remaining_keys = [registry_key_for_object(o) for o in self.actor.contents]
        self.assertEqual(remaining_keys, ["t_huskapple"])
        self.assertTrue(ObjectDB.objects.filter(pk=unrelated.id).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_reusable_use_preserves_quantity_and_mirrors(self):
        self.register_fixture(_fixture_item("t_reusable_tonic", consumable=False))
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_reusable_tonic"]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_reusable_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), ["t_reusable_tonic"])
        after = self.canonical_state()
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["contents"], before["contents"])

    @covers_requirement(
        "lore-item-catalog::a-non-consuming-use-settles-without-spending-the-item"
    )
    def test_non_consuming_item_preserves_inventory_and_advances_clock(self):
        # Scenario 1: A reusable item survives its own use
        self.register_fixture(_fixture_item("t_reusable_device", consumable=False))
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_reusable_device"]
        clock = WorldClock()
        settlement = use_item(self.actor, "t_reusable_device", clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(list_items(self.actor), ["t_reusable_device"])
        self.assertEqual(clock.tick, ITEM_USE_SECONDS)

        # Scenario 2: A consuming item is spent
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic", "t_moss_tonic"]
        consuming_clock = WorldClock()
        consuming_settlement = use_item(
            self.actor, "t_moss_tonic", clock=consuming_clock
        )
        self.assertEqual(consuming_settlement.result.outcome, "success")
        self.assertEqual(list_items(self.actor), ["t_moss_tonic"])
        self.assertEqual(consuming_clock.tick, ITEM_USE_SECONDS)

    def test_healing_clamps_at_maximum_and_reports_actual_amount(self):
        self.hurt(5)
        self.actor.db.inventory = ["t_moss_tonic"]
        before_hp = int(self.actor.traits.hp.current)
        maximum = int(self.actor.traits.hp.max)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.hp.current), maximum)
        entry = result.event_log.entries[0]
        self.assertEqual(entry.data["amount"], maximum - before_hp)
        self.assertLess(entry.data["amount"], HEAL_AMOUNT)

    @covers_requirement(
        "item-use-resolution::successful-item-use-emits-a-stable-eventlog-entry"
    )
    def test_item_used_log_carries_the_exact_data_fields(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        log = result.event_log
        self.assertEqual(log.skill_key, _TONIC_KEY)
        self.assertEqual(log.targets, (self.actor.key,))
        self.assertEqual(len(log.entries), 1)
        entry = log.entries[0]
        self.assertEqual(entry.kind, "item_used")
        self.assertEqual(
            set(entry.data), {"item_key", "consumable", "stat", "amount"}
        )
        self.assertEqual(entry.data["item_key"], _TONIC_KEY)
        self.assertEqual(entry.data["stat"], "hp")
        self.assertIs(entry.data["consumable"], True)
        self.assertEqual(entry.data["amount"], HEAL_AMOUNT)

    @covers_requirement(
        "item-use-resolution::item-use-preflight-is-side-effect-free-and-revalidates-current-conditions"
    )
    def test_rejected_settlement_writes_nothing(self):
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        self.actor.db.inventory = ["t_moss_tonic"]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.HP_FULL)
        self.assertIsNone(result.event_log)
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_inventory_failure_rolls_back_hp_and_journal(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        before = self.canonical_state()
        with patch(
            "world.rules.items.settlement.plan_inventory_delta",
            side_effect=RuntimeError("inventory boom"),
        ):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
                )
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_mirror_deletion_failure_rolls_back_every_surface(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        materialize_registry_object(self.actor, "t_moss_tonic")
        mirror_pk = next(
            o.id for o in self.actor.contents if registry_key_for_object(o) == "t_moss_tonic"
        )
        before = self.canonical_state()
        from world.rules.items import settlement as items_module

        real_delete = items_module._delete_mirror

        def boom(actor, plan, journal):
            real_delete(actor, plan, journal)
            raise RuntimeError("mirror boom")

        with patch.object(items_module, "_delete_mirror", boom):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, "t_moss_tonic"), in_combat=False
                )
        # Durable rows and every cache agree with the pre-call state.
        self.assert_state_unchanged(before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())
        # The deleted instance is out of the idmapper so the fetch is fresh.
        live = ObjectDB.objects.get(pk=mirror_pk)
        self.assertIn(live.id, [o.id for o in self.actor.contents])


class ExplorationItemUseTests(_ItemUseTestCase):
    def setUp(self):
        super().setUp()
        self._sources = dict(_EVENT_SOURCES)

        def restore_sources():
            _EVENT_SOURCES.clear()
            _EVENT_SOURCES.update(self._sources)

        self.addCleanup(restore_sources)

    @staticmethod
    def _raising_stage():
        return EventSourceRegistration(
            lambda start, end: (_ for _ in ()).throw(
                RuntimeError("simulated clock boundary failure")
            ),
            None,
        )

    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-time-once"
    )
    def test_exploration_use_advances_the_canonical_cost_once(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        clock = WorldClock()
        settlement = use_item(self.actor, "t_moss_tonic", clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(clock.tick, ITEM_USE_SECONDS)
        self.assertEqual(list_items(self.actor), [])

    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-time-once"
    )
    def test_rejected_exploration_use_advances_no_time(self):
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        self.actor.db.inventory = ["t_moss_tonic"]
        clock = WorldClock()
        before = self.canonical_state()
        settlement = use_item(self.actor, "t_moss_tonic", clock=clock)
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.HP_FULL)
        self.assertEqual(clock.tick, 0)
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-time-once"
    )
    def test_clock_callback_failure_rolls_back_item_and_clock_together(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        materialize_registry_object(self.actor, "t_moss_tonic")
        mirror_pk = next(
            o.id for o in self.actor.contents if registry_key_for_object(o) == "t_moss_tonic"
        )
        before = self.canonical_state()
        _EVENT_SOURCES["shop_hours"] = self._raising_stage()
        clock = WorldClock()
        with self.assertRaises(RuntimeError):
            use_item(self.actor, "t_moss_tonic", clock=clock)
        self.assertEqual(clock.tick, 0)
        self.assert_state_unchanged(before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_active_combat_session_rejects_exploration_use(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["t_moss_tonic"]
        clock = WorldClock()
        with patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            settlement = use_item(self.actor, "t_moss_tonic", clock=clock)
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.ACTIVE_SESSION)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(list_items(self.actor), ["t_moss_tonic"])
