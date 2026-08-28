"""Deterministic tests for item-use preflight, settlement, and the clock facade.

Covers side-effect-free eligibility, atomic effect/consumption settlement
including contained-mirror handling and cache restoration, the stable
``item_used`` event identity, and the composed out-of-combat clock boundary.
"""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemEffectKey,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.rules.clock import EventSourceRegistration, WorldClock, _EVENT_SOURCES
from world.rules.equipment import materialize_registry_object, registry_key_for_object
from world.skills.equipment import list_items
from world.rules.items import (
    ITEM_EFFECT_RULES,
    ITEM_USE_SECONDS,
    ItemUseReason,
    ItemUseRequest,
    preflight_item_use,
    resolve_item_use,
    use_item,
)

HEAL_AMOUNT = ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount


def _presentation(kind: ItemKind = ItemKind.POTION) -> ItemPresentation:
    return ItemPresentation(
        kind=kind,
        icon_key=ItemIconKey.POTION,
        rarity=ItemRarity.COMMON,
        summary_zh="測試用的治療物品。",
    )


def _fixture_item(
    key: str,
    *,
    consumable: bool,
    combat_allowed: bool = True,
    kind: ItemKind = ItemKind.POTION,
) -> ItemDefinition:
    return ItemDefinition(
        key=key,
        display_name_zh="測試物品",
        price_table_key="potion",
        sellable=False,
        presentation=_presentation(kind),
        use_mechanics=ItemUseMechanics(
            effect_key=ItemEffectKey.SELF_HEAL,
            consumable=consumable,
            combat_allowed=combat_allowed,
        ),
    )


class _ItemUseTestCase(EvenniaTest):
    """Shared item-use setup: registry hygiene and an injured baseline actor."""

    def setUp(self):
        super().setUp()
        registry_snapshot = dict(ITEM_REGISTRY)

        def restore_registry():
            ITEM_REGISTRY.clear()
            ITEM_REGISTRY.update(registry_snapshot)

        self.addCleanup(restore_registry)
        self.actor = self.char1
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.inventory = []
        self.actor.db.equipment = None

    def register_fixture(self, definition: ItemDefinition) -> None:
        """Add one fixture definition to the live registry (cleanup-restore)."""
        ITEM_REGISTRY[definition.key] = definition

    def hurt(self, missing: int) -> tuple[int, int]:
        """Lower the actor's HP by ``missing``; return (current, maximum)."""
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum - missing
        return maximum - missing, maximum

    def canonical_state(self) -> dict:
        """Capture every durable surface an item use could touch."""
        return {
            "inventory": deepcopy(self.actor.db.inventory),
            "equipment": deepcopy(self.actor.db.equipment),
            "traits": deepcopy(self.actor.attributes.get("traits", category="traits")),
            "quest_log": deepcopy(self.actor.db.quest_log),
            "contents": sorted(
                (obj.id, registry_key_for_object(obj))
                for obj in self.actor.contents
            ),
        }

    def assert_state_unchanged(self, before: dict) -> None:
        self.assertEqual(self.canonical_state(), before)


class ItemUsePreflightTests(_ItemUseTestCase):
    def test_full_hp_rejects_with_hp_full(self):
        self.actor.db.inventory = ["healing_potion"]
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.HP_FULL)
        self.assertIsNone(preflight.plan)
        self.assert_state_unchanged(before)

    def test_missing_ownership_rejects_without_effect(self):
        self.hurt(10)
        self.actor.db.inventory = ["meal"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.ITEM_NOT_HELD)
        self.assert_state_unchanged(before)

    def test_eligible_preflight_writes_nothing(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertTrue(preflight.allowed)
        self.assertIsNotNone(preflight.plan)
        self.assertEqual(preflight.plan.amount, HEAL_AMOUNT)
        self.assert_state_unchanged(before)

    def test_visual_metadata_cannot_make_an_item_usable(self):
        inspect_only = replace(
            ITEM_REGISTRY["meal"],
            presentation=replace(ITEM_REGISTRY["meal"].presentation, kind=ItemKind.POTION),
        )
        self.register_fixture(inspect_only)
        self.hurt(10)
        self.actor.db.inventory = ["meal"]
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "meal"), in_combat=False
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
            _fixture_item("test_quiet_tonic", consumable=True, combat_allowed=False)
        )
        self.hurt(10)
        self.actor.db.inventory = ["test_quiet_tonic"]
        rejected = preflight_item_use(
            ItemUseRequest(self.actor, "test_quiet_tonic"), in_combat=True
        )
        self.assertIs(rejected.reason, ItemUseReason.COMBAT_NOT_ALLOWED)
        allowed = preflight_item_use(
            ItemUseRequest(self.actor, "test_quiet_tonic"), in_combat=False
        )
        self.assertTrue(allowed.allowed)

    def test_malformed_inventory_fails_closed(self):
        self.hurt(10)
        self.actor.db.inventory = [42]
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.MALFORMED_INVENTORY)

    def test_malformed_hp_storage_fails_closed(self):
        self.actor.db.inventory = ["healing_potion"]
        traits = self.actor.attributes.get("traits", category="traits")
        traits["hp"] = {"trait_type": "gauge"}
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertIs(preflight.reason, ItemUseReason.MALFORMED_TRAITS)


