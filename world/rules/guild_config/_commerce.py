"""Assortment/price validation and the shop-offer resolution primitives.

The row-field sets, the integer price helpers, and the complete-or-rejected
override parsing — everything the shop join needs except the shop loop itself
(lives in ``_shops``).
"""

from dataclasses import replace
from typing import Any, Mapping

from world.lore.economy import PRICE_TABLE
from world.lore.items import ITEM_REGISTRY
from world.lore.settlements.assortments import (
    ASSORTMENT_REGISTRY,
    KEEPSAKE_BAND_KEY,
)
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY

from ._loaders import _commerce_error, _require_int
from ._types import ItemOfferRule


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
