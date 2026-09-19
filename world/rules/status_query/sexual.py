"""No-create sexual-state readers: ordered levels, counters, intimate view.

Every helper interprets the persisted ``sexual_traits`` record or the
import-time baseline in memory and fails closed with
:class:`StatusQueryError`; none ever creates ``entity.sexual``.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.equipment_effects import effective_exposure
from world.rules.sexual_state import PLEASURE_CONFIG
from world.rules.stored_sexual_reads import StoredLevel

from .models import (
    _SEXUAL_TRAITS_CATEGORY,
    _SEXUAL_TRAITS_KEY,
    IntimateView,
    StatusQueryError,
    _LevelRef,
)
from .readers import _read_attribute


def _sexual_level(entity: Any, field: str) -> Any:
    """Read one ordered-level or counter trait in memory without a handler.

    Returns a read-only :class:`_LevelRef` for ordinal comparison, the stored
    level string when only a baseline is available, or ``None`` when the
    record is entirely absent. A baseline field the seed intentionally omitted
    (``PresetSexualBaseline.to_record`` and the import card keep optionals
    absent, floored later by ``SexualState._build_from_baseline``) resolves to
    ``None`` exactly like ``stored_sexual_reads.stored_sexual_level``, so the
    panel's condition chips can never disagree with the combat no-create path.
    A present-but-malformed record fails closed. Never creates ``entity.sexual``.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if field == "arousal":
        if isinstance(traits, Mapping) and "pleasure" in traits:
            raw = traits["pleasure"]
            base = raw.get("base") if isinstance(raw, Mapping) else None
            if isinstance(base, int) and not isinstance(base, bool):
                # Defensive: CounterTrait.base's own setter clamps writes into
                # [0, 100], so an out-of-range stored value implies corrupted
                # storage; clamp it so the ordinal lookup still resolves.
                base = min(100, max(0, base))
                return _LevelRef(
                    PLEASURE_CONFIG.ordinal_for(base), AROUSAL_LEVELS
                )
            return None
    elif isinstance(traits, Mapping) and field in traits:
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
    if not isinstance(baseline, Mapping):
        raise StatusQueryError(f"sexual state {field!r} is malformed")
    value = baseline.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise StatusQueryError(f"sexual state {field!r} is malformed")
    return value


def _ordinal_of(levels: tuple[str, ...], label: str) -> int:
    try:
        return levels.index(label)
    except ValueError as error:
        raise StatusQueryError(f"unknown level {label!r}") from error


_INTIMATE_LEVEL_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wetness", WETNESS_LEVELS),
    ("shame", SHAME_LEVELS),
    ("exposure", EXPOSURE_LEVELS),
    ("climax_phase", CLIMAX_PHASE_LEVELS),
)


