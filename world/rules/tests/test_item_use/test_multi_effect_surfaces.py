"""Slice of ``test_item_use``: NegativeGaugeDrainTests, RemovalSelectorSettlementTests, SettlementScopeSeamTests."""
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
    _ALL_VIAL_KEY,
    _APPLY_KEY,
    _FOCUS_DROP_KEY,
    _MultiEffectTestCase,
    _PLEASURE_DOWN_KEY,
    _SP_DOWN_KEY,
)


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

    @covers_requirement(
        "item-use-resolution::every-effect-family-names-its-own-ineffective-reason"
    )
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
    """Non-self scopes reach real multi-entity resolution (design D2/D4).

    Retired with add-item-effect-targeting: the settlement-time self-only
    fail-closed these tests pinned is replaced by genuine target resolution,
    so the suite pins the new observable contract instead.
    """

    def test_group_scope_profile_reaches_every_present_entity_once(self):
        # Delta: "A multi-target use consumes exactly one unit" — one
        # injected ALL-scoped effect settles one step per present entity,
        # including the actor, and removes exactly one inventory unit.
        from world.rules.item_effects import ItemTargetScope

        injected = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.ALL
                ),
            )
        )
        live_item_effect_profiles()[_APPLY_KEY] = injected
        maximum = self.hurt(50)[1]
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.traits.hp.current = 1
        self.char2.location = self.actor.location
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.hp.current), maximum - 10)
        self.assertEqual(int(self.char2.traits.hp.current), 41)
        self.assertEqual(list_items(self.actor), [])
        log = result.event_log
        self.assertEqual(sorted(log.targets), sorted([self.actor.key, self.char2.key]))
        self.assertEqual(
            sorted(entry.target for entry in log.entries),
            sorted([self.actor.key, self.char2.key]),
        )

    def test_single_scope_without_a_target_rejects_no_target(self):
        # Delta: "A single-entity effect without a target rejects" — the
        # stable NO_TARGET reason fires before the resolver is consulted.
        from world.rules.item_effects import ItemTargetScope

        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SINGLE
                ),
            )
        )
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.NO_TARGET)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])

    def test_unresolved_target_token_rejects_target_invalid(self):
        # Delta: "A player cannot change an item's reach" — a raw shorthand
        # token (or any unresolved key) is a TARGET_INVALID target, never a
        # crash inside the validators.
        from world.rules.item_effects import ItemTargetScope

        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SINGLE
                ),
            )
        )
        self.actor.db.inventory = [_APPLY_KEY]
        for token in ("all", "all-allies", "some_item_key"):
            with self.subTest(token=token):
                result = resolve_item_use(
                    ItemUseRequest(self.actor, _APPLY_KEY, target=token),
                    in_combat=False,
                )
                self.assertEqual(result.outcome, "rejected")
                self.assertIs(result.reason, ItemUseReason.TARGET_INVALID)
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
