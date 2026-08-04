"""Deterministic merchant-stock and buy/sell transactions (guild-economy D-8).

Shops use finite persistent integer stock and exact integer copper prices.
``buy`` and ``sell`` preflight every input, compute complete replacement values
without writing, then commit wallet, inventory, ACQUIRE quest progress, and
merchant stock in one transaction with full cache restoration. Money is always
integer copper; wallet can never become negative and stock never overflows its
cap.
"""

from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.components import Merchant
from world.lore.items import ITEM_REGISTRY
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.guild_config import get_catalog
from world.rules.surfaces import (
    attribute_snapshot,
    restore_traits,
    snapshot_traits,
)
from world.rules.equipment import plan_inventory_delta

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


class TradeError(ValueError):
    """A shop trade violates the deterministic trade contract."""


class TradeReason(StrEnum):
    NOT_A_PLAYER = "not_a_player"
    NO_MERCHANT = "no_merchant"
    REMOTE_MERCHANT = "remote_merchant"
    CLOSED = "closed"
    UNKNOWN_ITEM = "unknown_item"
    NOT_OFFERED = "not_offered"
    UNSELLABLE = "unsellable"
    BAD_QUANTITY = "bad_quantity"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INSUFFICIENT_STOCK = "insufficient_stock"
    INSUFFICIENT_ITEMS = "insufficient_items"
    STOCK_OVERFLOW = "stock_overflow"
    MALFORMED_STOCK = "malformed_stock"


def _require_local_merchant(actor: Any, merchant_host: Any) -> Any:
    if merchant_host is None or not hasattr(merchant_host, "components"):
        raise TradeError(TradeReason.NO_MERCHANT)
    if not merchant_host.components.has(Merchant.name):
        raise TradeError(TradeReason.NO_MERCHANT)
    if actor.location is None or merchant_host.location != actor.location:
        raise TradeError(TradeReason.REMOTE_MERCHANT)
    return merchant_host.components.get(Merchant.get_component_slot())


def _require_positive_quantity(quantity: Any) -> int:
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise TradeError(TradeReason.BAD_QUANTITY)
    return quantity


def parse_merchant_stock(merchant: Any) -> dict[str, int]:
    """Strictly parse a merchant's stock mapping, failing closed on corruption."""
    raw = merchant.merchant_stock
    if raw is None:
        return {}
    if not hasattr(raw, "items"):
        raise TradeError(TradeReason.MALFORMED_STOCK)
    stock: dict[str, int] = {}
    for item_key, quantity in dict(raw).items():
        if item_key not in ITEM_REGISTRY:
            raise TradeError(TradeReason.MALFORMED_STOCK, item_key)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise TradeError(TradeReason.MALFORMED_STOCK, item_key)
        stock[item_key] = quantity
    return stock


def _current_tick() -> int:
    return int(get_world_clock().tick)


def _shop_open_at(config: Any, tick: int) -> bool:
    """Return whether ``config``'s interval contains the world tick (pure)."""
    seconds_into_day = tick % _DAY_SECONDS
    seconds_per_hour = int(CLOCK_YAML["seconds_per_hour"])
    current_hour = seconds_into_day // seconds_per_hour
    current_minute = (seconds_into_day % seconds_per_hour) // 60
    now = current_hour * 60 + current_minute
    open_minute = config.open_hour * 60
    close_minute = config.close_hour * 60
    if open_minute < close_minute:
        return open_minute <= now < close_minute
    return now >= open_minute or now < close_minute


def shop_is_open_at(shop_key: str, tick: int) -> bool:
    """Return whether the shop's interval contains the given world tick.

    Pure and clock-free so read-only presentation can derive opening state
    without ever creating the world-clock singleton.
    """
    config = get_catalog().shop_configs.get(shop_key)
    if config is None:
        raise TradeError(TradeReason.MALFORMED_STOCK, "unknown shop")
    return _shop_open_at(config, tick)


def shop_is_open(shop_key: str) -> bool:
    """Return whether the shop's interval currently contains the world time."""
    return shop_is_open_at(shop_key, _current_tick())


def _offer_rule(shop_key: str, item_key: str):
    config = get_catalog().shop_configs.get(shop_key)
    if config is None:
        raise TradeError(TradeReason.MALFORMED_STOCK, "unknown shop")
    for offer in config.offers:
        if offer.item_key == item_key:
            return offer
    raise TradeError(TradeReason.NOT_OFFERED, item_key)


def _snapshot_trade(actor: Any, merchant: Any) -> dict[str, Any]:
    return {
        "wallet": attribute_snapshot(actor, "wallet"),
        "inventory": attribute_snapshot(actor, "inventory"),
        "quest_log": attribute_snapshot(actor, "quest_log"),
        "merchant_stock": attribute_snapshot(merchant.host, f"{merchant.get_component_slot()}::merchant_stock"),
        "last_restock_day": attribute_snapshot(merchant.host, f"{merchant.get_component_slot()}::last_restock_day"),
        "traits": snapshot_traits(actor),
    }


