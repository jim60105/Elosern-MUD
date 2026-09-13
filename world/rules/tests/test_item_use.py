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

from ._combat_session_helpers import (
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
from world.rules import item_effects as _item_effects_module
from world.rules.tests._equipment_rulebook_probes import immune_to_key, rule_for

ITEM_USE_SECONDS = _item_effects_module.ITEM_USE_SECONDS


def _gauge_profile(stat: ItemStat, amount: int) -> ItemEffectProfile:
    """One single-gauge synthetic profile (the fixture's own magnitudes)."""
    return ItemEffectProfile(effects=(GaugeAdjustEffect(stat=stat, amount=amount),))


HEAL_PROFILE = _gauge_profile(ItemStat.HP, 40)
GREATER_PROFILE = _gauge_profile(ItemStat.HP, 120)
MANA_PROFILE = _gauge_profile(ItemStat.MP, 40)
HEAL_AMOUNT = HEAL_PROFILE.effects[0].amount
GREATER_AMOUNT = GREATER_PROFILE.effects[0].amount
MANA_AMOUNT = MANA_PROFILE.effects[0].amount

_TONIC_KEY = "t_moss_tonic"
_GREATER_KEY = "t_dew_of_vigor"
_MANA_KEY = "t_mist_vial"


def _consumable(key: str) -> ItemDefinition:
    """One synthetic consumable; its effect arrives via the profile scope."""
    return make_item(
        key,
        display_name_zh="合成治療藥劑",
        price_table_key="t_mossmeals",
        use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=True),
    )


_SCOPE_ITEMS = {
    d.key: d
    for d in (_consumable(_TONIC_KEY), _consumable(_GREATER_KEY), _consumable(_MANA_KEY))
}

# The rulebook-side half of the scoped rows: settlement resolves effects by
# item key, so the scope carries each usable item's profile with it.
_SCOPE_PROFILES = {
    _TONIC_KEY: HEAL_PROFILE,
    _GREATER_KEY: GREATER_PROFILE,
    _MANA_KEY: MANA_PROFILE,
}


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
        price_table_key="t_mossmeals",
        sellable=False,
        presentation=_presentation(kind),
        use_mechanics=ItemUseMechanics(
            consumable=consumable,
            combat_allowed=combat_allowed,
        ),
    )


def _equipment_shape(*accessories: str) -> dict:
    """The canonical equipment storage shape with the given accessories."""
    return {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": list(accessories),
    }


class _ItemUseTestCase(EvenniaTest):
    """Shared item-use setup: registry hygiene and an injured baseline actor."""

    def setUp(self):
        super().setUp()
        # Kit scope: the item registry swaps to merged rows (fixtures below
        # mutate the scoped copy, which the kit restores on exit), with the
        # matching rulebook-side profiles.
        open_synthetic_scope(
            self,
            "items",
            extra={"items": dict(_SCOPE_ITEMS), "item_effect_profiles": dict(_SCOPE_PROFILES)},
        )
        self.actor = self.char1
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.inventory = []
        self.actor.db.equipment = None

    def register_fixture(
        self, definition: ItemDefinition, profile: ItemEffectProfile = HEAL_PROFILE
    ) -> None:
        """Add one fixture definition and its profile to the scope (kit restores)."""
        live_item_registry()[definition.key] = definition
        live_item_effect_profiles()[definition.key] = profile

    def hurt(self, missing: int) -> tuple[int, int]:
        """Lower the actor's HP by ``missing``; return (current, maximum)."""
        maximum = int(self.actor.traits.hp.max)
        self.actor.traits.hp.current = maximum - missing
        return maximum - missing, maximum

    def pleasure(self) -> int:
        """The actor's pleasure gauge base through the handler."""
        return int(self.actor.sexual.pleasure.base)

    def set_pleasure(self, value: int) -> None:
        """Write the pleasure counter through its handler."""
        self.actor.sexual.pleasure.base = value

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
            "world.rules.items.plan_inventory_delta",
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
        from world.rules import items as items_module

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