def _sexual_counter(entity: Any, field: str) -> int | None:
    """Read one sexual counter trait in memory without a handler.

    Reads the materialized ``sexual_traits`` entry the same way
    ``_require_static_trait`` prefers ``raw.get("current", raw.get("base"))``.
    Absent a materialized record, falls back to the baseline's ``climax_today``
    (default ``0`` when the key is missing), or ``None`` when no record exists
    at all. A present-but-malformed record fails closed. Never creates
    ``entity.sexual``.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if not isinstance(raw, Mapping):
            raise StatusQueryError(f"sexual counter {field!r} is malformed")
        value = raw.get("current", raw.get("base"))
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StatusQueryError(f"sexual counter {field!r} is malformed")
        return value
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping):
        raise StatusQueryError("sexual baseline is malformed")
    value = baseline.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StatusQueryError(f"sexual baseline {field!r} is malformed")
    return value


def _validate_intimate_level_entry(raw: Any, vocabulary: tuple[str, ...]) -> str:
    """Strictly validate one materialized ordered-level entry, fail-closed."""
    if not isinstance(raw, Mapping):
        raise StatusQueryError("materialized sexual level entry is malformed")
    levels = raw.get("levels")
    # Evennia deserializes nested lists as `_SaverList` (a MutableSequence,
    # not a list/tuple), so accept any non-str sequence and compare its
    # contents against the field's fixed vocabulary.
    if isinstance(levels, str) or not isinstance(levels, Sequence) or tuple(levels) != vocabulary:
        raise StatusQueryError(
            f"materialized sexual level entry levels do not match the fixed vocabulary"
        )
    value = raw.get("value")
    if isinstance(value, bool):
        raise StatusQueryError("materialized sexual level value must not be a boolean")
    if isinstance(value, int) and 0 <= value < len(vocabulary):
        return vocabulary[value]
    if isinstance(value, str) and value in vocabulary:
        return value
    raise StatusQueryError("materialized sexual level value is malformed")


def _effective_exposure_label(entity: Any, stored_label: str) -> str:
    """Return the effective exposure label, falling back to the stored one.

    The equipment overlay (P4 D4) never fails closed on the panel: strict
    stored validation has already passed when this runs, so a view that
    cannot be resolved simply keeps the stored label.
    """
    view = effective_exposure(entity)
    if isinstance(view, StoredLevel) and tuple(view.levels) == EXPOSURE_LEVELS:
        return view.levels[view.value]
    return stored_label


def _read_intimate(entity: Any) -> IntimateView | None:
    """Build the intimate view from no-create-safe readers, or return None.

    A materialized ``sexual_traits`` record must be complete (the ``SexualState``
    handler always writes every intimate entry, so a missing entry is
    corruption that fails the panel closed, never a silent baseline fallback).
    Absent a materialized record, level fields resolve from the import-time
    baseline; a level field the baseline seed omitted floors to its
    vocabulary's lowest level — the exact value ``SexualState``'s baseline
    construction will materialize for it — and absent both records, the whole
    view is ``None``.

    The exposure row renders the EFFECTIVE level (stored ordinal plus worn
    equipment ``exposure_bias``, clamped) while the stored trait is never
    touched; every other row keeps the stored value.
    """
    traits = _read_attribute(
        entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping):
        required = ("pleasure", "climax_today") + tuple(field for field, _ in _INTIMATE_LEVEL_FIELDS)
        for field in required:
            if field not in traits:
                raise StatusQueryError(f"materialized sexual state is missing {field!r}")
        pleasure = traits["pleasure"]
        if not isinstance(pleasure, Mapping):
            raise StatusQueryError("materialized pleasure counter is malformed")
        base = pleasure.get("base")
        if isinstance(base, bool) or not isinstance(base, int) or not 0 <= base <= 100:
            raise StatusQueryError("materialized pleasure counter base is malformed")
        values = {"arousal": AROUSAL_LEVELS[PLEASURE_CONFIG.ordinal_for(base)]}
        for field, vocabulary in _INTIMATE_LEVEL_FIELDS:
            values[field] = _validate_intimate_level_entry(traits[field], vocabulary)
        return IntimateView(
            arousal=values["arousal"],
            wetness=values["wetness"],
            shame=values["shame"],
            exposure=_effective_exposure_label(entity, values["exposure"]),
            climax_phase=values["climax_phase"],
            climax_today=_sexual_counter(entity, "climax_today"),
        )
    baseline = _read_attribute(entity, "sexual", default=None)
    if baseline is None:
        return None
    if not isinstance(baseline, Mapping):
        raise StatusQueryError("sexual baseline is malformed")
    values = {}
    for field, vocabulary in (("arousal", AROUSAL_LEVELS), *_INTIMATE_LEVEL_FIELDS):
        value = baseline.get(field)
        if value is None:
            # Omitted optional levels are legal on an import/preset seed and
            # floor exactly as SexualState._build_from_baseline seeds them.
            values[field] = vocabulary[0]
        elif isinstance(value, str) and value in vocabulary:
            values[field] = value
        else:
            raise StatusQueryError(f"sexual baseline {field!r} is malformed")
    climax_today = _sexual_counter(entity, "climax_today")
    if climax_today is None:
        return None
    return IntimateView(
        arousal=values["arousal"],
        wetness=values["wetness"],
        shame=values["shame"],
        exposure=_effective_exposure_label(entity, values["exposure"]),
        climax_phase=values["climax_phase"],
        climax_today=climax_today,
    )
