"""Slice of ``test_item_use``: MultiEffectSettlementTests."""
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
    _APPLY_KEY,
    _BOTH_FULL_KEY,
    _GUARD_KEY,
    _MULTI_KEY,
    _MultiEffectTestCase,
    _PLEASURE_DOWN_KEY,
    _PLEASURE_UP_KEY,
    _POISON_DRAFT_KEY,
    _UNIQUE2_KEY,
    _UNIQUE_KEY,
    _WARDEN_KEY,
    _equipment_shape,
)


class MultiEffectSettlementTests(_MultiEffectTestCase):
    """Delta requirement: multi-effect item use settlement."""

    @covers_requirement(
        "item-use-resolution::受洗聖水-purges-debuffs-through-an-ordinary-status-removal-effect"
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
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically",
        "item-use-resolution::an-ineffective-effect-is-skipped-silently-rather-than-failing-the-use"
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
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically",
        "item-use-resolution::every-effect-family-names-its-own-ineffective-reason"
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
        "item-use-resolution::item-use-applies-effect-and-conditional-consumption-atomically",
        "item-use-resolution::every-effect-family-names-its-own-ineffective-reason"
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
        "item-use-resolution::受洗聖水-purges-debuffs-through-an-ordinary-status-removal-effect"
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

    @covers_requirement(
        "lore-item-catalog::a-usable-item-s-pleasure-gain-routes-through-the-shared-intimacy-writer"
    )
    def test_pleasure_gain_uses_the_shared_writer(self):
        # Scenario 1: A pleasure gain needs no status vocabulary
        profile = live_item_effect_profiles()[_PLEASURE_UP_KEY]
        self.assertEqual(len(profile.effects), 1)
        self.assertIs(profile.effects[0].stat, ItemStat.PLEASURE)
        self.assertFalse(hasattr(profile.effects[0], "status"))
        self.assertFalse(hasattr(profile.effects[0], "remove_status"))

        # Scenario 2: A device's stimulation drives the same cascade as a skill's
        self.set_pleasure(60)
        self.actor.sexual.wetness.value = 1
        wetness_before = self.actor.sexual.wetness.value
        self.assertEqual(self.actor.sexual.arousal.level, "高度")
        self.actor.db.inventory = [_PLEASURE_UP_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.pleasure(), 90)
        self.assertEqual(self.actor.sexual.arousal.level, "極限")
        self.assertEqual(self.actor.sexual.wetness.value, wetness_before + 1)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["amount"], 30)
        self.assertIn("提升", entry.text_template)

        # Clamped near-ceiling case: reported amount is actual gauge delta, not declared
        self.set_pleasure(85)
        self.actor.db.inventory = [_PLEASURE_UP_KEY]
        clamped_result = resolve_item_use(
            ItemUseRequest(self.actor, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertEqual(clamped_result.outcome, "success")
        self.assertEqual(self.pleasure(), 100)
        (clamped_entry,) = clamped_result.event_log.entries
        self.assertEqual(clamped_entry.data["amount"], 15)

    @covers_requirement(
        "lore-item-catalog::a-usable-item-s-pleasure-gain-routes-through-the-shared-intimacy-writer"
    )
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

    @covers_requirement(
        "lore-item-catalog::a-usable-item-s-pleasure-gain-routes-through-the-shared-intimacy-writer"
    )
    def test_unmaterialized_intimacy_state_preflight_allows_and_settles_gain(self):
        # Task 5.1: unmaterialised intimacy state
        from typeclasses.npcs import NPC
        fresh = create_object(NPC, key="t_unmaterialized_npc")
        fresh.race = "human"
        fresh.apply_race_baseline()
        fresh.location = self.actor.location
        fresh.db.inventory = [_PLEASURE_UP_KEY]
        # Assert sexual_traits is unmaterialized before the call
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))
        self.assertNotIn("sexual", fresh.__dict__)

        # Preflight's fail-closed read does not reject it
        preflight = preflight_item_use(
            ItemUseRequest(fresh, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertTrue(preflight.allowed)
        self.assertIsNone(preflight.reason)

        # Still unmaterialized after preflight!
        self.assertIsNone(fresh.attributes.get("sexual_traits", category="traits"))

        # Settlement raises pleasure through the shared writer
        result = resolve_item_use(
            ItemUseRequest(fresh, _PLEASURE_UP_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(fresh.sexual.pleasure.base), 30)
        (entry,) = result.event_log.entries
        self.assertEqual(entry.data["stat"], "pleasure")
        self.assertEqual(entry.data["amount"], 30)
