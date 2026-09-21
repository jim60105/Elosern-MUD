"""Data-contract test: guild/shop config validation contract
Shared rulebook readers, the registry-isolation base, and the
synthetic price-shop harness for the ``test_guild_config`` slices.

Module-level fixtures moved verbatim from the original flat module
(not a collected test module).
"""


from tools.spec_traceability import covers_requirement

import unittest
from contextlib import contextmanager
from dataclasses import fields, replace
from pathlib import Path
from unittest import mock

import yaml

from world.lore.economy import PRICE_TABLE, PriceEntry
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import (
    ITEM_REGISTRY,
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
    SUMMARY_MAX,
)
from world.lore.settlements.assortments import ASSORTMENT_REGISTRY, AssortmentDefinition
from world.lore.settlements.places import PLACE_REGISTRY, PlaceDefinition, PlaceKind
from world.lore.settlements.shops import (
    SHOP_REGISTRY,
    ShopDefinition,
    validate_registry_identity_uniqueness,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.catalog import register_catalog
from world.rules.guild_config import (
    CATALOG,
    EXAM_RANKS,
    GuildCatalog,
    GuildConfigError,
    ItemOfferRule,
    ShopConfig,
    load_commerce_config,
    load_guild_catalog,
    validate_assortment_configs,
    validate_exam_profiles,
    validate_merit_thresholds,
    validate_price_scales,
    validate_quest_rewards,
    validate_service_hosts,
    validate_shop_configs,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildOfferError,
    GuildQuestOffer,
    register_guild_offer,
)
from world.skills.equipment import EquipmentSlot
from world.skills.registry import SKILL_REGISTRY


RULEBOOK = Path(__file__).resolve().parents[3] / "rules" / "rulebook" / "guild_economy.yaml"

COMMERCE_DIR = Path(__file__).resolve().parents[3] / "rules" / "rulebook" / "commerce"

class CatalogRegistryIsolation(unittest.TestCase):
    def setUp(self):
        super().setUp()
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        # Snapshot the REAL module cache (the name imported above is a value
        # copy; rebinding it restores nothing).
        import world.rules.guild_config as _guild_config

        self._guild_config_module = _guild_config
        self._catalog = _guild_config.CATALOG
        register_catalog()

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        self._guild_config_module.CATALOG = self._catalog
        super().tearDown()

def raw_rulebook() -> dict:
    return yaml.safe_load(RULEBOOK.read_text(encoding="utf-8"))

def raw_commerce() -> dict:
    return load_commerce_config(COMMERCE_DIR)

def _shipped_scales() -> dict:
    """The shipped price_scales section, validated like catalog load does."""
    return validate_price_scales(raw_commerce()["price_scales"])

def _assortment_row(
    assortment_key: str,
    mutate_offers=None,
) -> list[dict]:
    """Deep-copied shipped assortment rows with one row's offers mutated."""
    rows = raw_commerce()["assortments"]
    out: list[dict] = []
    for row in rows:
        copy = dict(row)
        if copy["key"] == assortment_key:
            offers = [dict(offer) for offer in copy["offers"]]
            if mutate_offers is not None:
                offers = mutate_offers(offers)
            copy["offers"] = offers
        out.append(copy)
    return out

def _price_shop_env(
    *,
    shop_key="t_price_stall",
    place_key="t_price_store",
    assortment_key="t_price_goods",
    item_key="t_price_probe",
    band_key="t_price_band",
    band_min=20,
    band_max=None,
    base_buy=25,
    base_sell=10,
    price_scale=None,
    overrides=(),
    extra_item_keys=(),
    excluded_item_keys=(),
    settlement_key="t_scale_city",
    scales=None,
) -> dict:
    """One synthetic price-scaling shop environment (design §8).

    A single place authoring one shop over one assortment of one item with
    its own price band — everything the scale/override pipeline touches.
    Returns the raw parse inputs (``row``, ``offers``, ``scales``) plus the
    registry rows for ``_price_shop_scope``.
    """
    item = ItemDefinition(
        key=item_key,
        display_name_zh="合成價格探針",
        price_table_key=band_key,
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.TOOL,
            icon_key=ItemIconKey.TOOL,
            rarity=ItemRarity.COMMON,
            summary_zh="合成價格縮放測試物。",
        ),
    )
    band = PriceEntry(band_key, "合成價格頻帶", band_min, band_max, "synthetic probe band")
    assortment = AssortmentDefinition(assortment_key, "合成價格貨架", (item_key,))
    shop = ShopDefinition(
        key=shop_key,
        host_name="合成價格攤主",
        host_title="合成價格攤主",
        assortment_keys=(assortment_key,),
    )
    place = PlaceDefinition(
        key=place_key,
        settlement_key=settlement_key,
        kind=PlaceKind.GENERAL_STORE,
        room_name_zh="合成價格雜貨店",
        room_desc_zh="A synthetic price-scaling store.",
        exterior_xy=(0, 0),
        doorway_key_zh="合成價格入口",
        doorway_aliases=("probe store",),
        host_name="合成價格店主",
        host_title="合成價格雜貨店主",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="t_price_merchant",
        service_id="t_price_merchant",
        assortment_keys=(assortment_key,),
        authored_kwargs=(("shop_key", shop_key),),
        extra_item_keys=extra_item_keys,
        excluded_item_keys=excluded_item_keys,
    )
    row = {"shop_key": shop_key, "open_hour": 8, "close_hour": 20, "restock_hour": 6}
    if price_scale is not None:
        row["price_scale"] = price_scale
    if overrides:
        row["overrides"] = list(overrides)
    offers = {
        assortment_key: {
            item_key: ItemOfferRule(
                item_key=item_key,
                buy_copper=base_buy,
                sell_copper=base_sell,
                max_stock=5,
                initial_stock=2,
                restock_quantity=1,
            )
        }
    }
    return {
        "row": row,
        "offers": offers,
        "scales": {settlement_key: 100} if scales is None else scales,
        "items": {item.key: item},
        "bands": {band.key: band},
        "assortments": {assortment.key: assortment},
        "shops": {shop.key: shop},
        "places": {place.key: place},
    }

@contextmanager
def _price_shop_scope(*envs):
    """Patch the registries for one or more synthetic price-shop environments."""
    items: dict = {}
    bands: dict = {}
    assortments: dict = {}
    shops: dict = {}
    places: dict = {}
    for env in envs:
        items.update(env["items"])
        bands.update(env["bands"])
        assortments.update(env["assortments"])
        shops.update(env["shops"])
        places.update(env["places"])
    with mock.patch.dict(ITEM_REGISTRY, items, clear=False), \
         mock.patch.dict(PRICE_TABLE, bands, clear=False), \
         mock.patch.dict(ASSORTMENT_REGISTRY, assortments, clear=False), \
         mock.patch.dict(SHOP_REGISTRY, shops, clear=True), \
         mock.patch.dict(PLACE_REGISTRY, places, clear=True):
        yield