def _restore_trade(actor: Any, merchant: Any, snapshot: dict[str, Any]) -> None:
    from world.rules.surfaces import restore_attribute_best_effort

    for key in ("wallet", "inventory", "quest_log"):
        restore_attribute_best_effort(actor, key, snapshot[key])
    restore_attribute_best_effort(
        merchant.host,
        f"{merchant.get_component_slot()}::merchant_stock",
        snapshot["merchant_stock"],
    )
    restore_attribute_best_effort(
        merchant.host,
        f"{merchant.get_component_slot()}::last_restock_day",
        snapshot["last_restock_day"],
    )
    restore_traits(actor, snapshot["traits"])


def buy(actor: Any, merchant_host: Any, item_key: str, quantity: int = 1) -> dict[str, Any]:
    """Buy ``quantity`` of an offered item with exact integer copper."""
    quantity = _require_positive_quantity(quantity)
    if item_key not in ITEM_REGISTRY:
        raise TradeError(TradeReason.UNKNOWN_ITEM, item_key)
    merchant = _require_local_merchant(actor, merchant_host)
    shop_key = merchant.shop_key
    offer = _offer_rule(shop_key, item_key)
    if not shop_is_open(shop_key):
        raise TradeError(TradeReason.CLOSED)
    stock = parse_merchant_stock(merchant)
    if stock.get(item_key, 0) < quantity:
        raise TradeError(TradeReason.INSUFFICIENT_STOCK)
    total = offer.buy_copper * quantity
    wallet = int(actor.db.wallet or 0)
    if wallet < total:
        raise TradeError(TradeReason.INSUFFICIENT_FUNDS)

    inventory_plan = plan_inventory_delta(
        actor,
        additions=tuple(item_key for _ in range(quantity)),
    )
    snapshot = _snapshot_trade(actor, merchant)
    pin_operations = inventory_plan.acquire[1] if inventory_plan.acquire is not None else ()
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in pin_operations:
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    def writer():
        actor.db.wallet = wallet - total
        actor.db.inventory = list(inventory_plan.after)
        if inventory_plan.acquire is not None:
            from world.quests.transitions import apply_quest_log_delta

            apply_quest_log_delta(
                actor,
                list(inventory_plan.acquire[0]),
                inventory_plan.acquire[1],
            )
        new_stock = dict(stock)
        new_stock[item_key] -= quantity
        merchant.merchant_stock = new_stock

    def restore():
        _restore_trade(actor, merchant, snapshot)
        from world.quests.transitions import restore_pin_reasons

        for room, _, _ in pin_operations:
            restore_pin_reasons(room, pin_snapshots[id(room)])

    try:
        with transaction.atomic():
            writer()
    except Exception:
        restore()
        raise
    return {
        "item_key": item_key,
        "quantity": quantity,
        "total_copper": total,
        "wallet": wallet - total,
    }


def sell(actor: Any, merchant_host: Any, item_key: str, quantity: int = 1) -> dict[str, Any]:
    """Sell ``quantity`` of a sellable held item for exact integer copper."""
    quantity = _require_positive_quantity(quantity)
    if item_key not in ITEM_REGISTRY:
        raise TradeError(TradeReason.UNKNOWN_ITEM, item_key)
    definition = ITEM_REGISTRY[item_key]
    if not definition.sellable:
        raise TradeError(TradeReason.UNSELLABLE, item_key)
    merchant = _require_local_merchant(actor, merchant_host)
    shop_key = merchant.shop_key
    offer = _offer_rule(shop_key, item_key)
    if not shop_is_open(shop_key):
        raise TradeError(TradeReason.CLOSED)
    inventory = list(actor.db.inventory or [])
    if inventory.count(item_key) < quantity:
        raise TradeError(TradeReason.INSUFFICIENT_ITEMS)
    stock = parse_merchant_stock(merchant)
    if stock.get(item_key, 0) + quantity > offer.max_stock:
        raise TradeError(TradeReason.STOCK_OVERFLOW)
    total = offer.sell_copper * quantity

    inventory_plan = plan_inventory_delta(
        actor,
        removals=tuple(item_key for _ in range(quantity)),
    )
    snapshot = _snapshot_trade(actor, merchant)
    pin_operations = inventory_plan.acquire[1] if inventory_plan.acquire is not None else ()
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in pin_operations:
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    def writer():
        actor.db.wallet = int(actor.db.wallet or 0) + total
        actor.db.inventory = list(inventory_plan.after)
        if inventory_plan.acquire is not None:
            from world.quests.transitions import apply_quest_log_delta

            apply_quest_log_delta(
                actor,
                list(inventory_plan.acquire[0]),
                inventory_plan.acquire[1],
            )
        new_stock = dict(stock)
        new_stock[item_key] = new_stock.get(item_key, 0) + quantity
        merchant.merchant_stock = new_stock

    def restore():
        _restore_trade(actor, merchant, snapshot)
        from world.quests.transitions import restore_pin_reasons

        for room, _, _ in pin_operations:
            restore_pin_reasons(room, pin_snapshots[id(room)])

    try:
        with transaction.atomic():
            writer()
    except Exception:
        restore()
        raise
    return {
        "item_key": item_key,
        "quantity": quantity,
        "total_copper": total,
        "wallet": int(actor.db.wallet or 0),
    }