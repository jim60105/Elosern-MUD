"""Slice of ``test_item_use``: MultiTargetRollbackTests, TargetResolutionScenarioTests."""
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
    _MultiEffectTestCase,
)


class TargetResolutionScenarioTests(_MultiEffectTestCase):
    """Delta (item-use-resolution): per-effect target resolution scenarios."""

    def _ally(self, ally, *, hp_missing: int) -> None:
        ally.race = "human"
        ally.apply_race_baseline()
        ally.location = self.actor.location
        ally.traits.hp.current = int(ally.traits.hp.max) - hp_missing

    def _third(self, key: str, *, hp_missing: int, location: Any = "room"):
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC

        ally = create_object(NPC, key=key)
        ally.race = "human"
        ally.apply_race_baseline()
        ally.traits.hp.current = int(ally.traits.hp.max) - hp_missing
        if location == "room":
            ally.location = self.actor.location
        else:
            ally.location = None
        return ally

    def _scope(self, stat: ItemStat, amount: int, scope_name: str) -> None:
        from world.rules.item_effects import ItemTargetScope

        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=stat, amount=amount, scope=getattr(ItemTargetScope, scope_name)
                ),
            )
        )

    @covers_requirement(
        "item-use-resolution::item-preflight-resolves-each-effect-s-targets-through-the-shared-resolver"
    )
    def test_dead_single_target_carries_the_resolver_own_reason(self):
        # Delta: "An invalid target reports the resolver's own reason" — the
        # item layer maps to TARGET_INVALID and passes target_dead through as
        # detail verbatim, never a second validator's wording.
        from world.rules.item_effects import ItemTargetScope

        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SINGLE
                ),
            )
        )
        dead = self.char2
        dead.race = "human"
        dead.apply_race_baseline()
        dead.location = self.actor.location
        dead.traits.hp.current = 0
        self.actor.db.inventory = [_APPLY_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY, target=dead), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.TARGET_INVALID)
        self.assertTrue(result.detail.startswith("target_dead"), result.detail)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])
        self.assert_state_unchanged(before)

    def test_own_side_group_scope_needs_no_caller_target(self):
        # Delta: "A group scope needs no caller target" — an ALL_ALLIES use
        # with target=None resolves every eligible member through the context.
        # Out of combat every co-located non-actor is allied, and a character
        # in another room cannot ride along: presence is the resolver's check.
        self._scope(ItemStat.HP, 40, "ALL_ALLIES")
        self.hurt(50)
        self._ally(self.char2, hp_missing=50)
        elsewhere = self._third("t_elsewhere_ally", hp_missing=1, location=None)
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.actor.traits.hp.current), int(self.actor.traits.hp.max) - 10)
        self.assertEqual(int(self.char2.traits.hp.current), int(self.char2.traits.hp.max) - 10)
        self.assertEqual(list_items(self.actor), [])

    def test_out_of_combat_room_resolution_reaches_actor_and_two_companions(self):
        # Delta: "An out-of-combat group scope resolves through the room" —
        # three present entities (the actor included) resolve through the
        # room context because out-of-combat relations carry no hostility.
        self._scope(ItemStat.HP, 40, "ALL")
        self.hurt(50)
        self._ally(self.char2, hp_missing=50)
        third = self._third("t_room_ally_two", hp_missing=50)
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        for entity in (self.actor, self.char2, third):
            self.assertEqual(
                int(entity.traits.hp.current), int(entity.traits.hp.max) - 10
            )
        self.assertEqual(
            sorted(result.event_log.targets),
            sorted([self.actor.key, self.char2.key, third.key]),
        )
        self.assertEqual(list_items(self.actor), [])

    def test_opposing_group_scope_with_no_enemy_rejects_without_consuming(self):
        # Delta: "A group scope with no eligible member rejects" — with no
        # hostility model out of combat, all-enemies has no candidate and the
        # resolver's own empty-area reason arrives as the invalid-target detail.
        self._scope(ItemStat.HP, 40, "ALL_ENEMIES")
        self.hurt(50)
        self._ally(self.char2, hp_missing=50)
        self.actor.db.inventory = [_APPLY_KEY]
        before = self.canonical_state()
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, ItemUseReason.TARGET_INVALID)
        self.assertTrue(
            result.detail.startswith("no_valid_targets_in_area"), result.detail
        )
        self.assert_state_unchanged(before)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])
        self.assertEqual(int(self.char2.traits.hp.current), int(self.char2.traits.hp.max) - 50)

    @covers_requirement(
        "item-use-resolution::item-use-preflight-is-side-effect-free-and-revalidates-current-conditions"
    )
    def test_one_effective_target_among_several_carries_the_whole_use(self):
        # Delta: "One effective target among several carries the whole use" —
        # the group use is eligible on the injured ally alone and settlement
        # writes that ally only; the full-HP members gain no entry.
        self._scope(ItemStat.HP, 40, "ALL")
        self._ally(self.char2, hp_missing=30)
        third = self._third("t_full_ally", hp_missing=0)
        self.actor.traits.hp.current = int(self.actor.traits.hp.max)
        self.actor.db.inventory = [_APPLY_KEY]
        result = resolve_item_use(
            ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
        )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(int(self.char2.traits.hp.current), int(self.char2.traits.hp.max))
        self.assertEqual(int(self.actor.traits.hp.current), int(self.actor.traits.hp.max))
        self.assertEqual(int(third.traits.hp.current), int(third.traits.hp.max))
        (entry,) = result.event_log.entries
        self.assertEqual(entry.target, str(self.char2.key))
        self.assertEqual(result.event_log.targets, (str(self.char2.key),))
        self.assertEqual(list_items(self.actor), [])


