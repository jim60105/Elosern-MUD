"""Catalog loader joining the guild-economy and commerce rulebooks to immutable lore identities (D-1/D-8).

``guild_economy.yaml`` carries merit thresholds, exam opponent profiles and
quest rewards; ``commerce.yaml`` carries assortment offer rules and per-shop
hours (settlement-shops design §3.1). The service-host roster is DERIVED from
the place registry (``world/lore/settlements/places.py``), so a service host
is declared exactly once. This module validates every entry against the
immutable registries and exposes frozen dataclasses, so deterministic APIs
never duplicate balance constants.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import yaml

from world.lore.economy import PRICE_TABLE
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.races import STATIC_TIER_REGISTRY
from world.lore.settlements.assortments import (
    ASSORTMENT_REGISTRY,
    KEEPSAKE_BAND_KEY,
)
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
from world.lore.settlements.shops import SHOP_REGISTRY
from world.rules.guild_offers import (
    GuildOfferError,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.skills.registry import SKILL_REGISTRY

if TYPE_CHECKING:
    from world.rules.profession_config import Profession


class GuildConfigError(ValueError):
    """The guild-economy rulebook violates the immutable-contract load rules."""


RANK_ORDER = tuple(rank.key for rank in sorted(GUILD_RANK_REGISTRY.values(), key=lambda r: r.order))
EXAM_RANKS = ("E", "D", "C", "B", "A", "S")
RANK_TO_TIER = {
    "E": "human_adventurer",
    "D": "human_adventurer",
    "C": "human_elite",
    "B": "human_elite",
    "A": "human_veteran",
    "S": "human_swordmaster",
}


@dataclass(frozen=True)
class ExamProfile:
    """The deterministic opponent used by one target-rank guild examination."""

    target_rank: str
    static_tier_key: str
    hp: int
    mp: int
    sp: int
    atk_phys: int
    agility: int
    defense: int
    magic_power: int
    skills: tuple[str, ...]


@dataclass(frozen=True)
class ItemOfferRule:
    """Exact integer trade and stock rules for one offered item."""

    item_key: str
    buy_copper: int
    sell_copper: int
    max_stock: int
    initial_stock: int
    restock_quantity: int


@dataclass(frozen=True)
class ShopConfig:
    """Validated opening-hour and offer rules for one shop.

    ``display_name_zh`` is the owning place's authored room name, populated
    during shop resolution so the player-facing listing can name the shop.
    """

    shop_key: str
    display_name_zh: str
    open_hour: int
    close_hour: int
    restock_hour: int
    offers: tuple[ItemOfferRule, ...]


@dataclass(frozen=True)
class ServiceHostRow:
    """One declarative service-host roster row (declarative-service-hosts D7).

    ``profession`` is the RESOLVED registry row, not a key: sync executes the
    exact row config validation approved, so a rulebook reload between config
    load and sync can never mix blueprints (the change-2 snapshot decision).
    ``authored_kwargs`` holds the row's flat identity kwargs (``shop_key`` /
    ``branch_key`` / ``dialogue_key``); the shared assembly helper projects
    them per blueprint component.
    """

    name: str
    title: str
    profession: "Profession"
    anchor_room: str
    service_id: str
    authored_kwargs: "Mapping[str, str]"


def _error(message: str) -> GuildConfigError:
    return GuildConfigError(f"guild_economy.yaml: {message}")


def _commerce_error(message: str) -> GuildConfigError:
    return GuildConfigError(f"commerce.yaml: {message}")


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{field} must be a non-empty string")
    return value


def _require_int(
    value: Any,
    field: str,
    *,
    minimum: int | None = None,
    raise_error: Callable[[str], GuildConfigError] = _error,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise raise_error(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise raise_error(f"{field} must be at least {minimum}")
    return value


def load_config() -> dict[str, Any]:
    raw = yaml.safe_load(
        (Path(__file__).parent / "rulebook" / "guild_economy.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    return dict(raw)


def load_commerce_config() -> dict[str, Any]:
    raw = yaml.safe_load(
        (Path(__file__).parent / "rulebook" / "commerce.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise _commerce_error("rulebook must be a mapping")
    return dict(raw)


def validate_merit_thresholds(raw: Mapping[str, Any]) -> dict[str, int]:
    """Require strictly increasing non-negative E-through-S thresholds."""
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"merit_thresholds missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"merit_thresholds has unknown ranks {sorted(unknown)}")
    values = {
        rank: _require_int(raw[rank], f"merit_thresholds.{rank}", minimum=0)
        for rank in EXAM_RANKS
    }
    for lower_rank, upper_rank in zip(EXAM_RANKS, EXAM_RANKS[1:]):
        if not values[lower_rank] < values[upper_rank]:
            raise _error(
                f"merit_thresholds must be strictly increasing: "
                f"{lower_rank}={values[lower_rank]} is not below "
                f"{upper_rank}={values[upper_rank]}"
            )
    return values


def validate_exam_profiles(raw: Mapping[str, Any]) -> dict[str, ExamProfile]:
    """Validate every target-rank profile against its required lore band."""
    if not isinstance(raw, Mapping):
        raise _error("exam_profiles must be a mapping")
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"exam_profiles missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"exam_profiles has unknown ranks {sorted(unknown)}")

    profiles: dict[str, ExamProfile] = {}
    for rank in EXAM_RANKS:
        entry = raw[rank]
        if not isinstance(entry, Mapping):
            raise _error(f"exam_profiles.{rank} must be a mapping")
        static_tier_key = entry.get("static_tier")
        if static_tier_key != RANK_TO_TIER[rank]:
            raise _error(
                f"exam_profiles.{rank} must use tier {RANK_TO_TIER[rank]!r}, "
                f"got {static_tier_key!r}"
            )
        tier = STATIC_TIER_REGISTRY[static_tier_key]
        if tier.race_key != "human":
            raise _error(f"exam_profiles.{rank} tier must belong to the human race")
        physical = {
            axis: _require_int(
                entry.get(axis), f"exam_profiles.{rank}.{axis}", minimum=0
            )
            for axis in ("atk_phys", "agility", "defense")
        }
        band = tier.band
        band_floor, band_ceiling = band
        for axis, value in physical.items():
            if not band_floor <= value <= (band_ceiling if band_ceiling is not None else value):
                raise _error(
                    f"exam_profiles.{rank}.{axis}={value} is outside tier "
                    f"{static_tier_key!r} band {(band_floor, band_ceiling)}"
                )
        skills = entry.get("skills")
        if not isinstance(skills, list) or not skills:
            raise _error(f"exam_profiles.{rank}.skills must be a non-empty list")
        if any(not isinstance(key, str) or key not in SKILL_REGISTRY for key in skills):
            raise _error(f"exam_profiles.{rank} references an unknown skill key")
        profiles[rank] = ExamProfile(
            target_rank=rank,
            static_tier_key=static_tier_key,
            hp=_require_int(entry.get("hp"), f"exam_profiles.{rank}.hp", minimum=1),
            mp=_require_int(entry.get("mp"), f"exam_profiles.{rank}.mp", minimum=0),
            sp=_require_int(entry.get("sp"), f"exam_profiles.{rank}.sp", minimum=0),
            atk_phys=physical["atk_phys"],
            agility=physical["agility"],
            defense=physical["defense"],
            magic_power=_require_int(
                entry.get("magic_power"), f"exam_profiles.{rank}.magic_power", minimum=0
            ),
            skills=tuple(skills),
        )
    return profiles


_ASSORTMENT_ROW_FIELDS = frozenset({"key", "offers"})
_SHOPS_ROW_FIELDS = frozenset(
    {"shop_key", "open_hour", "close_hour", "restock_hour", "price_scale", "overrides"}
)
_SHOP_SCALE_MIN = 1
_SHOP_SCALE_MAX = 1000
_OVERRIDE_ROW_FIELDS = frozenset(
    {"item_key", "buy_copper", "sell_copper", "max_stock", "initial_stock", "restock_quantity"}
)
_OFFER_PRICE_FIELDS = frozenset(
    {"buy_copper", "sell_copper", "max_stock", "initial_stock", "restock_quantity"}
)


def validate_assortment_configs(raw: Any) -> dict[str, dict[str, ItemOfferRule]]:
    """Join YAML assortment offers to immutable AssortmentDefinition identities.

    Every item/offer alignment, money, band, stock and keepsake rejection the
    old per-shop join enforced is now evaluated once per assortment, however
    many shops reference it. An assortment SHALL NOT declare hours, a host or
    a location, so stray fields are rejected. Prices are validated as exact
    integers here; the band containment, sell-not-above-buy and
    non-negative checks run against the RESOLVED values at shop resolution
    (place-price-scaling §4), because scaling is what a player is charged.
    Returns ``assortment_key -> {item_key: ItemOfferRule}`` in YAML offer order.
    """
    if not isinstance(raw, list):
        raise _commerce_error("assortments must be a list")
    validated: dict[str, dict[str, ItemOfferRule]] = {}
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _commerce_error(f"assortments[{position}] must be a mapping")
        unknown_fields = set(entry) - _ASSORTMENT_ROW_FIELDS
        if unknown_fields:
            raise _commerce_error(
                f"assortments[{position}] has unknown field(s) {sorted(unknown_fields)}"
            )
        assortment_key = entry.get("key")
        definition = ASSORTMENT_REGISTRY.get(assortment_key)
        if definition is None:
            raise _commerce_error(
                f"assortments[{position}].key {assortment_key!r} is unknown"
            )
        if assortment_key in validated:
            raise _commerce_error(
                f"duplicate assortment_key {assortment_key!r} in assortments"
            )
        item_set = set(definition.item_keys)
        for item_key in definition.item_keys:
            if item_key not in ITEM_REGISTRY:
                raise _commerce_error(
                    f"assortments.{assortment_key}.item_keys contains unknown item_key {item_key!r}"
                )
            if ITEM_REGISTRY[item_key].price_table_key == KEEPSAKE_BAND_KEY:
                raise _commerce_error(
                    f"assortments.{assortment_key} contains keepsake-band item "
                    f"{item_key!r}: the {KEEPSAKE_BAND_KEY!r} band is never traded"
                )
        offers_entry = entry.get("offers")
        if not isinstance(offers_entry, list):
            raise _commerce_error(f"assortments.{assortment_key}.offers must be a list")
        offers: dict[str, ItemOfferRule] = {}
        seen_items: set[str] = set()
        for offer_position, offer in enumerate(offers_entry, start=1):
            if not isinstance(offer, Mapping):
                raise _commerce_error(
                    f"assortments.{assortment_key}.offers[{offer_position}] must be a mapping"
                )
            item_key = offer.get("item_key")
            if item_key not in ITEM_REGISTRY:
                raise _commerce_error(
                    f"assortments.{assortment_key}.offers[{offer_position}].item_key "
                    f"{item_key!r} is unknown"
                )
            if item_key not in item_set:
                raise _commerce_error(
                    f"assortments.{assortment_key}.offers includes {item_key!r} which is "
                    f"not offered by AssortmentDefinition {assortment_key!r}"
                )
            if item_key in seen_items:
                raise _commerce_error(
                    f"duplicate offered item {item_key!r} in assortment {assortment_key!r}"
                )
            seen_items.add(item_key)
            buy_copper = _require_int(
                offer.get("buy_copper"),
                f"assortments.{assortment_key}.{item_key}.buy_copper",
                raise_error=_commerce_error,
            )
            sell_copper = _require_int(
                offer.get("sell_copper"),
                f"assortments.{assortment_key}.{item_key}.sell_copper",
                raise_error=_commerce_error,
            )
            price_entry = PRICE_TABLE.get(ITEM_REGISTRY[item_key].price_table_key)
            if price_entry is None:
                raise _commerce_error(
                    f"assortments.{assortment_key}.{item_key} has no price-table entry"
                )
            max_stock = _require_int(
                offer.get("max_stock"),
                f"assortments.{assortment_key}.{item_key}.max_stock",
                minimum=1,
                raise_error=_commerce_error,
            )
            initial_stock = _require_int(
                offer.get("initial_stock"),
                f"assortments.{assortment_key}.{item_key}.initial_stock",
                minimum=0,
                raise_error=_commerce_error,
            )
            if initial_stock > max_stock:
                raise _commerce_error(
                    f"assortments.{assortment_key}.{item_key}: initial_stock "
                    f"{initial_stock} exceeds max_stock {max_stock}"
                )
            restock_quantity = _require_int(
                offer.get("restock_quantity"),
                f"assortments.{assortment_key}.{item_key}.restock_quantity",
                minimum=1,
                raise_error=_commerce_error,
            )
            offers[item_key] = ItemOfferRule(
                item_key=item_key,
                buy_copper=buy_copper,
                sell_copper=sell_copper,
                max_stock=max_stock,
                initial_stock=initial_stock,
                restock_quantity=restock_quantity,
            )
        missing = item_set - seen_items
        if missing:
            raise _commerce_error(
                f"assortments.{assortment_key} is missing offers for {sorted(missing)}"
            )
        validated[assortment_key] = offers
    missing_assortments = set(ASSORTMENT_REGISTRY) - set(validated)
    if missing_assortments:
        raise _commerce_error(
            f"assortments is missing rules for {sorted(missing_assortments)}"
        )
    return validated


def validate_price_scales(raw: Any) -> dict[str, int]:
    """Validate the ``price_scales:`` section of commerce.yaml (design §4).

    The section is keyed by settlement, and each value is an integer
    percentage in ``1..1000`` where ``100`` is par. A settlement may be
    declared at par only explicitly — ``100`` is an authored value, not a
    silent fallback. An unknown settlement key, a non-integer scale, or a
    scale outside the bounded range each fail catalog load naming the
    declaring settlement.
    """
    if not isinstance(raw, Mapping):
        raise _commerce_error("price_scales must be a mapping")
    scales: dict[str, int] = {}
    for settlement_key, scale in raw.items():
        if settlement_key not in SETTLEMENT_REGISTRY:
            raise _commerce_error(
                f"price_scales names unknown settlement {settlement_key!r}"
            )
        if settlement_key in scales:
            raise _commerce_error(
                f"duplicate settlement {settlement_key!r} in price_scales"
            )
        value = _require_int(
            scale,
            f"price_scales.{settlement_key}",
            minimum=_SHOP_SCALE_MIN,
            raise_error=_commerce_error,
        )
        if value > _SHOP_SCALE_MAX:
            raise _commerce_error(
                f"price_scales.{settlement_key} scale {value} must be at most "
                f"{_SHOP_SCALE_MAX}"
            )
        scales[str(settlement_key)] = value
    return scales


def _scaled_price(base_copper: int, scale: int) -> int:
    """Half-up rounding ``(base * scale + 50) // 100`` — exact integer copper.

    Precondition: ``scale`` was already validated in 1..1000 by the caller
    (``validate_price_scales`` / ``_resolve_scale``); this helper stays a bare
    integer multiply with no float entering the copper path.
    """
    return (base_copper * scale + 50) // 100


def _authoring_place(shop_key: str):
    """The place registry row that authors ``shop_key`` (design §3.2).

    SHOP_REGISTRY is a projection of PLACE_REGISTRY: every shop identity is
    authored on exactly one place. A commerce row whose shop_key no place
    authors is unreachable in production and fails closed here, so a
    place-level operation (scale, additions, removals) always has a row to
    resolve against.
    """
    for place in PLACE_REGISTRY.values():
        if dict(place.authored_kwargs).get("shop_key") == shop_key:
            return place
    raise _commerce_error(f"shops.{shop_key} is authored by no place registry row")


def _resolve_shop_scale(
    shop_key: str, entry: Mapping[str, Any], place: Any, price_scales: Mapping[str, int]
) -> int:
    """The effective integer scale for one shop (design §4).

    A shop row's own ``price_scale`` overrides its settlement's entry; a shop
    whose settlement declares no scale fails load naming the settlement and
    the place, because a silent par would hide an authoring gap.
    """
    declared = entry.get("price_scale")
    if declared is not None:
        scale = _require_int(
            declared,
            f"shops.{shop_key}.price_scale",
            minimum=_SHOP_SCALE_MIN,
            raise_error=_commerce_error,
        )
        if scale > _SHOP_SCALE_MAX:
            raise _commerce_error(
                f"shops.{shop_key} price_scale {scale} must be at most {_SHOP_SCALE_MAX}"
            )
        return scale
    scale = price_scales.get(place.settlement_key)
    if scale is None:
        raise _commerce_error(
            f"shops.{shop_key} (place {place.key!r}) has no price_scales entry "
            f"for settlement {place.settlement_key!r}"
        )
    return scale


def _validate_overrides_row(
    shop_key: str, position: int, row: Any, place: Any
) -> ItemOfferRule:
    """One complete-or-rejected override row, wholly replacing an offer rule."""
    what = f"shops.{shop_key} (place {place.key!r}) overrides[{position}]"
    if not isinstance(row, Mapping):
        raise _commerce_error(f"{what} must be a mapping")
    unknown_fields = set(row) - _OVERRIDE_ROW_FIELDS
    if unknown_fields:
        raise _commerce_error(f"{what} has unknown field(s) {sorted(unknown_fields)}")
    item_key = row.get("item_key")
    if item_key is None or item_key not in ITEM_REGISTRY:
        raise _commerce_error(
            f"shops.{shop_key} (place {place.key!r}) override {item_key!r} "
            "must name a known item"
        )
    missing_fields = sorted(_OFFER_PRICE_FIELDS - set(row))
    if missing_fields:
        raise _commerce_error(
            f"shops.{shop_key} (place {place.key!r}) override for {item_key!r} "
            f"is missing field(s) {missing_fields}"
        )
    buy_copper = _require_int(
        row.get("buy_copper"),
        f"{what}.{item_key}.buy_copper",
        raise_error=_commerce_error,
    )
    sell_copper = _require_int(
        row.get("sell_copper"),
        f"{what}.{item_key}.sell_copper",
        raise_error=_commerce_error,
    )
    max_stock = _require_int(
        row.get("max_stock"),
        f"{what}.{item_key}.max_stock",
        minimum=1,
        raise_error=_commerce_error,
    )
    initial_stock = _require_int(
        row.get("initial_stock"),
        f"{what}.{item_key}.initial_stock",
        minimum=0,
        raise_error=_commerce_error,
    )
    if initial_stock > max_stock:
        raise _commerce_error(
            f"{what}.{item_key}: initial_stock {initial_stock} exceeds "
            f"max_stock {max_stock}"
        )
    restock_quantity = _require_int(
        row.get("restock_quantity"),
        f"{what}.{item_key}.restock_quantity",
        minimum=1,
        raise_error=_commerce_error,
    )
    return ItemOfferRule(
        item_key=item_key,
        buy_copper=buy_copper,
        sell_copper=sell_copper,
        max_stock=max_stock,
        initial_stock=initial_stock,
        restock_quantity=restock_quantity,
    )


def _validate_resolved_rule(shop_key: str, place: Any, rule: ItemOfferRule) -> None:
    """Rejections run against the RESOLVED value a player is charged (design §4)."""
    what = f"shops.{shop_key} (place {place.key!r}) item {rule.item_key!r}"
    if rule.buy_copper < 0 or rule.sell_copper < 0:
        raise _commerce_error(
            f"{what} resolved price must be a non-negative integer, "
            f"got buy {rule.buy_copper} sell {rule.sell_copper}"
        )
    if rule.sell_copper > rule.buy_copper:
        raise _commerce_error(
            f"{what}: resolved sell_copper {rule.sell_copper} exceeds "
            f"resolved buy_copper {rule.buy_copper}"
        )
    price_entry = PRICE_TABLE.get(ITEM_REGISTRY[rule.item_key].price_table_key)
    if price_entry is None:
        raise _commerce_error(f"{what} has no price-table entry")
    band_floor, band_ceiling = price_entry.min_copper, price_entry.max_copper
    if not band_floor <= rule.buy_copper <= (
        band_ceiling if band_ceiling is not None else rule.buy_copper
    ):
        raise _commerce_error(
            f"{what} resolved buy_copper {rule.buy_copper} is "
            f"outside price-table band {(band_floor, band_ceiling)}"
        )


def _parse_shop_overrides(
    entry: Mapping[str, Any], shop_key: str, place: Any
) -> dict[str, ItemOfferRule]:
    """Parse a shop row's ``overrides:`` list into item-keyed rules.

    Every override row is complete or rejected: all five offer fields, else
    a load error naming the place, the item and the missing fields. Two
    rows for one item, or a row naming an unknown item, also fail closed.
    """
    raw_overrides = entry.get("overrides")
    if raw_overrides is None:
        return {}
    if not isinstance(raw_overrides, list):
        raise _commerce_error(f"shops.{shop_key}.overrides must be a list")
    overrides: dict[str, ItemOfferRule] = {}
    for position, row in enumerate(raw_overrides, start=1):
        item_key = row.get("item_key") if isinstance(row, Mapping) else None
        rule = _validate_overrides_row(shop_key, position, row, place)
        if item_key in overrides:
            raise _commerce_error(
                f"shops.{shop_key} (place {place.key!r}) overrides "
                f"{item_key!r} more than once"
            )
        overrides[item_key] = rule
    return overrides


def _resolve_shop_offers(
    shop: Any,
    place: Any,
    overrides: dict[str, ItemOfferRule],
    assortment_offers: Mapping[str, Mapping[str, ItemOfferRule]],
    scale: int,
) -> tuple[ItemOfferRule, ...]:
    """Resolve one shop's final offers: additions, removals, scale, overrides.

    Offered goods are the assortment union plus the place's additions minus
    its removals (design §3.2). Every override must name an item the place
    offers, and every addition must carry a complete override — both
    directions fail load naming the place and the item. A base rule is used
    either verbatim (overridden) or scaled once with half-up rounding; an
    override is absolute and is never scaled.
    """
    what = f"place {place.key!r} (shop {shop.key!r})"
    assortment_items = set(shop.offered_item_keys)
    excluded = set(place.excluded_item_keys)
    for item_key in excluded:
        if item_key not in assortment_items:
            raise _commerce_error(
                f"{what} excludes {item_key!r} which no referenced "
                "assortment contains"
            )
    extras = set(place.extra_item_keys)
    for item_key in extras:
        if item_key in assortment_items:
            raise _commerce_error(
                f"{what} adds {item_key!r} which a referenced assortment "
                "already offers"
            )
        if item_key not in overrides:
            raise _commerce_error(
                f"{what} adds {item_key!r} without a complete override"
            )
    offered = (assortment_items - excluded) | extras
    for item_key in overrides:
        if item_key not in offered:
            raise _commerce_error(
                f"{what} overrides {item_key!r} which the place does not offer"
            )
    resolved: list[ItemOfferRule] = []
    for assortment_key in shop.assortment_keys:
        for base in assortment_offers[assortment_key].values():
            if base.item_key in excluded:
                continue
            if base.item_key in overrides:
                resolved.append(overrides[base.item_key])
            else:
                resolved.append(
                    replace(
                        base,
                        buy_copper=_scaled_price(base.buy_copper, scale),
                        sell_copper=_scaled_price(base.sell_copper, scale),
                    )
                )
    for item_key in place.extra_item_keys:
        resolved.append(overrides[item_key])
    return tuple(resolved)


def validate_shop_configs(
    raw: Any,
    assortment_offers: Mapping[str, Mapping[str, ItemOfferRule]],
    price_scales: Mapping[str, int],
) -> dict[str, ShopConfig]:
    """Resolve the ``shops:`` section of commerce.yaml against assortments.

    A shop's offered goods are the union of its referenced assortments'
    validated offer rules, plus the owning place's additions minus its
    removals, priced as either a complete absolute override or one half-up
    scaling of the base (place-price-scaling §4). Every price rejection
    runs against the RESOLVED value a player would be charged. The
    shops-completeness accounting is keyed on shop identity rather than a
    component-type field, so a shop whose rule row is absent is named no
    matter how many shops the registry carries (§1.1).
    """
    if not isinstance(raw, list):
        raise _commerce_error("shops must be a list")
    configs: dict[str, ShopConfig] = {}
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _commerce_error(f"shops[{position}] must be a mapping")
        unknown_fields = set(entry) - _SHOPS_ROW_FIELDS
        if unknown_fields:
            raise _commerce_error(
                f"shops[{position}] has unknown field(s) {sorted(unknown_fields)} "
                f"(offers moved to the assortments section)"
            )
        shop_key = entry.get("shop_key")
        if shop_key not in SHOP_REGISTRY:
            raise _commerce_error(f"shops[{position}].shop_key {shop_key!r} is unknown")
        if shop_key in configs:
            raise _commerce_error(f"duplicate shop_key {shop_key!r} in shops")
        shop = SHOP_REGISTRY[shop_key]
        if not shop.assortment_keys:
            raise _commerce_error(f"shops.{shop_key} references no assortments")
        if len(set(shop.assortment_keys)) != len(shop.assortment_keys):
            for assortment_key in shop.assortment_keys:
                if shop.assortment_keys.count(assortment_key) > 1:
                    break
            raise _commerce_error(
                f"shops.{shop_key} references assortment {assortment_key!r} more than once"
            )
        for assortment_key in shop.assortment_keys:
            if assortment_key not in ASSORTMENT_REGISTRY:
                raise _commerce_error(
                    f"shops.{shop_key} references unknown assortment {assortment_key!r}"
                )
        missing_rules = set(shop.assortment_keys) - set(assortment_offers)
        if missing_rules:
            raise _commerce_error(
                f"shops.{shop_key} has no offer rules for assortment(s) "
                f"{sorted(missing_rules)}"
            )
        # Per-shop overlap rejection: two referenced assortments both
        # containing one key would leave the resolver picking a price by an
        # unstated precedence rule (design §3.1).
        owner_by_item: dict[str, str] = {}
        for assortment_key in shop.assortment_keys:
            for item_key in ASSORTMENT_REGISTRY[assortment_key].item_keys:
                previous = owner_by_item.get(item_key)
                if previous is not None and previous != assortment_key:
                    raise _commerce_error(
                        f"shops.{shop_key} offers {item_key!r} through more than one "
                        f"assortment: {previous!r}, {assortment_key!r}"
                    )
                owner_by_item[item_key] = assortment_key
        from world.rules.clock import CLOCK_YAML

        hours_per_day = int(CLOCK_YAML["hours_per_day"])
        open_hour = _require_int(
            entry.get("open_hour"),
            f"shops.{shop_key}.open_hour",
            minimum=0,
            raise_error=_commerce_error,
        )
        close_hour = _require_int(
            entry.get("close_hour"),
            f"shops.{shop_key}.close_hour",
            minimum=0,
            raise_error=_commerce_error,
        )
        restock_hour = _require_int(
            entry.get("restock_hour"),
            f"shops.{shop_key}.restock_hour",
            minimum=0,
            raise_error=_commerce_error,
        )
        for label, hour in (
            ("open_hour", open_hour),
            ("close_hour", close_hour),
            ("restock_hour", restock_hour),
        ):
            if hour >= hours_per_day:
                raise _commerce_error(
                    f"shops.{shop_key}.{label}={hour} must be below "
                    f"hours_per_day={hours_per_day}"
                )
        if open_hour == close_hour:
            raise _commerce_error(f"shops.{shop_key} open and close hours cannot be equal")
        place = _authoring_place(shop_key)
        scale = _resolve_shop_scale(shop_key, entry, place, price_scales)
        overrides = _parse_shop_overrides(entry, shop_key, place)
        offers = _resolve_shop_offers(
            shop, place, overrides, assortment_offers, scale
        )
        for rule in offers:
            _validate_resolved_rule(shop_key, place, rule)
        configs[shop_key] = ShopConfig(
            shop_key=shop_key,
            display_name_zh=_place_for_shop(shop_key).room_name_zh,
            open_hour=open_hour,
            close_hour=close_hour,
            restock_hour=restock_hour,
            offers=tuple(offers),
        )
    missing_shops = set(SHOP_REGISTRY) - set(configs)
    if missing_shops:
        raise _commerce_error(
            f"shops is missing rules for {sorted(missing_shops)}"
        )
    return configs


def validate_service_hosts() -> tuple[ServiceHostRow, ...]:
    """Batch-validate the service-host roster derived from the place registry (design §3.2).

    The roster is no longer authored: each place yields one row declaring
    ``name``/``title`` (the host identity), ``profession``, the interior room
    tag the place anchors to (its key), ``service_id``, and the authored
    component identity kwargs. Every rejection the hand-authored roster
    carried runs unchanged over the derived rows: a profession naming no
    registry row, a blueprint component whose identity kwargs the place fails
    to supply, surplus kwargs no component consumes, a person-bound profession
    anchored to a row, a duplicate service anchor, or a non-text field each
    raise the catalog's named error family.

    Config load never touches the database: ``anchor_room`` is validated as a
    non-empty tag string only (room existence is a sync-time fact), and the
    profession prerequisite is the YAML-only profession registry. A malformed
    professions rulebook surfaces inside this catalog's named error family
    rather than escaping as ``ProfessionConfigError``.
    """
    from world.rules import profession_config
    from world.rules.profession_assembly import identity_fields

    rows: list[ServiceHostRow] = []
    seen_service_ids: set[str] = set()
    for place in PLACE_REGISTRY.values():
        what = f"place {place.key!r}"
        name = _require_text(place.host_name, f"{what}.host_name")
        title = _require_text(place.host_title, f"{what}.host_title")
        anchor_room = _require_text(place.key, f"{what}.key (anchor room tag)")
        service_id = _require_text(place.service_id, f"{what}.service_id")
        profession_key = _require_text(place.profession, f"{what}.profession")
        if service_id in seen_service_ids:
            raise _error(
                f"duplicate service_id {service_id!r} in the place registry; "
                "one roster row per service anchor"
            )
        seen_service_ids.add(service_id)
        try:
            profession = profession_config.get_profession(profession_key)
        except profession_config.ProfessionConfigError as error:
            raise _error(f"{what} profession {profession_key!r} cannot load: {error}") from error
        if profession is None:
            raise _error(
                f"{what} profession {profession_key!r} "
                "is not a profession rulebook row"
            )
        # A roster row IS an anchor registration: its mandatory anchor_room
        # only means something to ``place``-bound components. A ``person``
        # component here would silently carry an anchor — the invalid
        # combination the service-anchoring change forbids at authoring time.
        person_bound = sorted(
            component.type_key
            for component in profession.components
            if component.default_binding == "person"
        )
        if person_bound:
            raise _error(
                f"{what} profession {profession_key!r} "
                f"component(s) {person_bound} are person-bound; a roster row "
                "anchors only place-bound components"
            )
        authored = _require_place_kwargs(place)
        # Blueprint coverage: every component's identity fields except the
        # row-level service_id anchor must be authored by the place.
        consumed: set[str] = set()
        for component in profession.components:
            needed = set(identity_fields(component.type_key)) - {"service_id"}
            lacking = sorted(needed - set(authored))
            if lacking:
                raise _error(
                    f"{what} profession {profession_key!r} "
                    f"component {component.type_key!r} needs authored kwargs {lacking}"
                )
            consumed |= needed
        dead = sorted(set(authored) - consumed)
        if dead:
            raise _error(
                f"{what} authors kwargs {dead} that no component "
                f"of profession {profession_key!r} consumes"
            )
        rows.append(
            ServiceHostRow(
                name=name,
                title=title,
                profession=profession,
                anchor_room=anchor_room,
                service_id=service_id,
                authored_kwargs=authored,
            )
        )
    return tuple(rows)


def _require_place_kwargs(place: Any) -> dict[str, str]:
    """Flatten a place's authored kwargs, rejecting a non-mapping shape."""
    authored = place.authored_kwargs
    if not isinstance(authored, (tuple, list)):
        raise _error(f"place {place.key!r} authored_kwargs must be a sequence of pairs")
    out: dict[str, str] = {}
    for position, pair in enumerate(authored):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise _error(f"place {place.key!r} authored_kwargs[{position}] must be a pair")
        key, value = pair
        out[key] = _require_text(value, f"place {place.key!r}.authored_kwargs[{position}]")
    return out


