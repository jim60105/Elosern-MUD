"""Catalog loader joining the guild-economy and commerce rulebooks to immutable lore identities (D-1/D-8).

``guild_economy.yaml`` carries merit thresholds, exam opponent profiles and
quest rewards; ``commerce.yaml`` carries assortment offer rules and per-shop
hours (settlement-shops design §3.1). The service-host roster is DERIVED from
the place registry (``world/lore/settlements/places.py``), so a service host
is declared exactly once. This module validates every entry against the
immutable registries and exposes frozen dataclasses, so deterministic APIs
never duplicate balance constants.
"""

from collections.abc import Callable  # noqa: F401  (old namespace name)
from dataclasses import dataclass, replace  # noqa: F401  (old namespace names)
from pathlib import Path  # noqa: F401  (old namespace name)
from typing import TYPE_CHECKING, Any, Mapping

import yaml  # noqa: F401  (old namespace name)

from world.lore.economy import PRICE_TABLE  # noqa: F401  (old namespace name)
from world.lore.guild import GUILD_RANK_REGISTRY  # noqa: F401  (old namespace name)
from world.lore.items import ITEM_REGISTRY  # noqa: F401  (old namespace name)
from world.lore.races import STATIC_TIER_REGISTRY  # noqa: F401  (old namespace name)
from world.lore.settlements.assortments import (  # noqa: F401
    ASSORTMENT_REGISTRY,
    KEEPSAKE_BAND_KEY,
)
from world.lore.settlements.places import PLACE_REGISTRY  # noqa: F401  (old namespace name)
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY  # noqa: F401  (old namespace name)
from world.lore.settlements.shops import SHOP_REGISTRY  # noqa: F401  (old namespace name)
from world.rules.guild_config._catalog import GuildCatalog, register_catalog_offers  # noqa: F401
from world.rules.guild_config._commerce import (  # noqa: F401
    _ASSORTMENT_ROW_FIELDS,
    _OFFER_PRICE_FIELDS,
    _OVERRIDE_ROW_FIELDS,
    _SHOP_SCALE_MAX,
    _SHOP_SCALE_MIN,
    _SHOPS_ROW_FIELDS,
    _parse_shop_overrides,
    _resolve_shop_offers,
    _resolve_shop_scale,
    _scaled_price,
    _validate_overrides_row,
    _validate_resolved_rule,
    validate_assortment_configs,
    validate_price_scales,
)
from world.rules.guild_config._hosts import (  # noqa: F401
    _place_for_shop,
    _require_place_kwargs,
    validate_service_hosts,
)
from world.rules.guild_config._loaders import (  # noqa: F401
    _commerce_error,
    _error,
    _require_int,
    _require_text,
    load_commerce_config,
    load_config,
    validate_exam_profiles,
    validate_merit_thresholds,
)
from world.rules.guild_config._quests import (  # noqa: F401
    validate_guild_offer_side_effect_free,
    validate_quest_rewards,
)
from world.rules.guild_config._shops import validate_shop_configs  # noqa: F401
from world.rules.guild_config._types import (  # noqa: F401
    EXAM_RANKS,
    RANK_ORDER,
    RANK_TO_TIER,
    ExamProfile,
    GuildConfigError,
    ItemOfferRule,
    ServiceHostRow,
    ShopConfig,
)
from world.rules.guild_offers import (  # noqa: F401
    GuildOfferError,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.skills.registry import SKILL_REGISTRY  # noqa: F401  (old namespace name)

if TYPE_CHECKING:
    from world.rules.profession_config import Profession


def load_guild_catalog(definition_registry: Mapping[str, Any]) -> GuildCatalog:
    """Load and validate the complete guild-economy and commerce rulebooks.

    The quest reward section requires the caller's current definition registry;
    every other section validates against immutable lore registries alone.
    """
    raw = load_config()
    commerce = load_commerce_config()
    if "assortments" not in commerce:
        raise _commerce_error("assortments section is required")
    if "shops" not in commerce:
        raise _commerce_error("shops section is required")
    if "price_scales" not in commerce:
        raise _commerce_error("price_scales section is required")
    assortment_offers = validate_assortment_configs(commerce["assortments"])
    price_scales = validate_price_scales(commerce["price_scales"])
    return GuildCatalog(
        merit_thresholds=validate_merit_thresholds(raw["merit_thresholds"]),
        exam_profiles=validate_exam_profiles(raw["exam_profiles"]),
        shop_configs=validate_shop_configs(
            commerce["shops"], assortment_offers, price_scales
        ),
        quest_offers=validate_quest_rewards(raw["quest_rewards"], definition_registry),
        service_hosts=validate_service_hosts(),
    )


CATALOG: GuildCatalog | None = None


def get_catalog() -> GuildCatalog:
    """Return the cached guild-economy catalog, loading it on first use.

    Loading is side-effect free: it never mutates the process-global offer
    registry. Startup registers catalog offers explicitly through
    ``register_catalog_offers``.
    """
    global CATALOG
    if CATALOG is None:
        CATALOG = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
    return CATALOG


def load_catalog_into_cache() -> GuildCatalog:
    """Rebuild ``CATALOG`` against the current quest definition registry.

    Called by ``sync_guild_economy`` after quest synchronization has populated
    ``QUEST_DEFINITION_REGISTRY``; catalog offers are then registered by the
    same composition root.
    """
    global CATALOG
    CATALOG = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
    return CATALOG
