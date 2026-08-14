"""``shop_hours`` world-clock event source (guild-economy D-8).

Opening state is always derived from the WorldClock calendar; no redundant
open boolean is persisted. Crossing a same-day or overnight boundary emits one
JSON-safe ``ScheduledEvent`` per transition using direct boundary arithmetic,
never per-second iteration.
"""

from typing import Any

from evennia.utils.logger import log_warn

from world.rules.clock import CLOCK_YAML, ScheduledEvent, register_event_source
from world.rules.guild_config import get_catalog
from world.rules.guild_offers import GUILD_OFFER_REGISTRY

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
_HOUR_SECONDS = int(CLOCK_YAML["seconds_per_hour"])


def _boundary_ticks(shop_key: str, open_hour: int, close_hour: int, start_tick: int, end_tick: int) -> list[tuple[int, str]]:
    """Return ``(due_tick, kind)`` transitions crossed in (start_tick, end_tick].

    ``kind`` is ``open`` or ``close``. A same-day interval opens then closes;
    an overnight interval closes then opens.
    """
    result: list[tuple[int, str]] = []
    day = start_tick // _DAY_SECONDS
    last_day = end_tick // _DAY_SECONDS
    while day <= last_day:
        day_start = day * _DAY_SECONDS
        open_tick = day_start + open_hour * _HOUR_SECONDS
        close_tick = day_start + close_hour * _HOUR_SECONDS
        if open_hour < close_hour:
            for due_tick, kind in ((open_tick, "open"), (close_tick, "close")):
                if start_tick < due_tick <= end_tick:
                    result.append((due_tick, kind))
        else:
            for due_tick, kind in ((close_tick, "close"), (open_tick, "open")):
                if start_tick < due_tick <= end_tick:
                    result.append((due_tick, kind))
        day += 1
    result.sort(key=lambda item: (item[0], item[1]))
    return result


def settle_shop_hours(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Emit open/close events for every crossed boundary of every shop."""
    events: list[ScheduledEvent] = []
    for shop_key, config in get_catalog().shop_configs.items():
        for due_tick, kind in _boundary_ticks(
            shop_key,
            config.open_hour,
            config.close_hour,
            start_tick,
            end_tick,
        ):
            events.append(
                ScheduledEvent(
                    "shop_hours",
                    due_tick,
                    {"shop_key": shop_key, "kind": kind},
                )
            )
    return events


def register_shop_hours() -> None:
    """Register the ``shop_hours`` clock source idempotently.

    Read-only seam: settlement only emits events from the clock calendar and
    never writes durable state, so no advance-surface contract is declared.
    """
    register_event_source("shop_hours", settle_shop_hours)