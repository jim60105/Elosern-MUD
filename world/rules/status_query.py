"""Frozen no-create status read model for the WebClient status presenter.

Presentation must never materialize lazy handlers or default state. This module
reads only the persistent trait attribute, optional buff cache, sexual baseline
or materialized traits, creation flag, disguise record, and combat-session
record, and interprets them in memory. It never constructs ``entity.traits``,
``entity.buffs``, or ``entity.sexual`` and never writes to storage.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import matched_combat_modifiers
from world.rules.sexual_state import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS
from world.rules.status_display import display_for

_GAUGE_KEYS = ("hp", "mp", "sp")
_BUFF_CACHE_KEY = "buffs"
_SEXUAL_TRAITS_KEY = "sexual_traits"
_SEXUAL_TRAITS_CATEGORY = "traits"


class StatusQueryError(ValueError):
    """Required canonical state is missing, malformed, or could not be read."""


@dataclass(frozen=True)
class GaugeValue:
    current: int
    maximum: int


@dataclass(frozen=True)
class _LevelRef:
    """Read-only ordinal comparison mirror for an ordered level trait."""

    value: int
    levels: tuple[str, ...]

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, _LevelRef):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._ordinal_of(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other: object) -> bool:
        return self.value < self._ordinal_of(other)


@dataclass(frozen=True)
class ConditionValue:
    code: str
    label: str
    severity: str
    remaining_seconds: int | None
    modifiers: dict[str, Any]


@dataclass(frozen=True)
class StatusReadModel:
    """The complete read-only inputs a presenter may serialize."""

    actor_name: str
    actor_identity: str
    location_label: str | None
    location_identity: str | None
    resources: dict[str, GaugeValue]
    conditions: tuple[ConditionValue, ...]
    disguise_active: bool
    combat_mode: str | None
    combat_round: int | None
    creation_pending: bool


def _read_attribute(entity: Any, key: str, default=None, category: str | None = None) -> Any:
    return entity.attributes.get(key, default=default, category=category)


def _require_gauge(data: dict[str, Any], key: str) -> GaugeValue:
    """Read one gauge trait dict strictly without constructing a handler."""
    raw = data.get(key)
    if not isinstance(raw, Mapping):
        raise StatusQueryError(f"missing gauge trait {key!r}")
    base = raw.get("base")
    mod = raw.get("mod", 0)
    mult = raw.get("mult", 1)
    if isinstance(base, bool) or not isinstance(base, int):
        raise StatusQueryError(f"gauge {key!r} base is not an integer")
    if isinstance(mod, bool) or not isinstance(mod, (int, float)):
        raise StatusQueryError(f"gauge {key!r} mod is not numeric")
    if isinstance(mult, bool) or not isinstance(mult, (int, float)):
        raise StatusQueryError(f"gauge {key!r} mult is not numeric")
    maximum = int(round((base + mod) * mult))
    if maximum <= 0:
        raise StatusQueryError(f"gauge {key!r} has a non-positive maximum")
    current = raw.get("current")
    if current is None:
        # GaugeTrait defaults an unset current to full.
        current = maximum
    if isinstance(current, bool) or not isinstance(current, int):
        raise StatusQueryError(f"gauge {key!r} current is not an integer")
    if current < 0:
        raise StatusQueryError(f"gauge {key!r} current is negative")
    if current > maximum:
        raise StatusQueryError(f"gauge {key!r} current exceeds maximum")
    return GaugeValue(current=current, maximum=maximum)


def _read_buff_cache(entity: Any) -> dict[str, Any]:
    """Return the persisted buff cache dict without creating a handler."""
    cache = _read_attribute(entity, _BUFF_CACHE_KEY, default={})
    if cache is None:
        return {}
    if not isinstance(cache, Mapping):
        raise StatusQueryError("buff cache is malformed")
    return dict(cache)


def _active_buff_entries(entity: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return unpaused, positive-stack, unexpired buff cache entries."""
    entries: list[tuple[str, dict[str, Any]]] = []
    for buff_key, cache in _read_buff_cache(entity).items():
        if not isinstance(cache, Mapping):
            raise StatusQueryError(f"buff {buff_key!r} cache is malformed")
        cache = dict(cache)
        if cache.get("paused"):
            continue
        stacks = cache.get("stacks")
        if not isinstance(stacks, int) or stacks <= 0:
            continue
        remaining = cache.get("remaining_seconds")
        if isinstance(remaining, int) and remaining <= 0:
            continue
        entries.append((buff_key, cache))
    return entries