def _place_for_shop(shop_key: str):
    """Return the place row authoring this shop identity.

    A shop identity is authored on exactly one place (the derived
    ``SHOP_REGISTRY`` fails a duplicate at load), so the first match is the
    owning place. ``validate_shop_configs`` has already rejected any
    ``shop_key`` outside ``SHOP_REGISTRY``, so a miss here is an internal
    load invariant violating fail-closed rather than a user error.
    """
    for place in PLACE_REGISTRY.values():
        if dict(place.authored_kwargs).get("shop_key") == shop_key:
            return place
    raise _commerce_error(f"shops.{shop_key} has no owning place row")


def validate_quest_rewards(raw: Any, definition_registry: Mapping[str, Any]) -> list[GuildQuestOffer]:
    """Validate YAML hand-written rewards into immutable offers.

    ``definition_registry`` is supplied by the caller so catalog loading can run
    before quest synchronization registers definitions without importing state.
    Validation is side-effect free; callers register the returned offers
    explicitly through ``register_catalog_offers``.
    """
    if not isinstance(raw, list):
        raise _error("quest_rewards must be a list")
    offers: list[GuildQuestOffer] = []
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"quest_rewards[{position}] must be a mapping")
        definition_key = entry.get("definition_key")
        if definition_key not in definition_registry:
            raise _error(f"quest_rewards[{position}].definition_key {definition_key!r} is unknown")
        reward_entry = entry.get("reward")
        if not isinstance(reward_entry, Mapping):
            raise _error(f"quest_rewards[{position}].reward must be a mapping")
        copper = _require_int(reward_entry.get("copper"), f"quest_rewards.{definition_key}.copper", minimum=0)
        merit = _require_int(reward_entry.get("merit"), f"quest_rewards.{definition_key}.merit", minimum=0)
        items_entry = reward_entry.get("items")
        if not isinstance(items_entry, list):
            raise _error(f"quest_rewards.{definition_key}.items must be a list")
        quantities: list[ItemQuantity] = []
        seen: set[str] = set()
        for item_position, item in enumerate(items_entry, start=1):
            if not isinstance(item, Mapping):
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}] must be a mapping")
            item_key = item.get("item_key")
            if item_key not in ITEM_REGISTRY:
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}].item_key {item_key!r} is unknown")
            if item_key in seen:
                raise _error(f"quest_rewards.{definition_key} has duplicate item {item_key!r}")
            seen.add(item_key)
            quantity = _require_int(item.get("quantity"), f"quest_rewards.{definition_key}.{item_key}.quantity", minimum=1)
            quantities.append(ItemQuantity(item_key=item_key, quantity=quantity))
        offer = GuildQuestOffer(
            definition_key=definition_key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(copper=copper, items=tuple(quantities), merit=merit),
        )
        # Validate the full offer contract (known branch, rank band, items)
        # without touching the process-global offer registry.
        validate_guild_offer_side_effect_free(offer)
        offers.append(offer)
    return offers