class MultiTargetRollbackTests(_MultiEffectTestCase):
    """Design 5.8/D3: the per-entity journal walks every touched target."""

    def test_mid_settlement_fault_after_two_of_four_restores_everyone(self):
        # Delta: "A mid-settlement failure restores every touched entity" —
        # the fault fires once two of the four targets are fully written and
        # a third is mid-pair; every entity's traits, buffs, and sexual
        # surface, plus the actor's inventory and mirror, return to pre-call.
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC
        from world.rules.item_effects import ItemTargetScope

        # Pleasure first so the cascade-wetted intimate surface is written on
        # every entity before the fault fires, mid-way through the buff pair.
        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.PLEASURE, amount=30, scope=ItemTargetScope.ALL
                ),
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.ALL
                ),
                StatusApplyEffect(status="focus", scope=ItemTargetScope.ALL),
            )
        )
        self.hurt(50)
        allies = []
        for index, missing in enumerate((50, 30, 60), start=1):
            ally = create_object(NPC, key=f"t_fall_guy_{index}")
            ally.race = "human"
            ally.apply_race_baseline()
            ally.location = self.actor.location
            ally.traits.hp.current = int(ally.traits.hp.max) - missing
            allies.append(ally)
        # Two entities carry a live sexual surface mid-band (the pleasure
        # cascade writes four values at once) and buffs.
        intimate = [self.actor, allies[1]]
        for entity in intimate:
            entity.sexual.pleasure.base = 60
            entity.sexual.wetness.value = 2
        apply_buff(self.actor, "poisoned")
        apply_buff(allies[0], "poisoned")
        self.actor.db.inventory = [_APPLY_KEY]
        materialize_registry_object(self.actor, _APPLY_KEY)
        mirror_pk = next(
            obj.id
            for obj in self.actor.contents
            if registry_key_for_object(obj) == _APPLY_KEY
        )
        before = {
            "hp": {
                str(e.key): int(e.traits.hp.current)
                for e in (self.actor, *allies)
            },
            "buffs": {
                str(e.key): set(e.attributes.get("buffs", default={}))
                for e in (self.actor, *allies)
            },
            "pleasure": {
                str(e.key): (int(e.sexual.pleasure.base), e.sexual.wetness.level)
                for e in intimate
            },
        }

        from world.rules.items import settlement as items_module

        real_status = items_module._apply_status_step
        applied = {"count": 0}

        def boom(step, item_key):
            # Fail the THIRD focus write: every target's pleasure cascade and
            # HP gauge are already written and two buffs are committed.
            if applied["count"] >= 2:
                raise RuntimeError("settlement boom")
            applied["count"] += 1
            return real_status(step, item_key)

        with patch.object(items_module, "_apply_status_step", boom):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
                )
        self.assertEqual(applied["count"], 2)
        for entity in (self.actor, *allies):
            self.assertEqual(
                int(entity.traits.hp.current), before["hp"][str(entity.key)]
            )
            self.assertEqual(
                set(entity.attributes.get("buffs", default={})),
                before["buffs"][str(entity.key)],
            )
        for entity in intimate:
            self.assertEqual(
                int(entity.sexual.pleasure.base),
                before["pleasure"][str(entity.key)][0],
            )
            self.assertEqual(
                entity.sexual.wetness.level,
                before["pleasure"][str(entity.key)][1],
            )
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])
        self.assertTrue(ObjectDB.objects.filter(pk=mirror_pk).exists())

    def test_rolled_back_companion_reads_pleasure_through_its_handler(self):
        # Delta: "A rolled-back target reads its pre-call state through live
        # handlers" — task 1.2's contract at the rules level: the companion's
        # memoized sexual handler must be dropped by the restore, so the
        # in-process read (NOT an attribute-storage re-read, which passes
        # while the stale handler bug is present) reports the pre-call value.
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC
        from world.rules.item_effects import ItemTargetScope

        live_item_effect_profiles()[_APPLY_KEY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.PLEASURE, amount=30, scope=ItemTargetScope.ALL
                ),
            )
        )
        companion = create_object(NPC, key="t_rollback_companion")
        companion.race = "human"
        companion.apply_race_baseline()
        companion.location = self.actor.location
        self.actor.sexual.pleasure.base = 60
        companion.sexual.pleasure.base = 10
        self.actor.db.inventory = [_APPLY_KEY]
        # Touch both handlers pre-use so both are memoized across settlement.
        self.assertEqual(int(companion.sexual.pleasure.base), 10)
        self.assertEqual(self.pleasure(), 60)
        with patch(
            "world.rules.items.settlement._delete_mirror",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                resolve_item_use(
                    ItemUseRequest(self.actor, _APPLY_KEY), in_combat=False
                )
        self.assertEqual(int(companion.sexual.pleasure.base), 10)
        self.assertEqual(self.pleasure(), 60)
        self.assertEqual(list_items(self.actor), [_APPLY_KEY])
