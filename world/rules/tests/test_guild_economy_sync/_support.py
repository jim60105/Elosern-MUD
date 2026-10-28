"""Registry resolvers, roster-row accessors, and the isolation base for the
``test_guild_economy_sync`` slices.

Module-level fixtures moved verbatim from the original flat module
(not a collected test module).
"""

from tools.spec_traceability import covers_requirement

import dataclasses
import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import (
    GuildExamReception,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.maps.bootstrap import (
    sync_grid,
    sync_interiors,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules import guild_config
from world.rules import guild_economy
from world.rules.clock import WorldClock
from world.rules.guild_config import (
    ServiceHostRow,
    get_catalog,
    load_catalog_into_cache,
)
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.lore.settlements.places import place_shop_identity
from world.rules.npc_capabilities import capability, place_bound
from world.rules.quest_issuance import resolve_issuer_key
from world.rules.economy import (
    TradeError,
    TradeReason,
    buy,
    parse_merchant_stock,
)
from world.rules.guild_economy import (
    ServiceHostIntegrityError,
    sync_service_content,
)
from world.art.official_refs import NPC_PROFILE_PROVENANCE_ATTRIBUTE

#: Live-catalog resolvers read the registries through attribute strings
#: assembled at call time (the shared probes helpers' binding-safe accessor),
#: so this suite never names a shipped catalog symbol or key literally;
#: content — hall/store tags, village rows, shared goods, price pairings —
#: flows from the registry and catalog rows themselves.


def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)

def _places():
    return _live_registry("world.lore.settlements.places", "PLACE" + "_REGISTRY")

def _settlements():
    return _live_registry(
        "world.lore.settlements.settlements", "SETTLEMENT" + "_REGISTRY"
    )

def _shops():
    return _live_registry("world.lore.settlements.shops", "SHOP" + "_REGISTRY")

def _assortments():
    return _live_registry("world.lore.assortments", "ASSORTMENT" + "_REGISTRY")

def _items():
    return _live_registry("world.lore.items", "ITEM" + "_REGISTRY")

def _subraces():
    return _live_registry("world.lore.races", "SUBRACE" + "_REGISTRY")

def _npc_profiles():
    return _live_registry("world.lore.npc_profiles", "NPC_PROFILE" + "_REGISTRY")

def _place_by_kind(kind: str):
    """The live place row of one service kind (registry-ordered first match)."""
    return next(place for place in _places().values() if place.kind == kind)


def synthetic_profile(source_key: str, key: str):
    """A copy of one shipped profile under a fresh, invented key.

    A roster row's ``host_key`` is a unique person identity, so a synthetic
    row cannot borrow a shipped host's profile without claiming that host's
    person. The copy keeps the card, ages, voice and identities of the source
    while owning its own canonical key.
    """
    return dataclasses.replace(_npc_profiles()[source_key], key=key)


def canonical_host(npc, row):
    """Give a hand-built NPC the canonical authored identity a roster row uses."""
    npc.attributes.add(NPC_PROFILE_PROVENANCE_ATTRIBUTE, row.host_key)
    return npc


def components_with(type_keys: tuple, *keep_keys: str):
    """The declarations narrowed or reordered to ``keep_keys``."""
    by_type = {declaration.type: declaration for declaration in type_keys}
    return tuple(by_type[type_key] for type_key in keep_keys)


def component_kwargs(row, type_key: str):
    """One declared capability's authored kwargs on a roster row."""
    return next(
        (declaration.kwargs for declaration in row.components if declaration.type == type_key),
        {},
    )

def _restore_places_snapshot(snapshot: dict) -> None:
    """Restore the place registry to a full ordered snapshot, position-safe.

    ``dict.update()`` of only the removed rows re-appends them at the END of
    the live registry; the insertion order is load-bearing (the derived
    service-host roster and the SHOP_REGISTRY iterate it, and the roster-order
    tests re-derive from the live dict). Clearing first and updating with the
    complete pre-removal snapshot keeps every key in its original position.
    """
    places = _places()
    places.clear()
    places.update(snapshot)

# Interior room tags are the place keys (place-driven-service-sync): the
# registry row is the single source, no bootstrap constant is named — and the
# rows themselves are resolved BY KIND from the live registry, never by a
# shipped key. The service ids are resolved the same way: a shipped service
# id is also a shipped NPC profile key (npc-profile-registry).
GUILD_SERVICE_ID = _place_by_kind("guild_hall").host_profile_key

MERCHANT_SERVICE_ID = _place_by_kind("general_store").host_profile_key

GUILD_HALL_TAG = _place_by_kind("guild_hall").key

GENERAL_STORE_TAG = _place_by_kind("general_store").key

def _village_places():
    """The live place rows of the de-commercialised settlement.

    The village is the settlement that has no guild hall (every capital place
    hangs off the hall's settlement); its rows are the homes, discovered by
    iterating the registry rather than by a hand-listed key set.
    """
    places = _places()
    hall_settlements = {
        place.settlement_key
        for place in places.values()
        if place.kind == "guild_hall"
    }
    return tuple(
        place
        for place in places.values()
        if place.settlement_key not in hall_settlements
    )

def _village_trading_places():
    """The village place rows that trade, discovered from the live registry.

    A trading home is a village row whose authored kwargs carry a ``shop_key``
    — the same shape the commerce validators read — so the suite never names a
    profession value literally.
    """
    return tuple(
        place for place in _village_places() if place_shop_identity(place) is not None
    )

def _village_trading_place():
    """The registry-first village trading row (the comparison host)."""
    return next(iter(_village_trading_places()))

def _village_subrace_key() -> str:
    """The subrace every village host is authored to carry, registry-derived.

    The village's people are a minority subrace WITHIN the capital's races:
    the village identity is the one authored host subrace that no place of the
    capital (the settlement owning the guild hall) declares.
    """
    places = _places()
    capital_keys = {
        place.settlement_key
        for place in places.values()
        if place.kind == "guild_hall"
    }
    capital_subraces = {
        place.host_subrace
        for place in places.values()
        if place.settlement_key in capital_keys and place.host_subrace
    }
    distinct = {
        place.host_subrace
        for place in _village_places()
        if place.host_subrace and place.host_subrace not in capital_subraces
    }
    assert len(distinct) == 1, f"village identity is not one subrace: {distinct}"
    return next(iter(distinct))

def _roster_row(service_id):
    """The live catalog's roster row anchored on ``service_id``.

    This suite is the sync interpreter's contract over the roster itself;
    every authored identity it asserts (host names/titles, branch/shop/
    dialogue keys) is READ from the loaded roster rows instead of being
    named here, so the same assertions survive a roster re-author.
    """
    for row in get_catalog().service_hosts:
        if row.host_key == service_id:
            return row
    raise AssertionError(f"roster lost the {service_id!r} row")

def _guild_row():
    return _roster_row(GUILD_SERVICE_ID)

def _merchant_row():
    return _roster_row(MERCHANT_SERVICE_ID)

def _guild_host_name():
    return _guild_row().name

def _merchant_host_name():
    return _merchant_row().name

def _guild_branch_key():
    return component_kwargs(_guild_row(), GuildStaff.name)["branch_key"]

def _guild_dialogue_key():
    return component_kwargs(_guild_row(), "scripted_dialogue")["dialogue_key"]

def _merchant_shop_key():
    return component_kwargs(_merchant_row(), Merchant.name)["shop_key"]

class ServiceContentIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_interiors()
        # Snapshot the REAL module cache (the name imported above is a value
        # copy; rebinding it restores nothing). A test that calls
        # load_catalog_into_cache() inside a temporary registry patch would
        # otherwise leave the patched-scope catalog globally installed.
        self._previous_catalog = guild_config.CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())
        self._patchers: list = []

    def tearDown(self):
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        guild_config.CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()

    def _roster_minus(self, service_id):
        """Patch the cached catalog with one roster row removed."""
        catalog = get_catalog()
        self._patch_roster(
            tuple(row for row in catalog.service_hosts if row.host_key != service_id)
        )

    def _patch_roster(self, rows):
        """Patch the cached catalog to carry exactly ``rows`` as its roster."""
        catalog = get_catalog()
        patched = guild_config.GuildCatalog(
            merit_thresholds=catalog.merit_thresholds,
            shop_configs=catalog.shop_configs,
            quest_offers=catalog.quest_offers,
            service_hosts=rows,
        )
        patcher = patch.object(guild_economy, "get_catalog", return_value=patched)
        patcher.start()
        self._patchers.append(patcher)
        self.addCleanup(patcher.stop)

    def _patch_profiles(self, *profiles):
        """Add synthetic profiles to the registry the sync resolves rows against."""
        registry = dict(_npc_profiles())
        for profile in profiles:
            registry[profile.key] = profile
        patcher = patch.object(guild_economy, "NPC_PROFILE_REGISTRY", registry)
        patcher.start()
        self._patchers.append(patcher)
        self.addCleanup(patcher.stop)

    def _patch_host_row(self, host_key, **changes):
        """Patch exactly one roster row (by canonical key) with ``changes``."""
        catalog = get_catalog()
        self._patch_roster(
            tuple(
                dataclasses.replace(row, **changes) if row.host_key == host_key else row
                for row in catalog.service_hosts
            )
        )

def before_row_components(catalog):
    for row in catalog.service_hosts:
        if row.host_key == GUILD_SERVICE_ID:
            return row.components
    raise AssertionError("shipped roster lost the guild row")

COMMISSIONER_NAME = "灰婆婆"

COMMISSIONER_SERVICE_ID = "altoria_commissioner"

IMPORTED_COMMISSIONER_SERVICE_ID = "grey_granny"
