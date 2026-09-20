"""Slice of ``test_item_use``: JournalIdentityTests, SexualSurfaceRollbackTests."""
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
    _MULTI_KEY,
    _MultiEffectTestCase,
    _PLEASURE_UP_KEY,
    _fixture_item,
)


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
            "world.rules.items.settlement._delete_mirror",
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

    @covers_requirement(
        "lore-item-catalog::a-non-consuming-use-settles-without-spending-the-item"
    )
    def test_non_consuming_use_rollback_restores_all_surfaces_and_inventory(self):
        # Scenario 3: A rolled-back reusable use leaves nothing behind
        from world.rules.item_effects import ItemTargetScope
        reusable_pleasure = _fixture_item("t_reusable_pleasure", consumable=False)
        reusable_profile = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.PLEASURE, amount=30, scope=ItemTargetScope.SELF
                ),
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=20, scope=ItemTargetScope.SELF
                ),
            )
        )
        self.register_fixture(reusable_pleasure, reusable_profile)
        self.hurt(30)
        self.set_pleasure(60)
        self.actor.sexual.wetness.value = 1
        hp_before = int(self.actor.traits.hp.current)
        pleasure_before = self.pleasure()
        wetness_before = self.actor.sexual.wetness.value
        phase_before = self.actor.sexual.climax_phase.level
        self.actor.db.inventory = ["t_reusable_pleasure"]

        from world.rules.items import settlement as items_module
        real_gauge = items_module._apply_gauge_step
        step_count = 0
        def fail_on_second_step(step):
            nonlocal step_count
            step_count += 1
            if step_count > 1:
                raise RuntimeError("mid-settlement failure")
            return real_gauge(step)

        with patch(
            "world.rules.items.settlement._apply_gauge_step",
            side_effect=fail_on_second_step,
        ), self.assertRaises(RuntimeError):
            resolve_item_use(
                ItemUseRequest(self.actor, "t_reusable_pleasure"), in_combat=False
            )

        self.assertEqual(int(self.actor.traits.hp.current), hp_before)
        self.assertEqual(self.pleasure(), pleasure_before)
        self.assertEqual(self.actor.sexual.wetness.value, wetness_before)
        self.assertEqual(self.actor.sexual.climax_phase.level, phase_before)
        self.assertEqual(list_items(self.actor), ["t_reusable_pleasure"])

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
            "world.rules.items.settlement._delete_mirror",
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


class JournalIdentityTests(_MultiEffectTestCase):
    """Design Risks: a record may only be written back to its own entity."""

    def test_crossed_journal_records_are_skipped_with_a_diagnostic(self):
        from world.rules.item_effects import ItemTargetScope
        # Two targets whose gauges differ: a swapped restore would land
        # plausible-but-wrong numbers, so the identity assertion must refuse
        # both crossed records loudly instead of writing either snapshot onto
        # the other entity.
        self._multi = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP,
                    amount=40,
                    scope=ItemTargetScope.ALL,
                ),
            )
        )
        live_item_effect_profiles()[_APPLY_KEY] = self._multi
        self.hurt(30)
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.location = self.actor.location
        self.char2.traits.hp.current = int(self.char2.traits.hp.max) - 60
        self.actor.db.inventory = [_APPLY_KEY]
        preflight = preflight_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertTrue(preflight.allowed)
        targets = [step.target for step in preflight.plan.steps]
        journal = ItemTouchedJournal.capture(self.actor, targets)
        # Write both gauges forward, then cross the journal's entity half by
        # hand — the corruption the identity assertion exists to survive.
        actor_hp_before = int(self.actor.traits.hp.current)
        companion_hp_before = int(self.char2.traits.hp.current)
        self.actor.traits.hp.current += 20
        self.char2.traits.hp.current += 20
        identities = list(journal.entities)
        self.assertEqual(len(identities), 2)
        left, right = identities
        a_record, b_record = journal.entities[left], journal.entities[right]
        journal.entities[left] = replace(a_record, entity=b_record.entity)
        journal.entities[right] = replace(b_record, entity=a_record.entity)
        from world.rules.items import journal as items_module

        warnings: list[dict] = []
        real_warn = items_module.log_warn

        def spy(event, exc=None, context=None):
            warnings.append(context or {})
            return real_warn(event, exc=exc, context=context)

        with patch.object(items_module, "log_warn", spy):
            journal.restore()
        stages = [note.get("stage") for note in warnings]
        self.assertEqual(stages.count("item_journal_identity"), 2, warnings)
        # Neither crossed record was written back: the crossed restore failed
        # loudly instead of landing the other entity's plausible numbers.
        self.assertEqual(int(self.actor.traits.hp.current), actor_hp_before + 20)
        self.assertEqual(int(self.char2.traits.hp.current), companion_hp_before + 20)
