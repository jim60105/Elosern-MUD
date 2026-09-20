"""Shared synthetic game-data kit for behavior tests (add-test-synthetic-data-kit).

One stand-in world: per-catalog dicts built from the REAL definition
dataclasses, keyed with the reserved ``t_`` prefix and carrying invented
Traditional-Chinese display prose, so no kit key or label can ever collide
with a shipped token. The kit is gate-clean BY CONSTRUCTION: this file never
names a shipped catalog symbol or a shipped-content string literally — every
shipped reference goes through ``REGISTRY_TARGETS`` or a runtime lookup by
attribute string, and every display value is invented prose verified disjoint
from the shipped token universe by ``world/tests/test_synthetic_data.py``.

Injection seam (design D2): ``synthetic_registries(...)`` patches the shipped
catalogs for one test/class — ``patch.dict`` (clear+update, in place) for
mutable registries, an attribute swap to a ``MappingProxyType`` for frozen
ones, including every consumer-module binding that name-imported the target
attribute. Consumer bindings are not hand-maintained: an AST discovery pass
enumerates them from the source tree (cached). The lore-sync import-time
capture dict is an explicit target for scopes that invoke ``sync_all()``.

Process scope (design D2b): ``install_synthetic_catalogs()`` applies the same
swap process-wide and idempotently, for the separate managed-browser seed and
server processes that mirror catalogs into a private database at bootstrap.
The browser settings module activates it only under its opt-in flag; the
synthetic-aware seed fixtures and the end-to-end ``t_``-key journey belong to
``migrate-browser-tests-off-real-data``, the kit's first process-scope client.

Local fixtures (design D3): ``make_*`` factories build one synthetic entry
from keyword overrides; tests register them for their own scope through the
``extra=`` argument instead of growing the shared catalogs.

The single-module history is split into modules of a shared surface (the
``world.lore.items`` package precedent applies here): ``vocab`` holds the
runtime-resolved shipped seams and the shared element rows; the ``data_*``
modules each carry contiguous, in-order domain slices of the former catalog
literals (section banners included); ``js_payloads`` carries the JS-mirror
payload table; ``targets`` owns the registry target table and content
factories; ``discovery`` the AST consumer-binding pass; ``patching`` the
scoped ``synthetic_registries`` machinery; ``install`` the process-scoped
install; ``factories`` the ``make_*`` local-fixture helpers.

Every name resolves through this package's namespace exactly as the single
``world/tests/synthetic_data.py`` module exported it: consumers keep
importing ``world.tests.synthetic_data``. Catalog dicts are shared object
identities (the scope machinery patches them in place), never copies.
"""

from __future__ import annotations

import ast
import copy
import functools
import importlib
import unittest.mock
from dataclasses import replace
from collections.abc import Callable, Iterator, Mapping
from contextlib import ContextDecorator, ExitStack
from pathlib import Path
from types import MappingProxyType

from world.lore.anchors import Anchor, AnchorKind
from world.lore.anchor_placement import AnchorPlacement
from world.lore.economy import PriceEntry
from world.lore.elements import Element
from world.lore.guild import GuildBranch, GuildRank
from world.lore.items import (
    ItemDefinition,
    EquipmentModifierKey,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.lore.magic import MagicTier
from world.lore.monsters import MonsterTier
from world.lore.names import FrozenDict, NamePack, NamePart
from world.lore.nations import Nation
from world.lore.npc_tiers import NPCTier
from world.lore.player_presets import PlayerPreset, PresetPersona, StartingCompanion
from world.lore.races import (
    RaceProfile,
    StaticBand,
    StaticTier,
    StatModifiers,
    Subrace,
    Vitals,
)
from world.lore.scene_archetypes import SceneArchetype
from world.lore.sexual_vocab import BODY_PARTS
from world.lore.shops import ShopDefinition
from world.lore.starting_kits import SubraceStartingKit
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
from world.lore.wilderness_regions import WildernessRegion
from world.maps.city_gates import CityGateDef
from world.quests.definitions import (
    KNOWN_GRID_MAP_KEYS,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)
from world.rules.buffs import BuffDefinition
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)
from world.rules.dialogue import DialogueDefinition, KeywordResponse
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.quest_issuance import QuestIssuance, Settlement
from world.skills.cost_tiers import CostTier
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)
from world.skills.sexual_acts._builder import SexualActDef

