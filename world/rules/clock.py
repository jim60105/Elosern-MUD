"""Player-driven deterministic world time and settlement ordering."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import floor, gcd
from pathlib import Path
from typing import Any

import yaml
from django.db import transaction
from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

from world.rules.buffs import BUFF_DEFINITIONS, tick_buffs
from world.rules.sexual_state import (
    DECAY_CONFIG,
    PLEASURE_CONFIG,
    decay_tick,
    reset_daily_counters,
)
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
from world.rules.traits import GAUGE_KEYS


CLOCK_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "clock.yaml").read_text(encoding="utf-8")
)
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

# A single advance may cover at most one full game day: this keeps ``wait
# until``'s worst case (a day-long wait) legal while bounding the per-day
# boundary loop at one crossing per call.
MAX_ADVANCE_SECONDS = _DAY_SECONDS


def _validate_settlement_intervals(buff_definitions, decay_config) -> int:
    """Validate every settlement interval, returning their greatest common divisor."""
    intervals = [
        definition.tick_interval
        for definition in buff_definitions.values()
        if definition.tick_interval is not None
    ] + [config["interval_seconds"] for config in decay_config.values()]
    if any(not isinstance(interval, int) or interval <= 0 for interval in intervals):
        raise ValueError(f"invalid settlement interval: {intervals!r}")
    return gcd(*intervals)


SETTLEMENT_QUANTUM_SECONDS = _validate_settlement_intervals(BUFF_DEFINITIONS, DECAY_CONFIG)
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
    "instance_reclamation",
)


@dataclass
class SurfaceSnapshot:
    """One object's durable pre-advance state, captured by a pure read.

    ``attributes`` maps ``(key, category)`` to ``(existed, deepcopy(value))``
    exactly as the shared ``attribute_snapshot`` helper returns. ``location``
    is ``(existed, pre-advance db_location pk)`` when the declaring source may
    move the object: the location is stored as a plain primary key, never a
    live object, because a room deleted inside the rolled-back transaction has
    ``pk = None`` on its stale instance and restoring ``db_location`` from that
    instance would orphan the moved occupant.
    """

    attributes: dict[tuple[str, str | None], tuple[bool, Any]]
    location: tuple[bool, int] | None = None


@dataclass(frozen=True)
class EventSourceRegistration:
    """One registered boundary-stage source plus its advance-surface contract.

    ``surfaces`` is ``None`` for a read-only seam (or a test/synthetic
    source): ``advance()`` performs no snapshot or restore for it.
    """

    settle: Callable[[int, int], list["ScheduledEvent"]]
    surfaces: Callable[[int, int], Mapping[int, SurfaceSnapshot]] | None = None


_EVENT_SOURCES: dict[str, EventSourceRegistration] = {}


class DaypartError(ValueError):
    """Raised when a named clock daypart is unknown."""


class ClockAdvanceBoundError(ValueError):
    """Raised when an advance would exceed ``MAX_ADVANCE_SECONDS``."""


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
            # Gauge storage is integral (the status read model rejects floats),
            # so each gauge keeps a sub-unit regen remainder. Accruing in
            # float keeps segmented advances (two moves) equal to one advance
            # of the same total duration: floor(lost) + floor(lost) == floor(2*lost)
            # only when the per-advance fraction is carried, never dropped.
            carried = float(getattr(gauge, "regen_remainder", 0.0))
            continuous = _gauge_value(gauge) + carried + rate * elapsed_seconds
            if continuous >= maximum:
                gauge.current = round(maximum)
                gauge.regen_remainder = 0.0
            else:
                whole = floor(continuous)
                gauge.current = whole
                gauge.regen_remainder = continuous - whole


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
    for field, config in DECAY_CONFIG.items():
        if config.get("only_from") is not None and getattr(
            sexual, field
        ).level != config["only_from"]:
            continue
        trait = getattr(sexual, field)
        level = getattr(trait, "level", None)
        if level is not None:
            if level != config["floor"]:
                return True
        elif trait.value != PLEASURE_CONFIG.floor_for_level(config["floor"]):
            # Counter fields (pleasure) have no level vocabulary; the band
            # table's floor is their resting point.
            return True
    return False


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


def register_event_source(
    kind: str,
    source: Callable[[int, int], list[ScheduledEvent]],
    surfaces: Callable[[int, int], Mapping[int, SurfaceSnapshot]] | None = None,
) -> None:
    """Register a boundary-query seam owned by a future subsystem.

    ``surfaces`` is the optional advance-surface contract: a pure, read-only
    callable ``(start_tick, end_tick) -> mapping[id(obj), SurfaceSnapshot]``
    that re-discovers, with the same deterministic queries its settlement
    uses, every object the source may write and snapshots each durable
    surface. A source that writes durable state SHALL ship a contract; a
    source registered with ``surfaces=None`` is a read-only seam (or a test
    seam) and is never snapshotted or restored by ``advance()``.
    """
    _EVENT_SOURCES[kind] = EventSourceRegistration(source, surfaces)


def _settle_boundary_stages(start_tick: int, end_tick: int, entities: tuple[Any, ...]) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = []
    start_day, end_day = start_tick // _DAY_SECONDS, end_tick // _DAY_SECONDS
    for day in range(start_day + 1, end_day + 1):
        for entity in entities:
            if getattr(entity, "sexual", None) is not None:
                reset_daily_counters(entity)
        events.append(ScheduledEvent("daily_reset", day * _DAY_SECONDS, {}))
    for kind in _STAGE_ORDER[5:]:
        registration = _EVENT_SOURCES.get(kind)
        if registration is not None:
            events.extend(registration.settle(start_tick, end_tick))
    return events


def _run_stages(clock: "WorldClock", seconds: int, source: AdvanceSource, entities: tuple[Any, ...]) -> list[ScheduledEvent]:
    _settle_gauge_regen(entities, seconds)
    if source is not AdvanceSource.COMBAT:
        _settle_buffs_and_decay(entities, seconds)
        _try_accrue_magic_study(entities, seconds, source)
    return _settle_boundary_stages(clock.tick, clock.tick + seconds, entities)


# Durable attribute surfaces an advance can write on a caller-supplied entity:
# the shared entity-snapshot set (world/rules/action.py) plus the
# sexual-decay accumulators, so a rolled-back advance restores every cache.
_ADVANCE_ENTITY_SURFACES: tuple[tuple[str, str | None], ...] = (
    ("traits", "traits"),
    ("disguised_stats", None),
    ("sexual_traits", "traits"),
    ("virgin", "sexual_state"),
    ("experience_types", "sexual_state"),
    ("buffs", None),
    ("skill_grants", None),
    ("magic_xp", None),
    ("skill_proficiency", None),
) + tuple((f"decay_elapsed__{field}", "sexual_state") for field in DECAY_CONFIG)


def _snapshot_clock_tick(clock: "WorldClock") -> tuple[int, tuple[bool, Any] | None]:
    """Snapshot the in-memory tick and the persisted tick attribute."""
    script = getattr(clock, "_script", None)
    tick_snapshot = (
        attribute_snapshot(script, "tick") if script is not None else None
    )
    return clock.tick, tick_snapshot


def _restore_clock_tick(
    clock: "WorldClock",
    snapshot: tuple[int, tuple[bool, Any] | None],
) -> None:
    """Restore the in-memory and persisted tick after a rolled-back advance."""
    in_memory_tick, tick_snapshot = snapshot
    clock.tick = in_memory_tick
    script = getattr(clock, "_script", None)
    if script is not None and tick_snapshot is not None:
        restore_attribute_best_effort(script, "tick", tick_snapshot)


def build_advance_snapshot_registry(
    clock: "WorldClock",
    seconds: int,
    source: AdvanceSource,
    entities: Iterable[Any],
) -> dict[int, SurfaceSnapshot]:
    """Build the merged pre-advance snapshot registry, keyed by object id.

    Merges, by object identity: (a) the existing caller-entity surfaces
    (``_ADVANCE_ENTITY_SURFACES``, unchanged), then (b) every registered
    stage kind's advance-surface contract in ``_STAGE_ORDER[5:]`` order. A
    caller-supplied entity that a contract also discovers (a player with a
    due quest, a schedule-tagged NPC) is snapshotted once with the union of
    surfaces. Kinds registered without a contract are skipped entirely, so
    plain advances never run contract DB queries; a raising contract fails
    the advance before any write (fail-closed, no partial state).

    This is the outer-owner seam: an outer ``transaction.atomic()`` wrapping
    ``advance()`` (the movement and cast settlement changes) SHALL build this
    registry before its transaction opens and restore it together with the
    clock-tick snapshot after an outer-commit failure, so callback-owned
    surfaces are covered whichever boundary fails.
    """
    registry: dict[int, SurfaceSnapshot] = {}
    for entity in entities:
        if not hasattr(entity, "attributes"):
            continue
        registry[id(entity)] = SurfaceSnapshot(
            attributes={
                (key, category): attribute_snapshot(entity, key, category)
                for key, category in _ADVANCE_ENTITY_SURFACES
            }
        )
    for kind in _STAGE_ORDER[5:]:
        registration = _EVENT_SOURCES.get(kind)
        if registration is None or registration.surfaces is None:
            continue
        for obj_id, snapshot in registration.surfaces(clock.tick, clock.tick + seconds).items():
            existing = registry.get(obj_id)
            if existing is None:
                registry[obj_id] = snapshot
            else:
                existing.attributes.update(snapshot.attributes)
                if snapshot.location is not None:
                    existing.location = snapshot.location
    return registry


def _flush_deleted_instance(obj: Any) -> None:
    """Force a cached-but-deleted instance out of the idmapper cache.

    ``delete()`` evicts only when ``at_idmapper_flush()`` returns True, which
    ``TypedObject`` overrides to False when the object holds any NAttribute,
    so a deleted instance can survive in the cache with ``pk = None``. The
    next fetch must re-read the rolled-back rows, so the entry is removed by
    identity from the shared instance cache.
    """
    from evennia.objects.models import ObjectDB

    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is None:
        return
    for key, instance in list(cache.items()):
        if instance is obj:
            del cache[key]


def _restore_advance_location(obj: Any, target_pk: int) -> None:
    """Re-point one moved object at its pre-advance room after a rollback.

    The target is re-fetched by its snapshot pk: after the rollback the rows
    are back, and a cached-but-deleted target instance is flushed first so the
    fetch returns a fresh live object. The location setter reconciles the
    source and destination rooms' contents caches; the re-fetched room's
    contents cache is then reset so the next read agrees with the database. A
    vanished target is skipped with a bounded diagnostic.
    """
    from evennia.objects.models import ObjectDB
    from evennia.utils.logger import log_warn

    # A deleted instance that survived eviction stays in the cache under its
    # ORIGINAL pk key (Django nulls ``pk`` only after the collector finishes,
    # so the cached entry can no longer be found by comparing ``pk``); flush
    # it by key so the fetch below re-reads the rolled-back rows.
    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is not None:
        stale = cache.get(target_pk)
        if stale is not None and getattr(stale, "_is_deleted", False):
            _flush_deleted_instance(stale)
    target = ObjectDB.objects.filter(id=target_pk).first()
    if target is None:
        log_warn(
            f"clock advance could not restore {obj} to room #{target_pk}: "
            "the room vanished after rollback"
        )
        return
    obj.location = target
    target.contents_cache.clear()


def _restore_registry_attribute(
    obj: Any,
    key: str,
    category: str | None,
    snapshot: tuple[bool, Any],
) -> None:
    """Restore one registry attribute, degrading to a cache reset on failure.

    Writes the snapshot value directly instead of through the shared
    ``restore_attribute`` deepcopy: a contract surface may embed live database
    objects (the instance contract's ``owned_entities``), which plain
    ``deepcopy`` cannot copy; Evennia's ``attributes.add`` re-encodes through
    ``dbserialize`` and handles them natively.
    """
    from evennia.utils.logger import log_warn

    existed, value = snapshot
    try:
        if existed:
            obj.attributes.add(key, value, category=category)
        else:
            obj.attributes.remove(key, category=category)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:
            pass
        log_warn(f"clock advance could not restore {key!r} on {obj}: {error}")


def _restore_advance_registry(
    registry: dict[int, SurfaceSnapshot],
    entities: Iterable[Any],
) -> None:
    """Restore every registry surface after a rolled-back advance.

    For each registry entry: an object deleted during settlement is skipped
    (its still-cached deleted instance, when NAttributes kept it, is flushed
    so the next fetch re-reads the rolled-back rows); each attribute surface
    is restored; an optional location surface re-fetches the pre-advance room
    by its snapshot pk and assigns it through the location setter. Objects are
    resolved from the caller's own entities first -- a caller-supplied
    instance evicted from the idmapper without deletion (a theoretical
    maintenance path; nothing flushes the cache inside a synchronous
    ``advance()``) is still restored from the caller's reference -- then from
    the idmapper cache for contract-discovered objects. Caller-scope entities
    finish with the existing trait/sexual cache refresh.
    """
    from evennia.objects.models import ObjectDB

    objects: dict[int, Any] = {id(obj): obj for obj in entities}
    objects.update(
        {id(obj): obj for obj in ObjectDB.get_all_cached_instances()}
    )
    for obj_id, snapshot in registry.items():
        obj = objects.get(obj_id)
        if obj is None:
            continue
        if getattr(obj, "_is_deleted", False):
            _flush_deleted_instance(obj)
            continue
        for key, category in snapshot.attributes:
            _restore_registry_attribute(
                obj, key, category, snapshot.attributes[(key, category)]
            )
        if snapshot.location is not None:
            existed, target_pk = snapshot.location
            try:
                if existed:
                    _restore_advance_location(obj, target_pk)
                else:
                    obj.location = None
            except Exception as error:
                from evennia.utils.logger import log_warn

                log_warn(
                    f"clock advance could not restore the location of {obj}: {error}"
                )
    for entity in entities:
        if not hasattr(entity, "attributes"):
            continue
        _refresh_advance_entity_caches(entity)


def _refresh_advance_entity_caches(entity: Any) -> None:
    """Drop stale in-memory trait/sexual caches so the next read matches the DB."""
    from evennia.utils.logger import log_warn

    try:
        entity.traits.trait_data = entity.attributes.get(
            "traits", default={}, category="traits"
        )
        entity.traits._cache.clear()
    except Exception as error:
        log_warn(f"clock advance could not refresh trait caches on {entity}: {error}")
    try:
        entity.__dict__.pop("sexual", None)
    except Exception as error:
        log_warn(f"clock advance could not drop cached sexual state on {entity}: {error}")


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
        if seconds > MAX_ADVANCE_SECONDS:
            raise ClockAdvanceBoundError(
                f"advance of {seconds}s exceeds the {MAX_ADVANCE_SECONDS}s bound"
            )
        scope = tuple(entities)
        registry = build_advance_snapshot_registry(self, seconds, source, scope)
        tick_snapshot = _snapshot_clock_tick(self)
        try:
            with transaction.atomic():
                events = _run_stages(self, seconds, source, scope)
                self.tick += seconds
                persist = getattr(self, "_persist", None)
                if persist is not None:
                    persist(self.tick)
        except Exception:
            _restore_clock_tick(self, tick_snapshot)
            _restore_advance_registry(registry, scope)
            raise
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
    clock._script = script
    clock._persist = lambda tick: setattr(script.db, "tick", tick)
    return clock


def read_world_clock() -> WorldClock | None:
    """Return the existing world-clock singleton or ``None`` without creating.

    Presentation reads only through this accessor; it never calls
    ``get_world_clock``, which would create the Script. A missing singleton is
    reported as absence so presentation can fail safely.
    """
    matches = search_script("world_clock")
    if not matches:
        return None
    script = matches[0]
    clock = WorldClock(int(script.db.tick or 0))
    clock._script = script
    clock._persist = lambda tick: setattr(script.db, "tick", tick)
    return clock


def settle_combat_result(result: Any, entities: Iterable[Any]) -> list[ScheduledEvent]:
    """Settle a reported combat duration through the combat source gate."""
    return get_world_clock().advance(result.total_seconds, AdvanceSource.COMBAT, entities)
