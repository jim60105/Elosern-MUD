"""Sole writer and reader of the player character's landmark rite record.

The record is the `PlayerCharacter` attribute ``landmark_rites`` (design §7.1,
schema 1): one entry per district the character has completed a rite in, and one
entry per ritual option completed there, carrying counts and ticks.

The envelope is strict. A value outside schema 1 raises
:class:`LandmarkRiteRecordError`; reading never repairs and never writes, and a
corrupt record is never overwritten -- the rite refuses and repair belongs to
the GM console. Every district and option entry already stored is preserved on
write, including keys the current content no longer declares, so editing the
rite document never corrupts a record.

This module deliberately knows nothing about the rite content: it does not
import ``world.lore.rites`` and cannot tell a declared key from a retired one.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = [
    "RECORD_ATTR",
    "SCHEMA_VERSION",
    "LandmarkRiteRecordError",
    "completed_district_keys",
    "empty_record",
    "read_record",
    "seen_option_keys",
    "validate_record",
    "with_completion",
    "write_record",
]

#: The persisted attribute holding the completion record.
RECORD_ATTR = "landmark_rites"

#: The one schema this module reads and writes.
SCHEMA_VERSION = 1

_TOP_LEVEL_FIELDS = ("schema_version", "completed")
_DISTRICT_FIELDS = ("first_tick", "last_tick", "count", "options")
_OPTION_FIELDS = ("count", "last_tick")


class LandmarkRiteRecordError(ValueError):
    """A stored rite record violates the schema-1 envelope."""


def _is_int(value: Any) -> bool:
    """Whether ``value`` is an integer that is not a ``bool``."""
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(value: Any, label: str, minimum: int) -> int:
    if not _is_int(value) or value < minimum:
        raise LandmarkRiteRecordError(
            f"{label} must be an integer >= {minimum}, got {value!r}"
        )
    return value


def _require_key(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise LandmarkRiteRecordError(f"{label} must be a non-empty string")
    return value


def _require_fields(value: Any, fields: tuple[str, ...], label: str) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise LandmarkRiteRecordError(f"{label} must be a mapping")
    if set(value.keys()) != set(fields):
        raise LandmarkRiteRecordError(
            f"{label} must hold exactly {', '.join(fields)}"
        )
    return value


def _validate_option_entry(value: Any, district_key: str, option_key: str) -> dict[str, int]:
    label = f"option entry {option_key!r} of district {district_key!r}"
    entry = _require_fields(value, _OPTION_FIELDS, label)
    return {
        "count": _require_int(entry["count"], f"{label} count", 1),
        "last_tick": _require_int(entry["last_tick"], f"{label} last_tick", 0),
    }


def _validate_district_entry(value: Any, district_key: str) -> dict[str, Any]:
    label = f"district entry {district_key!r}"
    entry = _require_fields(value, _DISTRICT_FIELDS, label)
    first_tick = _require_int(entry["first_tick"], f"{label} first_tick", 0)
    last_tick = _require_int(entry["last_tick"], f"{label} last_tick", 0)
    if first_tick > last_tick:
        raise LandmarkRiteRecordError(
            f"{label} first_tick must not exceed last_tick"
        )
    options = entry["options"]
    if not isinstance(options, Mapping):
        raise LandmarkRiteRecordError(f"{label} options must be a mapping")
    return {
        "first_tick": first_tick,
        "last_tick": last_tick,
        "count": _require_int(entry["count"], f"{label} count", 1),
        "options": {
            _require_key(option_key, f"{label} option key"): _validate_option_entry(
                option_entry, district_key, option_key
            )
            for option_key, option_entry in options.items()
        },
    }


def empty_record() -> dict[str, Any]:
    """Return a fresh record with no completed district."""
    return {"schema_version": SCHEMA_VERSION, "completed": {}}


def validate_record(value: Any) -> dict[str, Any]:
    """Return a plain-dict deep copy of ``value``, or raise on any violation."""
    record = _require_fields(value, _TOP_LEVEL_FIELDS, "rite record")
    version = record["schema_version"]
    if not _is_int(version) or version != SCHEMA_VERSION:
        raise LandmarkRiteRecordError(
            f"rite record schema_version must be the integer {SCHEMA_VERSION}"
        )
    completed = record["completed"]
    if not isinstance(completed, Mapping):
        raise LandmarkRiteRecordError("rite record completed must be a mapping")
    return {
        "schema_version": SCHEMA_VERSION,
        "completed": {
            _require_key(district_key, "rite record district key"): (
                _validate_district_entry(entry, district_key)
            )
            for district_key, entry in completed.items()
        },
    }


def read_record(owner: Any) -> dict[str, Any]:
    """The owner's validated record; a missing attribute reads as the empty one.

    Reading never writes: a character who never completed a rite has no
    attribute before and after the read. A stored value outside the envelope
    raises and is left untouched.
    """
    from evennia.utils.dbserialize import deserialize

    raw = owner.attributes.get(RECORD_ATTR)
    if raw is None:
        return empty_record()
    return validate_record(deserialize(raw))


def completed_district_keys(owner: Any) -> frozenset[str]:
    """The districts the owner has completed at least one rite in."""
    return frozenset(read_record(owner)["completed"])


def seen_option_keys(owner: Any, district_key: str) -> tuple[str, ...]:
    """The options completed in one district, in stored order."""
    entry = read_record(owner)["completed"].get(district_key)
    if entry is None:
        return ()
    return tuple(entry["options"])


def with_completion(
    record: Any, district_key: str, option_key: str, tick: int
) -> dict[str, Any]:
    """Return a new record holding one more completion; ``record`` is untouched.

    A new district entry starts both ticks at ``tick``; an existing one keeps
    its ``first_tick``, increments ``count`` and refreshes ``last_tick``, and
    increments or creates the option entry. Every other district and option
    entry is copied unchanged.
    """
    district_key = _require_key(district_key, "completion district key")
    option_key = _require_key(option_key, "completion option key")
    completion_tick = _require_int(tick, "completion tick", 0)
    updated = validate_record(record)
    completed = updated["completed"]
    entry = completed.get(district_key)
    if entry is None:
        completed[district_key] = {
            "first_tick": completion_tick,
            "last_tick": completion_tick,
            "count": 1,
            "options": {option_key: {"count": 1, "last_tick": completion_tick}},
        }
        return updated
    entry["last_tick"] = completion_tick
    entry["count"] += 1
    option_entry = entry["options"].get(option_key)
    if option_entry is None:
        entry["options"][option_key] = {
            "count": 1,
            "last_tick": completion_tick,
        }
        return updated
    option_entry["last_tick"] = completion_tick
    option_entry["count"] += 1
    return updated


def write_record(owner: Any, record: Any) -> None:
    """Store one validated record; an invalid one raises and stores nothing."""
    owner.attributes.add(RECORD_ATTR, validate_record(record))