from world.tests.synthetic_data.vocab import (
    SYNTH_PREFIX,
    _SYNTH_MAP_KEY,
    _shipped_first_element_key,
    _first_equipment_modifier_key,
    _shipped_first_element_row,
    _SYNTH_ELEMENT,
    _SYNTH_ELEMENT_ROW,
    SYNTH_GLOWMIRE_ELEMENT,
    _synth_elements,
)
from world.tests.synthetic_data.data_items import SYNTH_PRICES, SYNTH_ITEMS, SYNTH_ITEM_EFFECT_PROFILES
from world.tests.synthetic_data.data_skills import (
    SYNTH_SKILLS,
    SYNTH_ACT_SKILL,
    SYNTH_ACT,
    SYNTH_ACTS,
    SYNTH_MP_COST_TIERS,
)
from world.tests.synthetic_data.data_characters import (
    SYNTH_RACES,
    SYNTH_STATIC_TIERS,
    SYNTH_SUBRACES,
    SYNTH_STARTING_KITS,
    SYNTH_NPC_TIERS,
    SYNTH_MONSTER_TIERS,
)
from world.tests.synthetic_data.data_world import (
    SYNTH_GUILD_RANKS,
    SYNTH_GUILD_BRANCHES,
    SYNTH_TITLES,
    SYNTH_ANCHORS,
    SYNTH_ANCHOR_PLACEMENTS,
    SYNTH_NATIONS,
    SYNTH_REGIONS,
    SYNTH_WILDERNESS_ENTRIES,
    SYNTH_NAME_PACKS,
    SYNTH_SHOPS,
    SYNTH_CITY_GATES,
    SYNTH_ARCHETYPES,
    SYNTH_DIALOGUE,
    SYNTH_BUFFS,
)
from world.tests.synthetic_data.data_presets_quests import (
    SYNTH_PRESETS,
    SYNTH_QUESTS,
    SYNTH_QUEST_REWARDS,
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_COMMISSIONER_KEY,
    SYNTH_GUILD_ISSUER_KEY,
    _build_issuances,
)
from world.tests.synthetic_data.js_payloads import SYNTH_JS_PAYLOADS
from world.tests.synthetic_data.targets import (
    _content_by_logical,
    _synth_sync_capture,
    REGISTRY_TARGETS,
    _CONTENT,
    _TARGET_DEPENDENCIES,
)
from world.tests.synthetic_data.discovery import (
    _DISCOVERY_ROOTS,
    _DISCOVERY_EXCLUDES,
    _BINDINGS_CACHE,
    _iter_discovery_sources,
    local_import_bindings,
    discover_consumer_bindings,
)
from world.tests.synthetic_data.patching import (
    synthetic_registries,
    _apply_target,
    _late_binder_sweep,
    _consumer_bindings,
    _dependency_order,
    _imported_modules,
)
from world.tests.synthetic_data.install import (
    _INSTALL_STATE,
    _INSTALLED_ATTRS,
    _INSTALL_REPLACEMENTS,
    _INSTALLED_DICTS,
    install_synthetic_catalogs,
    _INSTALLED_DICTS,
    uninstall_synthetic_catalogs,
)
from world.tests.synthetic_data.factories import (
    _derive,
    _dataclass_fields,
    _make,
    make_item,
    make_skill,
    make_price,
    make_npc_tier,
    make_monster_tier,
    make_anchor,
    make_region,
    make_city_gate,
    make_archetype,
    make_price_entry,
    make_shop,
    make_title,
    make_buff,
    make_dialogue,
    make_act,
    make_act_skill,
    make_quest,
    make_preset,
    make_race,
    make_subrace,
    make_static_tier,
    make_nation,
    make_guild_rank,
    make_element,
    make_magic_tier,
    make_name_pack,
    make_wilderness_entry,
    make_wilderness_gate,
    make_quest_reward,
    make_issuance,
    make_cost_tier,
    make_guild_offer,
    make_item_quantity,
    make_objective,
    make_stage,
)

__all__ = [
    "REGISTRY_TARGETS",
    "SYNTH_PREFIX",
    "discover_consumer_bindings",
    "install_synthetic_catalogs",
    "make_*",
    "synthetic_registries",
    "uninstall_synthetic_catalogs",
]
