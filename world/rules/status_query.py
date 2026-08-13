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

# Stable Traditional Chinese labels for the canonical trait keys, shared by
# every presentation surface: the WebClient character panel and the
# displayed-stats block appended on ``look <target>`` (displayed-stats-view
# A2). Consumers must read this map instead of duplicating the labels.
TRAIT_LABELS = {
    "hp": "生命",
    "mp": "魔力",
    "sp": "耐力",
    "atk_phys": "攻擊",
    "agility": "敏捷",
    "defense": "防禦",
    "magic_level": "魔法階級",
    "guild_merit": "功績",
}

_GAUGE_KEYS = ("hp", "mp", "sp")
_STATIC_KEYS = ("atk_phys", "agility", "defense")
_COUNTER_KEYS = ("magic_level", "guild_merit")
_EQUIPMENT_SLOTS = ("weapon_main", "weapon_off", "armor")
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


@dataclass(frozen=True)
class CharacterTraitView:
    """One read-only character trait row: gauges report current/maximum."""

    key: str
    current: int
    maximum: int | None


@dataclass(frozen=True)
class CharacterEquipmentView:
    """One read-only equipped item row (slot plus canonical item key)."""

    slot: str
    item_key: str


@dataclass(frozen=True)
class CharacterReadModel:
    """The complete read-only inputs of the version-1 ``character`` panel.

    Shares the same canonical trait storage the compact ``status`` panel reads,
    so the two panels cannot drift apart: gauges go through the same strict
    ``_require_gauge`` parser and statics/counters through the same trait dict.
    Every value is true state; ``disguise_displayed`` is reported separately
    and is never substituted for a true trait.
    """

    traits: tuple[CharacterTraitView, ...]
    passive_keys: tuple[str, ...]
    equipment: tuple[CharacterEquipmentView, ...]
    disguise_active: bool
    disguise_displayed: tuple[tuple[str, int], ...]
    guild_rank: str | None
    guild_merit: int
    wallet: int


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
    context["entity"] = entity
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


def _require_static_trait(traits_data: dict[str, Any], key: str) -> int:
    raw = traits_data.get(key)
    if not isinstance(raw, Mapping):
        raise StatusQueryError(f"trait {key!r} is missing")
    base = raw.get("current", raw.get("base"))
    if isinstance(base, bool) or not isinstance(base, int):
        raise StatusQueryError(f"trait {key!r} base is not an integer")
    return base


def _read_guild_merit(traits_data: dict[str, Any]) -> int:
    merit = _require_static_trait(traits_data, "guild_merit")
    if merit < 0:
        raise StatusQueryError("guild_merit is negative")
    return merit


def _read_passive_keys(entity: Any) -> tuple[str, ...]:
    raw = entity.db.skills
    if not isinstance(raw, Mapping):
        return ()
    passive = raw.get("passive")
    if not _is_list_like(passive):
        return ()
    return tuple(str(key) for key in passive if isinstance(key, str) and key)


def _is_list_like(value: Any) -> bool:
    """Whether ``value`` behaves like a bounded sequence of elements.

    Evennia deserializes stored lists as ``_SaverList`` (a
    ``MutableSequence``, not a ``list`` subclass), so the check must accept any
    non-string sequence.
    """
    from collections.abc import Sequence

    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _read_equipment(entity: Any) -> tuple[CharacterEquipmentView, ...]:
    raw = entity.db.equipment
    if not isinstance(raw, Mapping):
        return ()
    rows: list[CharacterEquipmentView] = []
    for slot in _EQUIPMENT_SLOTS:
        value = raw.get(slot)
        if isinstance(value, str) and value:
            rows.append(CharacterEquipmentView(slot, value))
    accessories = raw.get("accessories")
    if _is_list_like(accessories):
        for value in accessories:
            if isinstance(value, str) and value:
                rows.append(CharacterEquipmentView("accessory", value))
    return tuple(rows)


def _read_disguise(entity: Any) -> tuple[bool, tuple[tuple[str, int], ...]]:
    raw = _read_attribute(entity, "disguised_stats", default=None)
    if raw is None:
        return False, ()
    if not isinstance(raw, Mapping):
        raise StatusQueryError("disguised_stats is malformed")
    displayed: list[tuple[str, int]] = []
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise StatusQueryError("disguised_stats key is malformed")
        if isinstance(value, bool) or not isinstance(value, int):
            raise StatusQueryError(f"disguised_stats {key!r} is not an integer")
        displayed.append((key, value))
    displayed.sort(key=lambda entry: entry[0])
    return True, tuple(displayed)


def _read_wallet(entity: Any) -> int:
    raw = entity.db.wallet
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise StatusQueryError("wallet is malformed")
    return raw


def build_character_read_model(entity: Any) -> CharacterReadModel:
    """Build the frozen character read model or raise :class:`StatusQueryError`.

    Reads the same canonical trait dict the status model reads, so the expanded
    character surface and the compact status surface agree on every shared
    value. Equipment, disguise, guild, and wallet are read strictly and fail
    closed when malformed; no handler is materialized and nothing is written.
    """
    traits_data = _read_attribute(
        entity, "traits", default=None, category="traits"
    )
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)

    traits: list[CharacterTraitView] = []
    for key in _GAUGE_KEYS:
        gauge = _require_gauge(traits_data, key)
        traits.append(CharacterTraitView(key, gauge.current, gauge.maximum))
    for key in _STATIC_KEYS + _COUNTER_KEYS:
        traits.append(CharacterTraitView(key, _require_static_trait(traits_data, key), None))

    disguise_active, disguise_displayed = _read_disguise(entity)
    return CharacterReadModel(
        traits=tuple(traits),
        passive_keys=_read_passive_keys(entity),
        equipment=_read_equipment(entity),
        disguise_active=disguise_active,
        disguise_displayed=disguise_displayed,
        guild_rank=getattr(entity, "guild_rank", None),
        guild_merit=_read_guild_merit(traits_data),
        wallet=_read_wallet(entity),
    )