def _sexual_level(entity: Any, field: str) -> Any:
    """Read one ordered-level or counter trait in memory without a handler.

    Returns a read-only :class:`_LevelRef` for ordinal comparison, the stored
    level string when only a baseline is available, or ``None`` when the
    record is entirely absent. A present-but-malformed record fails closed.
    Never creates ``entity.sexual``.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if isinstance(raw, Mapping):
            value = raw.get("value")
            levels = raw.get("levels") or ()
            if isinstance(value, str):
                return _LevelRef(_ordinal_of(levels, value), tuple(levels)) if levels else value
            if isinstance(value, int):
                if isinstance(levels, (list, tuple)) and 0 <= value < len(levels):
                    return _LevelRef(value, tuple(levels))
            return value
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping) or not isinstance(baseline.get(field), str):
        raise StatusQueryError(f"sexual state {field!r} is malformed")
    return baseline[field]


def _ordinal_of(levels: tuple[str, ...], label: str) -> int:
    try:
        return levels.index(label)
    except ValueError as error:
        raise StatusQueryError(f"unknown level {label!r}") from error


def _sexual_condition_context(entity: Any) -> dict[str, Any]:
    """Build the combat-modifier condition context from read-only state."""
    context: dict[str, Any] = {"active_buffs": {key for key, _ in _active_buff_entries(entity)}}
    for field, levels in (("arousal", AROUSAL_LEVELS), ("climax_phase", CLIMAX_PHASE_LEVELS)):
        value = _sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _LevelRef(_ordinal_of(levels, value), levels)
        elif isinstance(value, _LevelRef):
            context[field] = value
    return context


def _read_combat(entity: Any) -> tuple[str, int] | None:
    """Read the persistent combat-session record without resolving entities."""
    raw = _read_attribute(entity, "active_combat", default=None)
    if raw is None:
        return None
    if not isinstance(raw, dict) and not isinstance(raw, Mapping):
        raise StatusQueryError("active combat record is malformed")
    mode = raw.get("mode")
    rounds = raw.get("rounds_elapsed")
    if mode not in {"hostile", "guild_exam"}:
        raise StatusQueryError("active combat mode is invalid")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        raise StatusQueryError("active combat round is invalid")
    return mode, rounds


def build_status_read_model(entity: Any) -> StatusReadModel:
    """Build the frozen read model or raise :class:`StatusQueryError`.

    Requires exactly the HP, MP, and SP gauges; other required data that is
    missing or malformed also fails closed so the presenter shows unavailable
    rather than fabricating values.
    """
    traits_data = _read_attribute(
        entity, "traits", default=None, category="traits"
    )
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)
    resources = {key: _require_gauge(traits_data, key) for key in _GAUGE_KEYS}

    conditions: list[ConditionValue] = []
    for buff_key, cache in _active_buff_entries(entity):
        definition_key = cache.get("definition_key")
        if not isinstance(definition_key, str) or definition_key not in BUFF_DEFINITIONS:
            raise StatusQueryError(f"buff {buff_key!r} has an unknown definition")
        display = display_for(definition_key)
        conditions.append(
            ConditionValue(
                code=definition_key,
                label=display.label,
                severity=display.severity,
                remaining_seconds=cache.get("remaining_seconds"),
                modifiers={},
            )
        )

    # Deterministic combat-modifier matches, read-only.
    context = _sexual_condition_context(entity)
    for rule_id, adjustments in matched_combat_modifiers(entity, context=context):
        display = display_for(rule_id)
        conditions.append(
            ConditionValue(
                code=rule_id,
                label=display.label,
                severity=display.severity,
                remaining_seconds=None,
                modifiers=dict(adjustments),
            )
        )

    combat = _read_combat(entity)
    identity = str(entity.pk)
    location = getattr(entity, "location", None)
    return StatusReadModel(
        actor_name=str(getattr(entity, "key", "?")),
        actor_identity=identity,
        location_label=None if location is None else str(location.key),
        location_identity=None if location is None else str(location.pk),
        resources=resources,
        conditions=tuple(conditions),
        disguise_active=bool(_read_attribute(entity, "disguised_stats", default=None)),
        combat_mode=None if combat is None else combat[0],
        combat_round=None if combat is None else combat[1],
        creation_pending=bool(getattr(entity, "creation_pending", False)),
    )
