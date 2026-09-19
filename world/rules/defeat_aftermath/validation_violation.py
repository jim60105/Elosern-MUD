"""Validator for the ``violation`` archetype section.

defeat-aftermath-violation-sequence D-V2.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
from pathlib import Path
from types import MappingProxyType
from typing import Any

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.rules.clock import MAX_ADVANCE_SECONDS
from world.rules.defeat_aftermath.contracts import (
    ArchetypeViolationRow,
    ViolationConfig,
    ViolationDeltas,
)
from world.rules.sexual_act_effects import mutator_name_for
from world.rules.sexual_state import AROUSAL_LEVELS


_VIOLATION_ROW_KEYS = frozenset(
    {
        "victory_pleasure_delta",
        "threshold_ordinal",
        "attempt_cap",
        "attempt_duration_seconds",
        "landed_deltas",
        "resisted_deltas",
        "credited_counters",
    }
)
_VIOLATION_DELTA_KEYS = ("victim_pleasure", "aggressor_pleasure")
# The direction-bound counters record what one body did or underwent alone;
# crediting an aggressor or victim with them would corrupt their meaning
# (sexual-counter-symmetric-crediting D-1), so a row may never declare them.
_DIRECTION_BOUND_COUNTERS = frozenset(
    {"exposure_act_count", "watched_count", "masturbation_count"}
)


def _require_non_negative_int(value: Any, path: Path, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{path}: violation {label} must be a non-negative integer, got {value!r}")
    return int(value)


def _validate_violation_deltas(
    raw: Any, path: Path, label: str
) -> ViolationDeltas:
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            f"{path}: violation {label} must be a non-empty mapping of "
            f"{list(_VIOLATION_DELTA_KEYS)}"
        )
    unknown = set(raw) - set(_VIOLATION_DELTA_KEYS)
    if unknown:
        raise ValueError(
            f"{path}: violation {label} has unknown keys {sorted(unknown)}"
        )
    values = {
        key: _require_non_negative_int(raw.get(key, 0), path, f"{label}.{key}")
        for key in _VIOLATION_DELTA_KEYS
    }
    return ViolationDeltas(**values)


def _validate_violation(raw: dict[str, Any], path: Path) -> ViolationConfig:
    """Validate the ``violation`` section fail-closed (DA4 D-V2).

    Archetype keys are the lore bestiary's monster species names
    (``MONSTER_TIER_REGISTRY`` ``example_monsters_zh`` — the durable identity
    a wilderness population monster carries as its key), so an unpublished
    species can never enter the balance table unnoticed. A ``shame`` key is
    rejected outright: a Monster's shame bounds are pinned at the floor by
    construction, and no archetype row may set shame (D-V2).
    """
    section = raw.get("violation")
    if not isinstance(section, dict):
        raise ValueError(f"{path}: section 'violation' must be a mapping")
    wake_line = section.get("violated_wake_line")
    if not isinstance(wake_line, str) or not wake_line.strip():
        raise ValueError(
            f"{path}: violation violated_wake_line must be a non-empty string"
        )
    archetypes = section.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise ValueError(
            f"{path}: violation archetypes must be a non-empty mapping"
        )
    lore_species = frozenset(
        name
        for tier in MONSTER_TIER_REGISTRY.values()
        for name in tier.example_monsters_zh
    )
    rows: dict[str, ArchetypeViolationRow] = {}
    for key, raw_row in archetypes.items():
        if key not in lore_species:
            raise ValueError(
                f"{path}: violation archetype {key!r} is not a lore monster "
                "species name"
            )
        if not isinstance(raw_row, dict):
            raise ValueError(
                f"{path}: violation archetype {key!r} must be a mapping"
            )
        if "shame" in raw_row:
            raise ValueError(
                f"{path}: violation archetype {key!r} may not declare shame "
                "(a monster's shame bounds are pinned at the floor, D-V2)"
            )
        unknown = set(raw_row) - _VIOLATION_ROW_KEYS
        if unknown:
            raise ValueError(
                f"{path}: violation archetype {key!r} has unknown keys {sorted(unknown)}"
            )
        threshold = _require_non_negative_int(
            raw_row.get("threshold_ordinal"), path, f"{key}.threshold_ordinal"
        )
        if threshold > len(AROUSAL_LEVELS) - 1:
            raise ValueError(
                f"{path}: violation {key}.threshold_ordinal must be an arousal "
                f"ordinal in [0, {len(AROUSAL_LEVELS) - 1}], got {threshold!r}"
            )
        cap = _require_non_negative_int(
            raw_row.get("attempt_cap"), path, f"{key}.attempt_cap"
        )
        if cap < 1:
            raise ValueError(
                f"{path}: violation {key}.attempt_cap must be at least 1"
            )
        duration = _require_non_negative_int(
            raw_row.get("attempt_duration_seconds"),
            path,
            f"{key}.attempt_duration_seconds",
        )
        if not 1 <= duration <= MAX_ADVANCE_SECONDS:
            raise ValueError(
                f"{path}: violation {key}.attempt_duration_seconds must be an "
                f"integer in [1, {MAX_ADVANCE_SECONDS}]"
            )
        counters_raw = raw_row.get("credited_counters")
        if (
            not isinstance(counters_raw, list)
            or not counters_raw
            or any(not isinstance(name, str) for name in counters_raw)
        ):
            raise ValueError(
                f"{path}: violation {key}.credited_counters must be a non-empty "
                "list of counter names"
            )
        if len(set(counters_raw)) != len(counters_raw):
            raise ValueError(
                f"{path}: violation {key}.credited_counters repeats a counter "
                "name; a repeated name would double-credit one act"
            )
        for name in counters_raw:
            if name in _DIRECTION_BOUND_COUNTERS:
                raise ValueError(
                    f"{path}: violation {key} may not credit the direction-bound "
                    f"counter {name!r} symmetrically"
                )
            try:
                mutator_name_for(name)
            except ValueError as error:
                raise ValueError(
                    f"{path}: violation {key} credits unknown counter {name!r}"
                ) from error
        rows[key] = ArchetypeViolationRow(
            archetype=key,
            victory_pleasure_delta=_require_non_negative_int(
                raw_row.get("victory_pleasure_delta"),
                path,
                f"{key}.victory_pleasure_delta",
            ),
            threshold_ordinal=threshold,
            attempt_cap=cap,
            attempt_duration_seconds=duration,
            landed=_validate_violation_deltas(
                raw_row.get("landed_deltas"), path, f"{key}.landed_deltas"
            ),
            resisted=_validate_violation_deltas(
                raw_row.get("resisted_deltas"), path, f"{key}.resisted_deltas"
            ),
            credited_counters=tuple(counters_raw),
        )
    return ViolationConfig(
        rows=MappingProxyType(rows),
        violated_wake_line=wake_line,
    )
