"""The shops-section validator: hours, join, overrides, resolved prices.

``validate_shop_configs`` resolves each shop row against its owning place
(:func:`world.rules.guild_config._hosts._place_for_shop`) and the validated
offer rules from ``_commerce``.
"""

from typing import Any, Mapping

from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
from world.lore.settlements.shops import SHOP_REGISTRY

from ._commerce import (
    _SHOPS_ROW_FIELDS,
    _parse_shop_overrides,
    _resolve_shop_offers,
    _resolve_shop_scale,
    _validate_resolved_rule,
)
from ._loaders import _commerce_error, _require_int
from ._hosts import _place_for_shop
from ._types import ItemOfferRule, ShopConfig


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
        place = _place_for_shop(shop_key)
        scale = _resolve_shop_scale(shop_key, entry, place, price_scales)
        overrides = _parse_shop_overrides(entry, shop_key, place)
        offers = _resolve_shop_offers(
            shop, place, overrides, assortment_offers, scale
        )
        for rule in offers:
            _validate_resolved_rule(shop_key, place, rule)
        configs[shop_key] = ShopConfig(
            shop_key=shop_key,
            display_name_zh=place.room_name_zh,
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