# --- multi-effect settlement (add-declarative-item-effects design §5) ---
#
# The profiles below declare the design-§5 shapes (ordered gauge + status
# verbs, bounded partial settlement, per-step logging, per-item status
# source identity) against synthetic items, so the shipped rows stay the
# frozen regression's contract.
_MULTI_KEY = "t_battle_elixir"
_APPLY_KEY = "t_focus_draft"
_UNIQUE_KEY = "t_regent_tea"
_UNIQUE2_KEY = "t_regent_tea_b"
_POISON_DRAFT_KEY = "t_noxious_draft"
_FOCUS_DROP_KEY = "t_focus_drop"
_ALL_VIAL_KEY = "t_all_vial"
_PLEASURE_UP_KEY = "t_bliss_drop"
_PLEASURE_DOWN_KEY = "t_cold_compress"
_SP_DOWN_KEY = "t_bitter_tonic"
_GUARD_KEY = "t_guard_charm"
_BOTH_FULL_KEY = "t_full_double"

_WARDEN_KEY = "t_warden_medallion"
_WARDEN = make_item(
    _WARDEN_KEY,
    display_name_zh="合成守護吊飾",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=immune_to_key("poisoned"),
)

_MULTI_PROFILE = ItemEffectProfile(
    effects=(
        StatusRemoveEffect(selector="negative"),
        GaugeAdjustEffect(stat=ItemStat.HP, amount=40),
        StatusApplyEffect(status="focus"),
        GaugeAdjustEffect(stat=ItemStat.PLEASURE, amount=-25),
    )
)
_SCOPE_MULTI_ITEMS = {
    _MULTI_KEY: _consumable(_MULTI_KEY),
    _APPLY_KEY: _consumable(_APPLY_KEY),
    _UNIQUE_KEY: _consumable(_UNIQUE_KEY),
    _UNIQUE2_KEY: _consumable(_UNIQUE2_KEY),
    _POISON_DRAFT_KEY: _consumable(_POISON_DRAFT_KEY),
    _FOCUS_DROP_KEY: _consumable(_FOCUS_DROP_KEY),
    _ALL_VIAL_KEY: _consumable(_ALL_VIAL_KEY),
    _PLEASURE_UP_KEY: _consumable(_PLEASURE_UP_KEY),
    _PLEASURE_DOWN_KEY: _consumable(_PLEASURE_DOWN_KEY),
    _SP_DOWN_KEY: _consumable(_SP_DOWN_KEY),
    _GUARD_KEY: _consumable(_GUARD_KEY),
    _BOTH_FULL_KEY: _consumable(_BOTH_FULL_KEY),
    _WARDEN_KEY: _WARDEN,
}
_SCOPE_MULTI_PROFILES = {
    _MULTI_KEY: _MULTI_PROFILE,
    _APPLY_KEY: ItemEffectProfile(effects=(StatusApplyEffect(status="focus"),)),
    _UNIQUE_KEY: ItemEffectProfile(
        effects=(StatusApplyEffect(status="item_regen_light"),)
    ),
    _UNIQUE2_KEY: ItemEffectProfile(
        effects=(StatusApplyEffect(status="item_regen_light"),)
    ),
    _POISON_DRAFT_KEY: ItemEffectProfile(
        effects=(StatusApplyEffect(status="poisoned"),)
    ),
    _FOCUS_DROP_KEY: ItemEffectProfile(
        effects=(StatusRemoveEffect(selector="focus"),)
    ),
    _ALL_VIAL_KEY: ItemEffectProfile(
        effects=(StatusRemoveEffect(selector="all"),)
    ),
    _PLEASURE_UP_KEY: ItemEffectProfile(
        effects=(GaugeAdjustEffect(stat=ItemStat.PLEASURE, amount=30),)
    ),
    _PLEASURE_DOWN_KEY: ItemEffectProfile(
        effects=(GaugeAdjustEffect(stat=ItemStat.PLEASURE, amount=-25),)
    ),
    _SP_DOWN_KEY: ItemEffectProfile(
        effects=(GaugeAdjustEffect(stat=ItemStat.SP, amount=-30),)
    ),
    _GUARD_KEY: ItemEffectProfile(
        effects=(
            GaugeAdjustEffect(stat=ItemStat.HP, amount=40),
            StatusApplyEffect(status="focus"),
        )
    ),
    _BOTH_FULL_KEY: ItemEffectProfile(
        effects=(
            GaugeAdjustEffect(stat=ItemStat.HP, amount=40),
            GaugeAdjustEffect(stat=ItemStat.MP, amount=40),
        )
    ),
}


