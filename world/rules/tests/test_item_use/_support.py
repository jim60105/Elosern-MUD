"""Synthetic item profiles, fixtures, and shared bases for the `test_item_use` slices.

Module-level fixtures, helpers, and bases moved verbatim from the
original flat module (not a collected test module).
"""

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


class _MultiEffectTestCase(_ItemUseTestCase):
    """Shared registration of the §5 synthetic profiles and immunity prop."""

    def setUp(self):
        super().setUp()
        live_item_registry().update(_SCOPE_MULTI_ITEMS)
        live_item_effect_profiles().update(_SCOPE_MULTI_PROFILES)