class RegistryEffectKeyTests(_ItemUseTestCase):
    """The shipped registry's non-default effect keys settle through the
    gauge-general path with real rulebook magnitudes."""

    def drain_mp(self, missing: int) -> tuple[int, int]:
        maximum = int(self.actor.traits.mp.max)
        self.actor.traits.mp.current = maximum - missing
        return maximum - missing, maximum

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_registry_greater_heal_potion_uses_the_rulebook_magnitude(self):
        greater = ITEM_EFFECT_RULES[ItemEffectKey.GREATER_HEAL].amount
        self.assertGreater(greater, HEAL_AMOUNT)
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = max(1, maximum - greater - 5)
        self.actor.db.inventory = [
            "greater_healing_potion",
            "greater_healing_potion",
        ]
        before_hp = int(self.actor.traits.hp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "greater_healing_potion"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        expected = min(before_hp + greater, maximum)
        self.assertEqual(int(self.actor.traits.hp.current), expected)
        entry = result.event_log.entries[0]
        self.assertEqual(entry.data["amount"], expected - before_hp)
        self.assertEqual(list_items(self.actor), ["greater_healing_potion"])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_registry_mana_potion_writes_the_mp_gauge_only(self):
        restore = ITEM_EFFECT_RULES[ItemEffectKey.MANA_RESTORE].amount
        self.drain_mp(restore + 5)
        self.actor.db.inventory = ["mana_potion"]
        before_hp = int(self.actor.traits.hp.current)
        before_mp = int(self.actor.traits.mp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "mana_potion"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.mp.current), before_mp + restore)
        self.assertEqual(int(self.actor.traits.hp.current), before_hp)
        self.assertEqual(list_items(self.actor), [])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_mana_restore_clamps_at_maximum_mp(self):
        restore = ITEM_EFFECT_RULES[ItemEffectKey.MANA_RESTORE].amount
        self.drain_mp(5)
        self.actor.db.inventory = ["mana_potion"]
        maximum = int(self.actor.traits.mp.max)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "mana_potion"), in_combat=False
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
        self.actor.db.inventory = ["mana_potion"]
        maximum = int(self.actor.traits.mp.max)
        self.actor.traits.mp.current = maximum
        before = self.canonical_state()
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, "mana_potion"), in_combat=False
        )
        self.assertFalse(preflight.allowed)
        self.assertIs(preflight.reason, ItemUseReason.MP_FULL)
        self.assertIsNone(preflight.plan)
        self.assert_state_unchanged(before)


