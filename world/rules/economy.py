"""Deterministic merchant-stock and buy/sell transactions (guild-economy D-8).

Shops use finite persistent integer stock and exact integer copper prices.
``buy`` and ``sell`` name one party member (the recipient or the seller), pay
from and credit the party purse (the commander's wallet), preflight every input,
compute complete replacement values without writing, then commit purse, the
member's inventory and ACQUIRE quest progress, and merchant stock in one
transaction with full cache restoration. Money is always integer copper; the
purse can never become negative and stock never overflows its cap.
"""

from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from world.lore.items import ITEM_REGISTRY
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.guild_config import get_catalog
from world.rules.service_gate import REASON_REMOTE, service_available
from world.rules.surfaces import (
    attribute_snapshot,
    restore_traits,
    snapshot_traits,
)
from world.rules.equipment import (
    EquippedRemovalError,
    materialize_registry_object,
    plan_inventory_delta,
    registry_key_for_object,
)
from world.rules.party_scope import (
    PURPOSE_ORGANIZE,
    authorize_member,
    resolve_commander,
)

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


class TradeError(ValueError):
    """A shop trade violates the deterministic trade contract."""


class TradeReason(StrEnum):
    NOT_A_PLAYER = "not_a_player"
    NO_MERCHANT = "no_merchant"
    REMOTE_MERCHANT = "remote_merchant"
    # Co-located but the shared anchoring gate refused (off-anchor place
    # binding or malformed stored data); the player line is the gate's
    # registry-owned message, not a shop-specific one.
    SERVICE_UNAVAILABLE = "service_unavailable"
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
    EQUIPPED_ITEM = "equipped_item"


def _require_local_merchant(actor: Any, merchant_host: Any) -> Any:
    if merchant_host is None or not isinstance(merchant_host, NPC):
        raise TradeError(TradeReason.NO_MERCHANT)
    if not hasattr(merchant_host, "components") or not merchant_host.components.has(Merchant.name):
        raise TradeError(TradeReason.NO_MERCHANT)
    merchant = merchant_host.components.get(Merchant.get_component_slot())
    verdict = service_available(actor, merchant_host, merchant)
    if not verdict.allowed:
        if verdict.reason == REASON_REMOTE:
            raise TradeError(TradeReason.REMOTE_MERCHANT)
        raise TradeError(TradeReason.SERVICE_UNAVAILABLE)
    return merchant


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


def _trade_member(acting: Any, member_id: Any) -> tuple[Any, Any]:
    """Re-derive the commander purse owner and one authorized member.

    Membership is checked before any price, stock, or item read, so a forged
    or stale id never reaches pricing. The organizing purpose admits a
    knocked-out member: buying into or selling from a bag reorganizes it
    without asking the member to act.
    """
    commander = resolve_commander(acting)
    member = authorize_member(
        commander, member_id, PURPOSE_ORGANIZE, anchor=acting
    )
    return commander, member


def _snapshot_trade(commander: Any, member: Any, merchant: Any) -> dict[str, Any]:
    return {
        "wallet": attribute_snapshot(commander, "wallet"),
        # A completed ACQUIRE objective auto-settles inside the quest-log
        # delta and pays the quest actor's own wallet, so a companion
        # recipient's wallet is a distinct trade surface.
        "member_wallet": (
            None if member is commander else attribute_snapshot(member, "wallet")
        ),
        "inventory": attribute_snapshot(member, "inventory"),
        "quest_log": attribute_snapshot(member, "quest_log"),
        "guild_reward_claims": attribute_snapshot(member, "guild_reward_claims"),
        "merchant_stock": attribute_snapshot(merchant.host, f"{merchant.get_component_slot()}::merchant_stock"),
        "last_restock_day": attribute_snapshot(merchant.host, f"{merchant.get_component_slot()}::last_restock_day"),
        "merchant_relations": attribute_snapshot(merchant.host, "relations_data"),
        "traits": snapshot_traits(member),
    }


def _restore_trade(
    commander: Any, member: Any, merchant: Any, snapshot: dict[str, Any]
) -> None:
    from world.rules.surfaces import restore_attribute_best_effort

    restore_attribute_best_effort(commander, "wallet", snapshot["wallet"])
    if snapshot["member_wallet"] is not None:
        restore_attribute_best_effort(member, "wallet", snapshot["member_wallet"])
    for key in ("inventory", "quest_log", "guild_reward_claims"):
        restore_attribute_best_effort(member, key, snapshot[key])
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
    restore_attribute_best_effort(
        merchant.host, "relations_data", snapshot["merchant_relations"]
    )
    restore_traits(member, snapshot["traits"])


