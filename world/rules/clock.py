"""Player-driven deterministic world time and settlement ordering."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from math import gcd
from pathlib import Path
from typing import Any

import yaml
from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

from world.rules.buffs import BUFF_DEFINITIONS, tick_buffs
from world.rules.sexual_state import DECAY_CONFIG, decay_tick, reset_daily_counters
from world.rules.traits import GAUGE_KEYS


CLOCK_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "clock.yaml").read_text(encoding="utf-8")
)
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
_INTERVALS = [
    definition.tick_interval
    for definition in BUFF_DEFINITIONS.values()
    if definition.tick_interval is not None
] + [config["interval_seconds"] for config in DECAY_CONFIG.values()]
if any(not isinstance(interval, int) or interval <= 0 for interval in _INTERVALS):
    raise ValueError(f"invalid settlement interval: {_INTERVALS!r}")
SETTLEMENT_QUANTUM_SECONDS = gcd(*_INTERVALS)
_STAGE_ORDER = (
    "gauge_regen",
    "buff_ticks",
    "sexual_decay",
    "magic_study",
    "daily_resets",
    "caravan_arrivals",
    "shop_hours",
    "quest_deadlines",
    "npc_schedules",
)
_EVENT_SOURCES: dict[str, Callable[[int, int], list["ScheduledEvent"]]] = {}


class DaypartError(ValueError):
    """Raised when a named clock daypart is unknown."""


class AdvanceSource(StrEnum):
    """The action category that supplied elapsed game seconds."""

    COMMAND = "command"
    COMBAT = "combat"
    SKIP = "skip"


@dataclass(frozen=True)
class WorldDateTime:
    """Calendar fields derived entirely from one game-time tick."""

    year: int
    season_index: int
    day_in_season: int
    hour: int
    minute: int
    second: int

    @classmethod
    def from_tick(cls, tick: int) -> "WorldDateTime":
        if tick < 0:
            raise ValueError("tick must be non-negative")
        total_days, remaining = divmod(tick, _DAY_SECONDS)
        days_per_year = CLOCK_YAML["days_per_season"] * CLOCK_YAML["seasons_per_year"]
        year, day_of_year = divmod(total_days, days_per_year)
        season_index, day_index = divmod(day_of_year, CLOCK_YAML["days_per_season"])
        hour, remaining = divmod(remaining, CLOCK_YAML["seconds_per_hour"])
        minute, second = divmod(remaining, 60)
        return cls(year, season_index, day_index + 1, hour, minute, second)

    @property
    def season_name(self) -> str:
        return CLOCK_YAML["season_names"][self.season_index]


def seconds_until_daypart(calendar: WorldDateTime, daypart_name: str) -> int:
    """Return seconds until the next strictly future occurrence of a daypart."""
    try:
        target_hour = CLOCK_YAML["dayparts"][daypart_name]
    except KeyError as error:
        raise DaypartError(f"unknown daypart {daypart_name!r}") from error
    current = calendar.hour * CLOCK_YAML["seconds_per_hour"] + calendar.minute * 60 + calendar.second
    target = target_hour * CLOCK_YAML["seconds_per_hour"]
    remaining = target - current
    return remaining if remaining > 0 else remaining + _DAY_SECONDS


@dataclass(frozen=True)
class ScheduledEvent:
    """A serializable event made due by a world-time boundary."""

    kind: str
    due_tick: int
    payload: dict[str, Any]


def _gauge_value(gauge: Any) -> float:
    return float(getattr(gauge, "current", gauge.value))


def _settle_gauge_regen(entities: Iterable[Any], elapsed_seconds: int) -> None:
    for entity in entities:
        for key in GAUGE_KEYS:
            gauge = getattr(entity.traits, key, None)
            if gauge is None:
                continue
            rate = float(getattr(gauge, "rate", 0))
            maximum = float(gauge.max)
            gauge.current = min(maximum, _gauge_value(gauge) + rate * elapsed_seconds)


def _has_settlement_work(entity: Any) -> bool:
    buffs = getattr(entity, "buffs", None)
    if buffs is not None and getattr(buffs, "all", None) and buffs.all:
        from world.rules.buffs import _active_buff_instances

        if any(
            buff.remaining_seconds is not None or buff.tick_interval is not None
            for buff in _active_buff_instances(entity)
        ):
            return True
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return False
    return any(
        getattr(sexual, field).level != config["floor"]
        for field, config in DECAY_CONFIG.items()
        if config.get("only_from") is None
        or getattr(sexual, field).level == config["only_from"]
    )


def _settle_buffs_and_decay(entities: tuple[Any, ...], elapsed_seconds: int) -> None:
    quanta, remainder = divmod(elapsed_seconds, SETTLEMENT_QUANTUM_SECONDS)
    for _ in range(min(quanta, CLOCK_YAML["max_settlement_quanta"])):
        if not any(_has_settlement_work(entity) for entity in entities):
            break
        for entity in entities:
            tick_buffs(entity, SETTLEMENT_QUANTUM_SECONDS)
            decay_tick(entity, SETTLEMENT_QUANTUM_SECONDS)
    if remainder and any(_has_settlement_work(entity) for entity in entities):
        for entity in entities:
            tick_buffs(entity, remainder)
            decay_tick(entity, remainder)


def _try_accrue_magic_study(entities: tuple[Any, ...], seconds: int, source: AdvanceSource) -> None:
    try:
        from world.rules.progression import accrue_magic_study
    except ImportError:
        return
    accrue_magic_study(entities, seconds, source)


def register_event_source(kind: str, source: Callable[[int, int], list[ScheduledEvent]]) -> None:
    """Register a boundary-query seam owned by a future subsystem."""
    _EVENT_SOURCES[kind] = source


def _settle_boundary_stages(start_tick: int, end_tick: int, entities: tuple[Any, ...]) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = []
    start_day, end_day = start_tick // _DAY_SECONDS, end_tick // _DAY_SECONDS
    for day in range(start_day + 1, end_day + 1):
        for entity in entities:
            if getattr(entity, "sexual", None) is not None:
                reset_daily_counters(entity)
        events.append(ScheduledEvent("daily_reset", day * _DAY_SECONDS, {}))
    for kind in _STAGE_ORDER[5:]:
        source = _EVENT_SOURCES.get(kind)
        if source is not None:
            events.extend(source(start_tick, end_tick))
    return events


def _run_stages(clock: "WorldClock", seconds: int, source: AdvanceSource, entities: tuple[Any, ...]) -> list[ScheduledEvent]:
    _settle_gauge_regen(entities, seconds)
    if source is not AdvanceSource.COMBAT:
        _settle_buffs_and_decay(entities, seconds)
        _try_accrue_magic_study(entities, seconds, source)
    return _settle_boundary_stages(clock.tick, clock.tick + seconds, entities)


@dataclass
class WorldClock:
    """The sole mutable driver of elapsed game time."""

    tick: int = 0

    @property
    def calendar(self) -> WorldDateTime:
        return WorldDateTime.from_tick(self.tick)

    def advance(self, seconds: int, source: AdvanceSource, entities: Iterable[Any]) -> list[ScheduledEvent]:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        scope = tuple(entities)
        events = _run_stages(self, seconds, source, scope)
        self.tick += seconds
        persist = getattr(self, "_persist", None)
        if persist is not None:
            persist(self.tick)
        return events


class WorldClockScript(DefaultScript):
    """Persistent attribute storage for the player-driven world tick."""

    def at_script_creation(self) -> None:
        self.db.tick = 0


def get_world_clock() -> WorldClock:
    """Find or create the non-repeating persisted clock singleton."""
    matches = search_script("world_clock")
    script = matches[0] if matches else create_script(
        WorldClockScript, key="world_clock", persistent=True, interval=0, repeats=0
    )
    clock = WorldClock(int(script.db.tick or 0))
    clock._persist = lambda tick: setattr(script.db, "tick", tick)
    return clock


def settle_combat_result(result: Any, entities: Iterable[Any]) -> list[ScheduledEvent]:
    """Settle a reported combat duration through the combat source gate."""
    return get_world_clock().advance(result.total_seconds, AdvanceSource.COMBAT, entities)