class ItemUseSettlementTests(_ItemUseTestCase):
    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_consumable_healing_removes_exactly_one_unit(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion", "healing_potion"]
        before_hp = int(self.actor.traits.hp.current)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.hp.current), before_hp + HEAL_AMOUNT)
        self.assertEqual(list_items(self.actor), ["healing_potion"])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_materialized_consumable_removes_one_mirror(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion", "healing_potion"]
        materialize_registry_object(self.actor, "healing_potion")
        materialize_registry_object(self.actor, "healing_potion")
        mirrors = [o.id for o in self.actor.contents if registry_key_for_object(o) == "healing_potion"]
        self.assertEqual(len(mirrors), 2)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        remaining = [o.id for o in self.actor.contents if registry_key_for_object(o) == "healing_potion"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(list_items(self.actor), ["healing_potion"])
        self.assertTrue(ObjectDB.objects.filter(pk=remaining[0]).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_key_only_consumable_fabricates_and_removes_nothing(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion"]
        unrelated = materialize_registry_object(self.actor, "meal")
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), [])
        remaining_keys = [registry_key_for_object(o) for o in self.actor.contents]
        self.assertEqual(remaining_keys, ["meal"])
        self.assertTrue(ObjectDB.objects.filter(pk=unrelated.id).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_reusable_use_preserves_quantity_and_mirrors(self):
        self.register_fixture(_fixture_item("test_reusable_tonic", consumable=False))
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["test_reusable_tonic"]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, "test_reusable_tonic"), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(list_items(self.actor), ["test_reusable_tonic"])
        after = self.canonical_state()
        self.assertEqual(after["inventory"], before["inventory"])
        self.assertEqual(after["contents"], before["contents"])

    def test_healing_clamps_at_maximum_and_reports_actual_amount(self):
        self.hurt(5)
        self.actor.db.inventory = ["healing_potion"]
        before_hp = int(self.actor.traits.hp.current)
        maximum = int(self.actor.traits.hp.max)
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
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
        self.actor.db.inventory = ["healing_potion"]
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
        )
        log = result.event_log
        self.assertEqual(log.skill_key, "healing_potion")
        self.assertEqual(log.targets, (self.actor.key,))
        self.assertEqual(len(log.entries), 1)
        entry = log.entries[0]
        self.assertEqual(entry.kind, "item_used")
        self.assertEqual(
            set(entry.data), {"item_key", "effect_key", "consumable", "amount"}
        )
        self.assertEqual(entry.data["item_key"], "healing_potion")
        self.assertEqual(entry.data["effect_key"], "self_heal")
        self.assertIs(entry.data["consumable"], True)
        self.assertEqual(entry.data["amount"], HEAL_AMOUNT)

    @covers_requirement(
        "item-use-resolution::item-use-preflight-is-side-effect-free-and-revalidates-current-conditions"
    )
    def test_rejected_settlement_writes_nothing(self):
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        self.actor.db.inventory = ["healing_potion"]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, "healing_potion"), in_combat=False
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
        self.actor.db.inventory = ["healing_potion"]
        before = self.canonical_state()
        with patch(
            "world.rules.items.plan_inventory_delta",
            side_effect=RuntimeError("inventory boom"),
        ):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, "healing_potion"), in_combat=False
                )
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_mirror_deletion_failure_rolls_back_every_surface(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion"]
        materialize_registry_object(self.actor, "healing_potion")
        mirror_pk = next(
            o.id for o in self.actor.contents if registry_key_for_object(o) == "healing_potion"
        )
        before = self.canonical_state()
        from world.rules import items as items_module

        real_delete = items_module._delete_mirror

        def boom(actor, plan, journal):
            real_delete(actor, plan, journal)
            raise RuntimeError("mirror boom")

        with patch.object(items_module, "_delete_mirror", boom):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, "healing_potion"), in_combat=False
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
        self.actor.db.inventory = ["healing_potion"]
        clock = WorldClock()
        settlement = use_item(self.actor, "healing_potion", clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(clock.tick, ITEM_USE_SECONDS)
        self.assertEqual(list_items(self.actor), [])

    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-time-once"
    )
    def test_rejected_exploration_use_advances_no_time(self):
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum
        self.actor.db.inventory = ["healing_potion"]
        clock = WorldClock()
        before = self.canonical_state()
        settlement = use_item(self.actor, "healing_potion", clock=clock)
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.HP_FULL)
        self.assertEqual(clock.tick, 0)
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::out-of-combat-item-use-advances-deterministic-time-once"
    )
    def test_clock_callback_failure_rolls_back_item_and_clock_together(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion"]
        materialize_registry_object(self.actor, "healing_potion")
        mirror_pk = next(
            o.id for o in self.actor.contents if registry_key_for_object(o) == "healing_potion"
        )
        before = self.canonical_state()
        _EVENT_SOURCES["shop_hours"] = self._raising_stage()
        clock = WorldClock()
        with self.assertRaises(RuntimeError):
            use_item(self.actor, "healing_potion", clock=clock)
        self.assertEqual(clock.tick, 0)
        self.assert_state_unchanged(before)
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_active_combat_session_rejects_exploration_use(self):
        self.hurt(HEAL_AMOUNT + 5)
        self.actor.db.inventory = ["healing_potion"]
        clock = WorldClock()
        with patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            settlement = use_item(self.actor, "healing_potion", clock=clock)
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, ItemUseReason.ACTIVE_SESSION)
        self.assertEqual(clock.tick, 0)
        self.assertEqual(list_items(self.actor), ["healing_potion"])