def buy(
    acting: Any,
    merchant_host: Any,
    item_key: str,
    quantity: int,
    recipient: Any,
) -> dict[str, Any]:
    """Buy ``quantity`` of an offered item into one member's bag.

    ``recipient`` is a member dbid re-derived through the party boundary and
    never trusted as identity; the unchanged buy price is debited from the
    commander's wallet (the party purse) and the merchant affinity stays
    between the host and the commander, because the commander pays.
    """
    commander, member = _trade_member(acting, recipient)
    quantity = _require_positive_quantity(quantity)
    if item_key not in ITEM_REGISTRY:
        raise TradeError(TradeReason.UNKNOWN_ITEM, item_key)
    definition = ITEM_REGISTRY[item_key]
    if not definition.sellable:
        raise TradeError(TradeReason.UNSELLABLE, item_key)
    merchant = _require_local_merchant(acting, merchant_host)
    shop_key = merchant.shop_key
    offer = _offer_rule(shop_key, item_key)
    if not shop_is_open(shop_key):
        raise TradeError(TradeReason.CLOSED)
    stock = parse_merchant_stock(merchant)
    if stock.get(item_key, 0) < quantity:
        raise TradeError(TradeReason.INSUFFICIENT_STOCK)
    total = offer.buy_copper * quantity
    wallet = int(commander.db.wallet or 0)
    if wallet < total:
        raise TradeError(TradeReason.INSUFFICIENT_FUNDS)

    inventory_plan = plan_inventory_delta(
        member,
        additions=tuple(item_key for _ in range(quantity)),
    )
    snapshot = _snapshot_trade(commander, member, merchant)
    pin_operations = inventory_plan.acquire[1] if inventory_plan.acquire is not None else ()
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in pin_operations:
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    def writer():
        commander.db.wallet = wallet - total
        member.db.inventory = list(inventory_plan.after)
        if inventory_plan.acquire is not None:
            from world.quests.transitions import apply_quest_log_delta

            apply_quest_log_delta(
                member,
                list(inventory_plan.acquire[0]),
                inventory_plan.acquire[1],
            )
        new_stock = dict(stock)
        new_stock[item_key] -= quantity
        merchant.merchant_stock = new_stock
        from world.rules.affinity import AffinitySource, apply_affinity_change

        # The commander pays, so the trade affinity stays with the commander
        # even when the goods enter a companion's bag.
        apply_affinity_change(merchant.host, commander, AffinitySource.TRADE, 1)
        # Mirror the key-list entries with one contained object each, so
        # drop/give always resolve a real object for the bought items.
        for _ in range(quantity):
            materialize_registry_object(member, item_key)

    def restore():
        _restore_trade(commander, member, merchant, snapshot)
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


def sell(
    acting: Any,
    merchant_host: Any,
    item_key: str,
    quantity: int,
    seller: Any,
) -> dict[str, Any]:
    """Sell ``quantity`` of one member's unequipped item into the party purse.

    ``seller`` is a member dbid re-derived through the party boundary and
    never trusted as identity. Only that member's unequipped copies are
    sellable: the planner refuses an equipped removal, which maps to
    ``item_equipped``. The unchanged, independently configured sell price is
    credited to the commander's wallet, and the trade affinity stays between
    the host and the commander, because the commander receives the proceeds.
    """
    commander, member = _trade_member(acting, seller)
    quantity = _require_positive_quantity(quantity)
    if item_key not in ITEM_REGISTRY:
        raise TradeError(TradeReason.UNKNOWN_ITEM, item_key)
    definition = ITEM_REGISTRY[item_key]
    if not definition.sellable:
        raise TradeError(TradeReason.UNSELLABLE, item_key)
    merchant = _require_local_merchant(acting, merchant_host)
    shop_key = merchant.shop_key
    offer = _offer_rule(shop_key, item_key)
    if not shop_is_open(shop_key):
        raise TradeError(TradeReason.CLOSED)
    inventory = list(member.db.inventory or [])
    if inventory.count(item_key) < quantity:
        raise TradeError(TradeReason.INSUFFICIENT_ITEMS)
    try:
        inventory_plan = plan_inventory_delta(
            member,
            removals=tuple(item_key for _ in range(quantity)),
        )
    except EquippedRemovalError:
        raise TradeError(TradeReason.EQUIPPED_ITEM, item_key)
    stock = parse_merchant_stock(merchant)
    if stock.get(item_key, 0) + quantity > offer.max_stock:
        raise TradeError(TradeReason.STOCK_OVERFLOW)
    total = offer.sell_copper * quantity

    snapshot = _snapshot_trade(commander, member, merchant)
    pin_operations = inventory_plan.acquire[1] if inventory_plan.acquire is not None else ()
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in pin_operations:
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    def writer():
        commander.db.wallet = int(commander.db.wallet or 0) + total
        member.db.inventory = list(inventory_plan.after)
        if inventory_plan.acquire is not None:
            from world.quests.transitions import apply_quest_log_delta

            apply_quest_log_delta(
                member,
                list(inventory_plan.acquire[0]),
                inventory_plan.acquire[1],
            )
        new_stock = dict(stock)
        new_stock[item_key] = new_stock.get(item_key, 0) + quantity
        merchant.merchant_stock = new_stock
        from world.rules.affinity import AffinitySource, apply_affinity_change

        # The commander receives the proceeds, so the trade affinity stays
        # with the commander even when a companion's item was sold.
        apply_affinity_change(merchant.host, commander, AffinitySource.TRADE, 1)
        # Drop the mirrored contained objects for the sold key; the key list
        # stays authoritative when containment holds fewer than sold.
        contained = [
            obj for obj in member.contents if registry_key_for_object(obj) == item_key
        ]
        for obj in contained[:quantity]:
            obj.delete()

    def restore():
        _restore_trade(commander, member, merchant, snapshot)
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
        "wallet": int(commander.db.wallet or 0),
    }