class _MultiEffectTestCase(_ItemUseTestCase):
    """Shared registration of the §5 synthetic profiles and immunity prop."""

    def setUp(self):
        super().setUp()
        live_item_registry().update(_SCOPE_MULTI_ITEMS)
        live_item_effect_profiles().update(_SCOPE_MULTI_PROFILES)


class MultiEffectSettlementTests(_MultiEffectTestCase):
    """Delta requirement: multi-effect item use settlement."""

    @covers_requirement(
        "item-use-resolution::blessed-cleansing-consumes-holy-water-to-purge-debuffs"
    )
    def test_effects_execute_in_profile_order_with_one_entry_each(self):
        self.hurt(50)
        self.set_pleasure(60)
        apply_buff(self.actor, "poisoned")
        self.actor.db.inventory = [_MULTI_KEY]
        maximum = int(self.actor.traits.hp.max)
        result = resolve_item_use(
            ItemUseRequest(self.actor, _MULTI_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        # Profile order: purge, heal, grant, drain — all settled truth.
        self.assertEqual(result.event_log.time_cost_seconds, 0)
        self.assertEqual(self.actor.traits.hp.current, maximum - 10)
        self.assertNotIn("poisoned", entity_active_buffs(self.actor))
        self.assertIn("focus", entity_active_buffs(self.actor))
        self.assertEqual(self.pleasure(), 35)
        self.assertEqual(list_items(self.actor), [])
        entries = result.event_log.entries
        self.assertEqual(len(entries), 4)
        self.assertEqual([entry.kind for entry in entries], ["item_used"] * 4)
        self.assertEqual(
            [entry.data for entry in entries],
            [
                {
                    "item_key": _MULTI_KEY,
                    "consumable": True,
                    "status_keys": ["poisoned"],
                    "count": 1,
                },
                {
                    "item_key": _MULTI_KEY,
                    "consumable": True,
                    "stat": "hp",
                    "amount": 40,
                },
                {
                    "item_key": _MULTI_KEY,
                    "consumable": True,
                    "status_keys": ["focus"],
                    "count": 1,
                },
                {
                    "item_key": _MULTI_KEY,
                    "consumable": True,
                    "stat": "pleasure",
                    "amount": -25,
                },
            ],
        )
        self.assertEqual([entry.target for entry in entries], [self.actor.key] * 4)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_ineligible_effects_are_skipped_eligible_ones_still_execute(self):
        # HP already full: the heal step is ineligible; the grant still fires.
        self.actor.db.inventory = [_GUARD_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _GUARD_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertIn("focus", entity_active_buffs(self.actor))
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["status_keys"], ["focus"])
        self.assertEqual(list_items(self.actor), [])

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_all_ineligible_steps_reject_with_no_effect_not_a_bound_code(self):
        # Delta scenario "All-ineligible rejection uses the generic
        # no-effect reason": both full-gauge steps name distinct resources.
        self.actor.db.inventory = [_BOTH_FULL_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _BOTH_FULL_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.NO_EFFECT)
        self.assertIsNone(result.event_log)
        self.assert_state_unchanged(before)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_status_apply_grants_the_named_buff_with_one_entry(self):
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertIn("focus", entity_active_buffs(self.actor))
        (entry,) = result.event_log.entries
        self.assertEqual(
            entry.data,
            {
                "item_key": _APPLY_KEY,
                "consumable": True,
                "status_keys": ["focus"],
                "count": 1,
            },
        )
        self.assertNotIn("effect_key", entry.data)

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_status_apply_immunity_blocks_before_consumption(self):
        # The shipped immunity predicate's debuff-polarity rule, reached
        # through the probed accessory conferring the probed poison immunity.
        self.actor.db.equipment = _equipment_shape(_WARDEN_KEY)
        self.actor.db.inventory = [_POISON_DRAFT_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _POISON_DRAFT_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.STATUS_BLOCKED)
        self.assert_state_unchanged(before)
        self.assertEqual(list_items(self.actor), [_POISON_DRAFT_KEY])

    @covers_requirement(
        "item-use-resolution::blessed-cleansing-consumes-holy-water-to-purge-debuffs"
    )
    def test_per_item_source_keys_keep_distinct_instances(self):
        # Delta scenario: two different items granting the same
        # unique_per_source buff yield two instances (per-item source).
        self.actor.db.inventory = [_UNIQUE_KEY]
        first = resolve_item_use(
            ItemUseRequest(self.actor, _UNIQUE_KEY), in_combat=False
        )
        self.assertEqual(first.outcome, "success")
        self.actor.db.inventory = [_UNIQUE2_KEY]
        second = resolve_item_use(
            ItemUseRequest(self.actor, _UNIQUE2_KEY), in_combat=False
        )
        self.assertEqual(second.outcome, "success")
        instances = list(self.actor.attributes.get("buffs", default={}))
        self.assertEqual(
            sorted(instances),
            [
                f"item_regen_light:item:{_UNIQUE_KEY}",
                f"item_regen_light:item:{_UNIQUE2_KEY}",
            ],
        )

    @covers_requirement(
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically"
    )
    def test_same_item_reuse_keeps_one_instance(self):
        # The per-item source identity makes repeat use refresh, not stack.
        for _ in range(2):
            self.actor.db.inventory = [_UNIQUE_KEY]
            result = resolve_item_use(
                ItemUseRequest(self.actor, _UNIQUE_KEY), in_combat=False
            )
            self.assertEqual(result.outcome, "success")
        instances = list(self.actor.attributes.get("buffs", default={}))
        self.assertEqual(instances, [f"item_regen_light:item:{_UNIQUE_KEY}"])

    def test_pleasure_drain_is_bounded_by_the_zero_floor(self):
        self.set_pleasure(10)
        self.actor.db.inventory = [_PLEASURE_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.pleasure(), 0)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["stat"], "pleasure")
        self.assertEqual(entry.data["amount"], -10)
        self.assertIn("失去", entry.text_template)

    def test_pleasure_gain_uses_the_shared_writer(self):
        self.set_pleasure(60)
        self.actor.db.inventory = [_PLEASURE_UP_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.pleasure(), 90)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["amount"], 30)
        self.assertIn("提升", entry.text_template)

    def test_pleasure_full_at_the_ceiling_rejects_consumption(self):
        self.set_pleasure(100)
        self.actor.db.inventory = [_PLEASURE_UP_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.PLEASURE_FULL)
        self.assert_state_unchanged(before)

    def test_pleasure_drain_at_the_zero_floor_reports_the_bound_code(self):
        # The vocabulary carries no floor-specific code; the stat-bound
        # reason is reused for a drain that can never move.
        self.actor.db.inventory = [_PLEASURE_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.PLEASURE_FULL)