def validate_guild_offer_side_effect_free(offer: GuildQuestOffer) -> None:
    """Run ``register_guild_offer``'s validation without mutating the registry."""
    from world.rules.guild_offers import GuildOfferError, validate_offer

    try:
        validate_offer(offer)
    except GuildOfferError as error:
        raise _error(f"catalog offer {offer.definition_key!r} is invalid: {error}") from error


class GuildCatalog:
    """Validated, immutable snapshot of the fully-joined guild-economy catalog."""

    def __init__(
        self,
        merit_thresholds: dict[str, int],
        exam_profiles: dict[str, ExamProfile],
        shop_configs: dict[str, ShopConfig],
        quest_offers: list[GuildQuestOffer],
        service_hosts: tuple[ServiceHostRow, ...],
    ):
        self.merit_thresholds = {**merit_thresholds}
        self.exam_profiles = {**exam_profiles}
        self.shop_configs = {**shop_configs}
        self.quest_offers = tuple(quest_offers)
        self.service_hosts = tuple(service_hosts)

    @property
    def offer_by_definition(self) -> dict[str, GuildQuestOffer]:
        return {offer.definition_key: offer for offer in self.quest_offers}

    @property
    def host_by_service_id(self) -> dict[str, ServiceHostRow]:
        return {row.service_id: row for row in self.service_hosts}


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


def register_catalog_offers(catalog: GuildCatalog) -> None:
    """Register every catalog offer idempotently (called by sync_guild_economy)."""
    from world.rules.guild_offers import register_guild_offer

    for offer in catalog.quest_offers:
        register_guild_offer(offer)