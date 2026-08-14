"""``caravan_arrivals`` world-clock event source (guild-economy D-8).

One deterministic restock per crossed merchant restock day, caught up across
multi-day skips via direct boundary arithmetic up to each cap. Each merchant's
``last_restock_day`` advances and one JSON-safe event is emitted per
merchant/day. Malformed merchant data is isolated: that host is left unchanged
and other merchants still settle.
"""

from typing import Any

from evennia.utils.logger import log_warn

from typeclasses.npcs import NPC
from typeclasses.components import Merchant
from world.rules.clock import CLOCK_YAML, ScheduledEvent, SurfaceSnapshot, register_event_source
from world.rules.guild_config import get_catalog
from world.rules.surfaces import attribute_snapshot

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
_HOUR_SECONDS = int(CLOCK_YAML["seconds_per_hour"])


def _merchant_surface_keys() -> tuple[str, ...]:
    """The host-attribute keys backing ``Merchant``'s restock DBFields.

    Component DBFields persist as host attributes keyed
    ``"{slot}::{field}"`` with no category (evennia contrib
    ``components.dbfield``); the keys stay next to the ``Merchant``
    declaration so a key drift fails the behavioral test, not silently.
    """
    slot = Merchant.get_component_slot()
    return (f"{slot}::merchant_stock", f"{slot}::last_restock_day")


def snapshot_caravan_arrival_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """Snapshot the durable surfaces ``settle_caravan_arrivals`` may write.

    The advance-surface contract for the ``caravan_arrivals`` source: the
    restock host attributes of every NPC host carrying the ``Merchant``
    component, using the same ``_merchants()`` discovery as settlement. Pure
    read: no attribute, location, or tag changes.
    """
    keys = _merchant_surface_keys()
    registry: dict[int, SurfaceSnapshot] = {}
    for host, _ in _merchants():
        registry[id(host)] = SurfaceSnapshot(
            attributes={(key, None): attribute_snapshot(host, key) for key in keys}
        )
    return registry


def _current_boundary_day(end_tick: int, restock_hour: int) -> int:
    """Return the restock-boundary day index that ``end_tick`` has reached."""
    today, seconds_into_day = divmod(end_tick, _DAY_SECONDS)
    if seconds_into_day >= restock_hour * _HOUR_SECONDS:
        return today
    return today - 1


def _merchants() -> list[tuple[Any, Any]]:
    for host in NPC.objects.all_family():
        merchant = host.components.get(Merchant.get_component_slot())
        if merchant is None:
            continue
        yield host, merchant


def _apply_restock_days(
    merchant: Any,
    host: Any,
    shop_config: Any,
    last_day: int,
    boundary_day: int,
) -> list[dict[str, Any]]:
    """Apply capped restocks for each crossed day and return event payloads.

    A malformed stock mapping isolates this host: a diagnostic is logged and
    the host is left unchanged while other merchants continue.
    """
    offers = {offer.item_key: offer for offer in shop_config.offers}
    raw_stock = merchant.merchant_stock
    if raw_stock is None:
        stock: dict[str, int] = {}
    elif hasattr(raw_stock, "items"):
        stock = {}
        for key, value in dict(raw_stock).items():
            if key not in offers or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                log_warn(
                    f"caravan_arrivals: malformed stock on {host.key}; "
                    "leaving host unchanged"
                )
                return []
            stock[key] = int(value)
    else:
        log_warn(
            f"caravan_arrivals: malformed stock on {host.key}; "
            "leaving host unchanged"
        )
        return []

    events: list[dict[str, Any]] = []
    for day_index in range(last_day + 1, boundary_day + 1):
        additions: list[str] = []
        for item_key, offer in offers.items():
            current_qty = int(stock.get(item_key, 0))
            if current_qty >= offer.max_stock:
                continue
            added = min(offer.restock_quantity, offer.max_stock - current_qty)
            stock[item_key] = current_qty + added
            additions.append(item_key)
        # The day is processed regardless of whether any item gained stock, so
        # replaying the same settlement never re-emits a past day.
        merchant.merchant_stock = stock
        merchant.last_restock_day = day_index
        events.append(
            {
                "shop_key": shop_config.shop_key,
                "day": day_index,
                "items_added": sorted(additions),
            }
        )
    return events


def settle_caravan_arrivals(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Apply one capped restock per crossed restock day for every merchant."""
    events: list[ScheduledEvent] = []
    catalog = get_catalog()
    for host, merchant in _merchants():
        shop_key = merchant.shop_key
        shop_config = catalog.shop_configs.get(shop_key)
        if shop_config is None:
            log_warn(
                f"caravan_arrivals: merchant {host.key} has unknown shop "
                f"{shop_key!r}"
            )
            continue
        restock_hour = shop_config.restock_hour
        start_boundary = _current_boundary_day(start_tick, restock_hour)
        end_boundary = _current_boundary_day(end_tick, restock_hour)
        current = merchant.last_restock_day
        if current is None:
            # A merchant created now already carries its initial stock; treat
            # the boundary reached at start_tick as its last processed day so
            # the first restock happens only on a genuinely crossed boundary.
            merchant.last_restock_day = start_boundary
            last_day = start_boundary
        elif isinstance(current, bool) or not isinstance(current, int):
            log_warn(
                f"caravan_arrivals: malformed last_restock_day on {host.key}; "
                "leaving host unchanged"
            )
            continue
        else:
            last_day = int(current)
        payloads = _apply_restock_days(
            merchant,
            host,
            shop_config,
            last_day,
            end_boundary,
        )
        for payload in payloads:
            events.append(
                ScheduledEvent(
                    "caravan_arrivals",
                    payload["day"] * _DAY_SECONDS
                    + shop_config.restock_hour * _HOUR_SECONDS,
                    {
                        "shop_key": payload["shop_key"],
                        "day": payload["day"],
                        "items_added": payload["items_added"],
                    },
                )
            )
    return events


def register_caravan_arrivals() -> None:
    """Register the ``caravan_arrivals`` clock source idempotently."""
    register_event_source(
        "caravan_arrivals",
        settle_caravan_arrivals,
        snapshot_caravan_arrival_surfaces,
    )