class RemovalSelectorSettlementTests(_MultiEffectTestCase):
    """Concrete and ``all`` removal selectors settle through removal."""

    def test_concrete_selector_removes_only_its_key(self):
        apply_buff(self.actor, "poisoned")
        apply_buff(self.actor, "focus")
        self.actor.db.inventory = [_FOCUS_DROP_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _FOCUS_DROP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), {"poisoned"})
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["status_keys"], ["focus"])
        self.assertEqual(entry.data["count"], 1)

    def test_all_selector_removes_buff_and_debuff_polarity(self):
        apply_buff(self.actor, "poisoned")
        apply_buff(self.actor, "focus")
        self.actor.db.inventory = [_ALL_VIAL_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _ALL_VIAL_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(entity_active_buffs(self.actor), set())
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["status_keys"], ["focus", "poisoned"])
        self.assertEqual(entry.data["count"], 2)

    def test_concrete_selector_with_no_match_rejects(self):
        self.actor.db.inventory = [_FOCUS_DROP_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _FOCUS_DROP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.NOTHING_TO_REMOVE)
        self.assert_state_unchanged(before)


class NegativeGaugeDrainTests(_MultiEffectTestCase):
    """Delta scenario: "A negative stat adjustment stops at zero"."""

    def set_sp(self, value: int) -> int:
        maximum = int(self.actor.traits.sp.max)
        self.actor.traits.sp.base = maximum
        self.actor.traits.sp.current = value
        return value

    def test_sp_drain_lands_on_the_declared_drop(self):
        self.set_sp(50)
        self.actor.db.inventory = [_SP_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _SP_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.sp.current), 20)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["stat"], "sp")
        self.assertEqual(entry.data["amount"], -30)
        self.assertIn("失去", entry.text_template)

    def test_sp_drain_clamps_at_zero_and_reports_the_actual_drop(self):
        self.set_sp(12)
        self.actor.db.inventory = [_SP_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _SP_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.sp.current), 0)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["amount"], -12)

    def test_pleasure_reduction_at_critical_point_does_not_advance_climax(self):
        # Design D2b: a participant sitting at 接近 who has pleasure drained
        # must stay at 接近. Before the negative-gain guard the shared gain
        # writer's was_at_critical_point branch walked it into 進行中.
        self.set_pleasure(80)
        self.actor.sexual.climax_phase.value = "接近"
        self.actor.db.inventory = [_PLEASURE_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.pleasure(), 55)
        self.assertEqual(self.actor.sexual.climax_phase.level, "接近")

    def test_pleasure_drain_does_not_fire_the_gain_cascade(self):
        # A reduction must never bump wetness or advance the climax phase the
        # way the shared gain writer's arousal-coupled cascade does (design
        # Risks); pleasure 95 sits inside the top band, so a drain crosses
        # down out of it and the cascade predicate sees no upward edge.
        self.actor.sexual.pleasure.base = 95
        self.actor.sexual.wetness.value = 2
        wetness_before = self.actor.sexual.wetness.level
        phase_before = self.actor.sexual.climax_phase.level
        self.actor.db.inventory = [_PLEASURE_DOWN_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_DOWN_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.pleasure(), 70)
        self.assertEqual(self.actor.sexual.wetness.level, wetness_before)
        self.assertEqual(self.actor.sexual.climax_phase.level, phase_before)


