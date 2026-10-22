"""Slice of ``test_item_use``: drain, removal, scope and accepted-operation evidence tests."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from dataclasses import replace
from unittest.mock import patch
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.lore.items import (
    ItemDefinition,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.narrative.action_adapters import (
    capture_milestone_snapshot,
    record_non_resolver_adult_milestones,
)
from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.rules.clock import (
    AdvanceSource,
    EventSourceRegistration,
    WorldClock,
    _EVENT_SOURCES,
    get_world_clock,
)
from world.rules.combat import CombatProvenance, combat_provenance
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
    ItemTargetScope,
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
    accepted_item_operation_id,
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
    _TONIC_KEY,
    _MultiEffectTestCase,
    _PLEASURE_DOWN_KEY,
    _SP_DOWN_KEY,
    _fixture_item,
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


_GROUP_BLISS_KEY = "t_group_bliss"

_GROUP_BLISS_PROFILE = ItemEffectProfile(
    effects=(
        GaugeAdjustEffect(
            stat=ItemStat.PLEASURE,
            amount=20,
            scope=ItemTargetScope.ALL_ALLIES,
        ),
    )
)


class AcceptedOperationEvidenceTests(_MultiEffectTestCase):
    """An accepted item use owns its own transition-time adult evidence.

    Spec: ``narrative-events`` — non-resolver adult milestones are recorded at
    transition time under an authoritative operation identity, and owner
    rollback removes evidence with the gameplay.
    """

    def setUp(self):
        super().setUp()
        self.register_fixture(
            _fixture_item(_GROUP_BLISS_KEY, consumable=True), _GROUP_BLISS_PROFILE
        )
        self.room = self.actor.location
        self.ally = self.char2
        self.ally.location = self.room
        self.ally.race = "human"
        self.ally.apply_race_baseline()
        self.second_ally = create_object(
            PlayerCharacter, key="item ally two", location=self.room
        )
        self.second_ally.race = "human"
        self.second_ally.apply_race_baseline()
        self.control = create_object(
            PlayerCharacter, key="item control", location=self.room
        )
        self.control.race = "human"
        self.control.apply_race_baseline()
        for entity in (self.ally, self.second_ally):
            entity.sexual.climax_phase.value = "接近"
            entity.sexual.pleasure.base = 40
        self.control.sexual.pleasure.base = 100

    def _operation_milestones(self, source_id: str) -> list[NarrativeEvent]:
        return list(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__action_source_id=source_id,
            )
        )

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_one_accepted_use_owns_each_affected_recipients_crossing(self):
        """Scenario: Accepted item use crossing uses the accepted operation."""
        before_ally = capture_milestone_snapshot(self.ally)
        self.actor.db.inventory = [_GROUP_BLISS_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _GROUP_BLISS_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.ally.sexual.climax_phase.level, "進行中")
        self.assertEqual(self.second_ally.sexual.climax_phase.level, "進行中")

        milestones = list(NarrativeEvent.objects.filter(event_type="adult_milestone"))
        self.assertEqual(
            {event.content["entity_id"] for event in milestones},
            {str(self.ally.pk), str(self.second_ally.pk)},
        )
        (operation_id,) = {event.content["action_source_id"] for event in milestones}
        self.assertTrue(operation_id.startswith("item:accept:"))
        self.assertEqual(len(self._operation_milestones(operation_id)), 2)

        # The unaffected control was ineligible at the top of its gauge: it
        # gained no evidence and kept its state.
        self.assertEqual(int(self.control.sexual.pleasure.base), 100)
        self.assertEqual(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__entity_id=str(self.control.pk),
            ).count(),
            0,
        )

        # Re-delivering the committed evidence reuses the original records.
        before_ids = [
            (event.pk, event.source_id)
            for event in self._operation_milestones(operation_id)
        ]
        record_non_resolver_adult_milestones(
            self.ally,
            before_ally,
            source_id=operation_id,
            tick=int(get_world_clock().tick),
        )
        self.assertEqual(
            [
                (event.pk, event.source_id)
                for event in self._operation_milestones(operation_id)
            ],
            before_ids,
        )

        # A later clock read never re-dates this operation's crossing, under
        # this or any other source.
        onsets_before = NarrativeEvent.objects.filter(
            event_type="adult_milestone", content__identifier="climax_onset"
        ).count()
        WorldClock(tick=0).advance(6, AdvanceSource.COMMAND, (self.ally,))
        self.assertEqual(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone", content__identifier="climax_onset"
            ).count(),
            onsets_before,
        )
        self.assertEqual(len(self._operation_milestones(operation_id)), 2)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_non_adult_use_and_preexisting_state_record_no_milestone(self):
        """A non-adult item use and an already-active phase create nothing."""
        self.hurt(20)
        self.actor.sexual.climax_phase.value = "進行中"
        self.actor.db.inventory = [_TONIC_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _TONIC_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            NarrativeEvent.objects.filter(event_type="adult_milestone").count(), 0
        )

    @covers_requirement(
        "narrative-events::durable-source-identity-makes-projection-recoverable"
    )
    def test_accepted_operation_identity_is_never_the_item_key_or_tick(self):
        first = accepted_item_operation_id(str(self.actor.pk), _GROUP_BLISS_KEY)
        second = accepted_item_operation_id(str(self.actor.pk), _GROUP_BLISS_KEY)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("item:accept:"))
        for slot in (0, 1):
            with combat_provenance(
                CombatProvenance(
                    engagement_id="hostile:items:1",
                    round_ordinal=1,
                    slot_ordinal=slot,
                )
            ):
                value = accepted_item_operation_id(
                    str(self.actor.pk), _GROUP_BLISS_KEY
                )
            self.assertEqual(
                value,
                f"item:combat:hostile:items:1:r1:s{slot}:"
                f"{self.actor.pk}:{_GROUP_BLISS_KEY}",
            )
        with self.assertRaises(ValueError):
            accepted_item_operation_id(
                str(self.actor.pk),
                _GROUP_BLISS_KEY,
                context=SimpleNamespace(battlefield=object()),
            )

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_two_slots_of_one_engagement_keep_distinct_operation_sources(self):
        """Scenario: two accepted operations in different slots stay distinct."""
        from world.rules.items import ItemUseRequest
        from world.rules.targeting import RoomActionContext

        key = "t_slot_bliss"
        self.register_fixture(
            _fixture_item(key, consumable=True),
            ItemEffectProfile(
                effects=(GaugeAdjustEffect(stat=ItemStat.PLEASURE, amount=20),)
            ),
        )
        for entity, slot in ((self.actor, 0), (self.ally, 1)):
            entity.sexual.climax_phase.value = "接近"
            entity.sexual.pleasure.base = 40
            entity.db.inventory = [key]
            with combat_provenance(
                CombatProvenance(
                    engagement_id="hostile:slots:1",
                    round_ordinal=1,
                    slot_ordinal=slot,
                )
            ):
                result = resolve_item_use(
                    ItemUseRequest(entity, key),
                    in_combat=True,
                    context=RoomActionContext(self.room),
                )
            self.assertEqual(result.outcome, "success")

        milestones = list(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__identifier="climax_onset",
            )
        )
        self.assertEqual(
            {m.content["action_source_id"] for m in milestones},
            {
                f"item:combat:hostile:slots:1:r1:s0:{self.actor.pk}:{key}",
                f"item:combat:hostile:slots:1:r1:s1:{self.ally.pk}:{key}",
            },
        )
        for milestone in milestones:
            self.assertEqual(
                milestone.content["encounter_context"]["encounter_id"],
                "hostile:slots:1",
            )
            self.assertEqual(
                NarrativeEvent.objects.filter(
                    event_type="adult_milestone",
                    content__action_source_id=milestone.content["action_source_id"],
                ).count(),
                1,
            )

    @covers_requirement(
        "narrative-events::narrative-facts-commit-atomically-with-covered-gameplay",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_evidence_write_failure_rolls_back_consumption_and_milestones(self):
        """Scenario: Owner rollback removes evidence with the gameplay."""
        from world.narrative.events import record_narrative_event
        from world.rules.clock import get_world_clock

        self.actor.db.inventory = [_GROUP_BLISS_KEY]
        tick_before = int(get_world_clock().tick)

        def failing(**kwargs: Any) -> Any:
            record_narrative_event(**kwargs)
            raise RuntimeError("injected evidence failure")

        with patch("world.narrative.events.record_narrative_event", side_effect=failing):
            with self.assertRaises(RuntimeError):
                use_item(self.actor, _GROUP_BLISS_KEY)

        self.assertEqual(self.actor.db.inventory, [_GROUP_BLISS_KEY])
        self.assertEqual(self.ally.sexual.climax_phase.level, "接近")
        self.assertEqual(int(self.ally.sexual.pleasure.base), 40)
        self.assertEqual(int(get_world_clock().tick), tick_before)
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        self.assertEqual(ProjectionProgress.objects.count(), 0)

