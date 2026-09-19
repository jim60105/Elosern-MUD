"""Validator for the ``digest`` rulebook section.

defeat-aftermath-digest-narrative D-D2.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
from pathlib import Path
from types import MappingProxyType
from typing import Any

from world.lore.sexual_vocab import SENSITIVITY_LEVELS, SHAME_LEVELS
from world.rules.defeat_aftermath.contracts import DigestConfig, DigestRow
from world.rules.sexual_state import AROUSAL_LEVELS


# The digest table's closed schema (defeat-aftermath-digest-narrative D-D2).
# Any condition key outside this frozenset — race, species, persona, or a
# typo — fails the load before the section is consulted, so persona flavor
# can never become a rule input.
_DIGEST_ROW_KEYS = frozenset({"id", "when", "outcome", "buff"})
_DIGEST_CONDITION_KEYS = frozenset(
    {
        "sensitivity_level",
        "shame_level",
        "arousal_ordinal",
        "outcome.climax_count",
        "outcome.zero_landed",
    }
)
_DIGEST_OUTCOMES = frozenset({"residue", "humiliated", "none"})
_DIGEST_CLIMAX_CEILING = 2**31 - 1



def _validate_digest_labels(
    raw: Any, path: Path, label: str, vocabulary: tuple[str, ...]
) -> tuple[str, ...]:
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(name, str) for name in raw)
    ):
        raise ValueError(
            f"{path}: digest {label} must be a non-empty list of level labels"
        )
    unknown = sorted(set(raw) - set(vocabulary))
    if unknown:
        raise ValueError(
            f"{path}: digest {label} has labels outside the closed "
            f"vocabulary {list(vocabulary)}: {unknown}"
        )
    return tuple(raw)


def _validate_digest_range(
    raw: Any, path: Path, label: str, low: int, high: int | None = None
) -> tuple[int, int]:
    if not isinstance(raw, dict) or set(raw) - {"min", "max"}:
        raise ValueError(
            f"{path}: digest {label} must be a mapping with only 'min'/'max'"
        )
    minimum = raw.get("min", low)
    maximum = raw.get("max", _DIGEST_CLIMAX_CEILING if high is None else high)
    for name, value in (("min", minimum), ("max", maximum)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{path}: digest {label}.{name} must be an integer")
    if minimum < low or maximum < minimum or (high is not None and maximum > high):
        raise ValueError(
            f"{path}: digest {label} must satisfy {low} <= min <= max"
            + (f" <= {high}" if high is not None else "")
        )
    return minimum, maximum


def _validate_digest(raw: dict[str, Any], path: Path) -> DigestConfig:
    """Validate the ``digest`` section fail-closed (delta requirement 1).

    The condition vocabulary is closed (``_DIGEST_CONDITION_KEYS``): any
    race/species/persona key fails the load. ``residue``/``humiliated``
    must declare a rulebook buff and ``none`` must not. The final row MUST
    be the empty-``when`` fallback, so first-match evaluation always yields
    exactly one outcome per selected participant.
    """
    section = raw.get("digest")
    if not isinstance(section, dict):
        raise ValueError(f"{path}: section 'digest' must be a mapping")
    rows_raw = section.get("rows")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise ValueError(f"{path}: digest rows must be a non-empty list of mappings")
    from world.rules.buffs import BUFF_DEFINITIONS

    rows: list[DigestRow] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(rows_raw):
        if not isinstance(raw_row, dict):
            raise ValueError(f"{path}: digest row {index} must be a mapping")
        unknown = set(raw_row) - _DIGEST_ROW_KEYS
        if unknown:
            raise ValueError(
                f"{path}: digest row {index} has unknown keys {sorted(unknown)}"
            )
        row_id = raw_row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            raise ValueError(f"{path}: digest row {index} needs a non-empty 'id'")
        if row_id in seen_ids:
            raise ValueError(f"{path}: digest row id {row_id!r} is duplicated")
        seen_ids.add(row_id)
        outcome = raw_row.get("outcome")
        if outcome not in _DIGEST_OUTCOMES:
            raise ValueError(
                f"{path}: digest row {row_id!r} outcome must be one of "
                f"{sorted(_DIGEST_OUTCOMES)}, got {outcome!r}"
            )
        buff = raw_row.get("buff")
        if outcome == "none":
            if buff is not None:
                raise ValueError(
                    f"{path}: digest row {row_id!r} (none) must not declare a buff"
                )
        elif not isinstance(buff, str) or not buff:
            raise ValueError(
                f"{path}: digest row {row_id!r} ({outcome}) must declare a buff key"
            )
        elif buff not in BUFF_DEFINITIONS:
            raise ValueError(
                f"{path}: digest row {row_id!r} buff {buff!r} is not a rulebook buff"
            )
        else:
            # The digest's mechanical footprint is a marker: world-second
            # duration and bounds-surface modifiers only (delta requirement
            # 2). A rate/decay buff or an unbounded duration would turn the
            # cosmetic digest table into a state-mutating periodic effect.
            definition = BUFF_DEFINITIONS[buff]
            if not isinstance(definition.duration, int) or isinstance(
                definition.duration, bool
            ) or definition.duration < 1:
                raise ValueError(
                    f"{path}: digest row {row_id!r} buff {buff!r} must carry a "
                    "positive world-second duration"
                )
            if set(definition.modifiers) != {"bounds"} or not definition.modifiers[
                "bounds"
            ]:
                raise ValueError(
                    f"{path}: digest row {row_id!r} buff {buff!r} must declare a "
                    "non-empty bounds-only modifier surface"
                )
        when_raw = raw_row.get("when", {})
        if not isinstance(when_raw, dict):
            raise ValueError(f"{path}: digest row {row_id!r} 'when' must be a mapping")
        unknown_conditions = set(when_raw) - _DIGEST_CONDITION_KEYS
        if unknown_conditions:
            raise ValueError(
                f"{path}: digest row {row_id!r} has condition keys outside the "
                f"closed vocabulary {sorted(_DIGEST_CONDITION_KEYS)}: "
                f"{sorted(unknown_conditions)}"
            )
        conditions: dict[str, Any] = {}
        for key, value in when_raw.items():
            if key == "sensitivity_level":
                conditions[key] = _validate_digest_labels(
                    value, path, f"{row_id}.{key}", SENSITIVITY_LEVELS
                )
            elif key == "shame_level":
                conditions[key] = _validate_digest_labels(
                    value, path, f"{row_id}.{key}", SHAME_LEVELS
                )
            elif key == "outcome.zero_landed":
                if not isinstance(value, bool):
                    raise ValueError(
                        f"{path}: digest {row_id}.{key} must be a boolean"
                    )
                conditions[key] = value
            elif key == "arousal_ordinal":
                conditions[key] = _validate_digest_range(
                    value, path, f"{row_id}.{key}", 0, len(AROUSAL_LEVELS) - 1
                )
            else:  # outcome.climax_count
                conditions[key] = _validate_digest_range(
                    value, path, f"{row_id}.{key}", 0
                )
        if index == len(rows_raw) - 1 and conditions:
            raise ValueError(
                f"{path}: the last digest row ({row_id!r}) must be the "
                "empty-when fallback so every participant digests exactly once"
            )
        rows.append(
            DigestRow(
                id=row_id,
                when=MappingProxyType(conditions),
                outcome=outcome,
                buff=buff,
            )
        )
    return DigestConfig(rows=tuple(rows))