class SettlementScopeSeamTests(_MultiEffectTestCase):
    """The self-only seam holds even for profiles injected past the loader."""

    def test_non_self_scope_profile_rejects_as_unknown_effect(self):
        # The loader refuses other scopes at startup (rulebook tests); this
        # pins the settlement-time fail-closed for an injected profile.
        from world.rules.item_effects import ItemTargetScope

        injected = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.ALL
                ),
            )
        )
        live_item_effect_profiles()[_APPLY_KEY] = injected
        self.hurt(50)
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.UNKNOWN_EFFECT)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])

    def test_unknown_status_profile_rejects_as_unknown_effect(self):
        # The loader refuses undefined status keys at startup; an injected
        # profile past it must fail closed with a stable reason, never an
        # unhandled KeyError at the command/web boundary.
        injected = ItemEffectProfile(
            effects=(StatusApplyEffect(status="not_a_buff"),)
        )
        live_item_effect_profiles()[_APPLY_KEY] = injected
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.UNKNOWN_EFFECT)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])


class SexualSurfaceRollbackTests(_MultiEffectTestCase):
    """The journal restores the intimate surface a pleasure step wrote."""

    def test_post_gain_fault_restores_the_whole_sexual_surface(self):
        # The +30 gain crosses an arousal band, so the shared writer's
        # cascade bumps wetness mid-transaction. A journal that snapshotted
        # only the pleasure counter would leave the wetness bump behind.
        self.set_pleasure(60)
        self.actor.sexual.wetness.value = 2
        wetness_before = self.actor.sexual.wetness.level
        phase_before = self.actor.sexual.climax_phase.level
        self.actor.db.inventory = [_PLEASURE_UP_KEY]
        with patch(
            "world.rules.items._delete_mirror",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, _PLEASURE_UP_KEY), in_combat=False
                )
        self.assertEqual(self.pleasure(), 60)
        self.assertEqual(self.actor.sexual.wetness.level, wetness_before)
        self.assertEqual(self.actor.sexual.climax_phase.level, phase_before)
        self.assertEqual(list_items(self.actor), [_PLEASURE_UP_KEY])

    def test_post_drain_fault_restores_pleasure_and_buffs(self):
        self.hurt(50)
        self.set_pleasure(60)
        apply_buff(self.actor, "poisoned")
        self.actor.db.inventory = [_MULTI_KEY]
        before_pleasure = self.pleasure()
        before_buffs = set(self.actor.attributes.get("buffs", default={}))
        before_hp = int(self.actor.traits.hp.current)
        before_wetness = self.actor.sexual.wetness.level
        before_phase = self.actor.sexual.climax_phase.level
        with patch(
            "world.rules.items._delete_mirror",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, _MULTI_KEY), in_combat=False
                )
        self.assertEqual(self.pleasure(), before_pleasure)
        self.assertEqual(self.actor.sexual.wetness.level, before_wetness)
        self.assertEqual(self.actor.sexual.climax_phase.level, before_phase)
        self.assertEqual(
            set(self.actor.attributes.get("buffs", default={})), before_buffs
        )
        self.assertEqual(int(self.actor.traits.hp.current), before_hp)
