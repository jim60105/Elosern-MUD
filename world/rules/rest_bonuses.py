"""Durable paid-lodging, street-nap and well-rested travel entitlements.

These are per-body (and per-party-owner) attribute records that several
deterministic owners must read without importing each other:

- ``world.rules.sleep_receipt`` needs the paid-sleep and street-nap facts while
  deriving a wake target;
- ``world.rules.fatigue`` needs the well-rested walking allowance while it
  settles foot travel;
- ``world.rules.clock`` needs both while it reconciles a sleep receipt;
- ``world.rules.lodging`` and ``world.rules.city_sleep`` write them.

This module is the leaf: it validates, reads and writes the records and imports
no settlement owner. Writers are expected to run inside their caller's
transaction; the attribute surface names are exported so every enclosing
rollback owner snapshots the same set.
"""

from __future__ import annotations

from typing import Any, Mapping

#: One body's lodging access entitlement: ``{booking_id, place_key, room_id}``.
ACCESS_ATTRIBUTE = "lodging_guest_access"
#: One body's paid sleep binding:
#: ``{sleep_id, booking_id, place_key, room_id}``.
PAID_SLEEP_ATTRIBUTE = "lodging_paid_sleep"
#: One body's active voluntary street nap:
#: ``{sleep_id, street, patrol_tick, day}``.
STREET_NAP_ATTRIBUTE = "city_street_nap"
#: One party owner's same-day street nap refusal: ``{street: day}``.
STREET_REFUSAL_ATTRIBUTE = "city_street_refusals"
#: Remaining well-rested foot-travel allowance, in game seconds.
ALLOWANCE_ATTRIBUTE = "well_rested_walking_seconds"
#: The sleep identity that already granted the current allowance.
AWARD_ATTRIBUTE = "well_rested_awarded_sleep"

#: Every durable surface an enclosing rollback owner must snapshot.
SURFACES: tuple[tuple[str, str | None], ...] = (
    (ACCESS_ATTRIBUTE, None),
    (PAID_SLEEP_ATTRIBUTE, None),
    (STREET_NAP_ATTRIBUTE, None),
    (STREET_REFUSAL_ATTRIBUTE, None),
    (ALLOWANCE_ATTRIBUTE, None),
    (AWARD_ATTRIBUTE, None),
)

#: The authored two-hour allowance; writers never exceed it.
MAX_ALLOWANCE_SECONDS = 7200

_ACCESS_FIELDS = frozenset({"booking_id", "place_key", "room_id"})
_PAID_FIELDS = frozenset({"sleep_id", "booking_id", "place_key", "room_id"})
_NAP_FIELDS = frozenset({"sleep_id", "street", "patrol_tick", "day"})


class RestBonusError(ValueError):
    """One durable rest-bonus record is malformed; the write fails closed."""


def _attributes(entity: Any) -> Any | None:
    return getattr(entity, "attributes", None)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _required_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not _is_int(value) or value <= 0:
        raise RestBonusError(f"{key} must be a positive integer")
    return int(value)


def _required_non_negative(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not _is_int(value) or value < 0:
        raise RestBonusError(f"{key} must be a non-negative integer")
    return int(value)


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RestBonusError(f"{key} must be a non-empty string")
    return value


def _read_exact(entity: Any, key: str, fields: frozenset[str]) -> dict[str, Any] | None:
    attributes = _attributes(entity)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        return None
    if not attributes.has(key):
        return None
    raw = attributes.get(key)
    if not isinstance(raw, Mapping) or set(raw) != fields:
        raise RestBonusError(f"{key} carries an unexpected shape")
    return dict(raw)


def _write(entity: Any, key: str, value: Mapping[str, Any]) -> None:
    attributes = _attributes(entity)
    if attributes is None:
        raise RestBonusError(f"{type(entity).__name__} has no attribute store")
    attributes.add(key, dict(value))


def _write_scalar(entity: Any, key: str, value: Any) -> None:
    attributes = _attributes(entity)
    if attributes is None:
        raise RestBonusError(f"{type(entity).__name__} has no attribute store")
    attributes.add(key, value)


# -- lodging access ----------------------------------------------------------


def read_access(entity: Any) -> dict[str, Any] | None:
    """Return one body's active lodging access, or ``None``."""
    payload = _read_exact(entity, ACCESS_ATTRIBUTE, _ACCESS_FIELDS)
    if payload is None:
        return None
    return {
        "booking_id": _required_text(payload, "booking_id"),
        "place_key": _required_text(payload, "place_key"),
        "room_id": _required_int(payload, "room_id"),
    }


def write_access(
    entity: Any, *, booking_id: str, place_key: str, room_id: int
) -> dict[str, Any]:
    value = {
        "booking_id": str(booking_id),
        "place_key": str(place_key),
        "room_id": int(room_id),
    }
    _write(entity, ACCESS_ATTRIBUTE, value)
    return value


def clear_access(entity: Any) -> None:
    attributes = _attributes(entity)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(ACCESS_ATTRIBUTE)


# -- paid sleep --------------------------------------------------------------


def read_paid_sleep(entity: Any) -> dict[str, Any] | None:
    """Return one body's paid-sleep binding, or ``None``."""
    payload = _read_exact(entity, PAID_SLEEP_ATTRIBUTE, _PAID_FIELDS)
    if payload is None:
        return None
    return {
        "sleep_id": _required_text(payload, "sleep_id"),
        "booking_id": _required_text(payload, "booking_id"),
        "place_key": _required_text(payload, "place_key"),
        "room_id": _required_int(payload, "room_id"),
    }


def write_paid_sleep(
    entity: Any,
    *,
    sleep_id: str,
    booking_id: str,
    place_key: str,
    room_id: int,
) -> dict[str, Any]:
    value = {
        "sleep_id": str(sleep_id),
        "booking_id": str(booking_id),
        "place_key": str(place_key),
        "room_id": int(room_id),
    }
    _write(entity, PAID_SLEEP_ATTRIBUTE, value)
    return value


def clear_paid_sleep(entity: Any, *, sleep_id: str | None = None) -> None:
    """Drop one paid binding, optionally only when it belongs to ``sleep_id``."""
    current = read_paid_sleep(entity)
    if current is None:
        return
    if sleep_id is not None and current["sleep_id"] != sleep_id:
        return
    attributes = _attributes(entity)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(PAID_SLEEP_ATTRIBUTE)


def paid_sleep_active(entity: Any, receipt: Any) -> bool:
    """Whether ``receipt`` is the body's accepted paid sleep right now.

    Reads only durable state: the posture must still be voluntary and both the
    receipt identity and the booking/room binding must match. The clock never
    needs to query the booking row to answer this, so settlement stays a pure
    per-body read.
    """
    if receipt is None or not getattr(receipt, "sleeping", False):
        return False
    from world.rules.fatigue import SleepPosture, read_optional_fatigue_state

    state = read_optional_fatigue_state(entity)
    if state is None or state.posture is not SleepPosture.VOLUNTARY:
        return False
    paid = read_paid_sleep(entity)
    if paid is None or paid["sleep_id"] != receipt.sleep_id:
        return False
    agreed = read_access(entity)
    return (
        agreed is not None
        and agreed["booking_id"] == paid["booking_id"]
        and agreed["place_key"] == paid["place_key"]
        and agreed["room_id"] == paid["room_id"]
    )


# -- street naps -------------------------------------------------------------


def read_street_nap(entity: Any) -> dict[str, Any] | None:
    """Return one body's active street-nap binding, or ``None``."""
    payload = _read_exact(entity, STREET_NAP_ATTRIBUTE, _NAP_FIELDS)
    if payload is None:
        return None
    return {
        "sleep_id": _required_text(payload, "sleep_id"),
        "street": _required_text(payload, "street"),
        "patrol_tick": _required_int(payload, "patrol_tick"),
        "day": _required_non_negative(payload, "day"),
    }


def write_street_nap(
    entity: Any,
    *,
    sleep_id: str,
    street: str,
    patrol_tick: int,
    day: int,
) -> dict[str, Any]:
    value = {
        "sleep_id": str(sleep_id),
        "street": str(street),
        "patrol_tick": int(patrol_tick),
        "day": int(day),
    }
    _write(entity, STREET_NAP_ATTRIBUTE, value)
    return value


def clear_street_nap(entity: Any, *, sleep_id: str | None = None) -> None:
    current = read_street_nap(entity)
    if current is None:
        return
    if sleep_id is not None and current["sleep_id"] != sleep_id:
        return
    attributes = _attributes(entity)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(STREET_NAP_ATTRIBUTE)


def read_street_refusals(entity: Any) -> dict[str, int]:
    """Return one party owner's same-day street refusal map."""
    attributes = _attributes(entity)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        return {}
    if not attributes.has(STREET_REFUSAL_ATTRIBUTE):
        return {}
    raw = attributes.get(STREET_REFUSAL_ATTRIBUTE)
    if not isinstance(raw, Mapping):
        raise RestBonusError("street refusal record is not a mapping")
    clean: dict[str, int] = {}
    for street, day in raw.items():
        if not isinstance(street, str) or not street or not _is_int(day) or day < 0:
            raise RestBonusError("street refusal record is malformed")
        clean[street] = int(day)
    return clean


def street_refused(entity: Any, street: str, day: int) -> bool:
    """Whether ``entity`` already had a street nap ended on ``street`` today."""
    try:
        return read_street_refusals(entity).get(str(street)) == int(day)
    except RestBonusError:
        # A malformed refusal record cannot prove the party is allowed back;
        # fail closed for the current day rather than granting a free retry.
        return True


def record_street_refusal(entity: Any, street: str, day: int) -> dict[str, int]:
    """Record one interrupted street nap for the party owner and day."""
    current = read_street_refusals(entity)
    # Keep only the current day: a refusal never survives into the next day and
    # the previous day's rows carry no meaning.
    clean = {key: value for key, value in current.items() if value == int(day)}
    clean[str(street)] = int(day)
    _write(entity, STREET_REFUSAL_ATTRIBUTE, clean)
    return clean


def clear_street_refusals(entity: Any) -> None:
    attributes = _attributes(entity)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(STREET_REFUSAL_ATTRIBUTE)


# -- well-rested walking allowance ------------------------------------------


def read_walking_allowance(entity: Any) -> int:
    """Return the remaining well-rested foot-travel seconds (0 when absent)."""
    attributes = _attributes(entity)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        return 0
    if not attributes.has(ALLOWANCE_ATTRIBUTE):
        return 0
    value = attributes.get(ALLOWANCE_ATTRIBUTE)
    if not _is_int(value) or not 0 <= value <= MAX_ALLOWANCE_SECONDS:
        raise RestBonusError("walking allowance is malformed")
    return int(value)


def write_walking_allowance(entity: Any, seconds: int) -> int:
    if not _is_int(seconds) or not 0 <= seconds <= MAX_ALLOWANCE_SECONDS:
        raise RestBonusError("walking allowance must be within its bound")
    _write_scalar(entity, ALLOWANCE_ATTRIBUTE, int(seconds))
    return int(seconds)


def award_walking_allowance(entity: Any, sleep_id: str) -> bool:
    """Grant the two-hour allowance once per sleep identity.

    A later qualifying sleep replaces the remaining allowance (never stacks);
    replaying the same completion is a no-op, so a replay after subsequent
    walking cannot refill what the walk spent.
    """
    attributes = _attributes(entity)
    if attributes is None:
        return False
    if attributes.has(AWARD_ATTRIBUTE):
        if attributes.get(AWARD_ATTRIBUTE) == str(sleep_id):
            return False
    write_walking_allowance(entity, MAX_ALLOWANCE_SECONDS)
    attributes.add(AWARD_ATTRIBUTE, str(sleep_id))
    return True


def consume_walking_allowance(entity: Any, seconds: int) -> int:
    """Spend committed foot-travel seconds from the allowance, clamped at zero."""
    if not _is_int(seconds) or seconds <= 0:
        return read_walking_allowance(entity)
    remaining = read_walking_allowance(entity)
    if remaining <= 0:
        return 0
    return write_walking_allowance(entity, max(0, remaining - int(seconds)))


def well_rested_active(entity: Any) -> bool:
    """Whether the body still carries any walking allowance."""
    return read_walking_allowance(entity) > 0


def clear_award(entity: Any) -> None:
    attributes = _attributes(entity)
    if attributes is not None and callable(getattr(attributes, "remove", None)):
        attributes.remove(AWARD_ATTRIBUTE)


__all__ = [
    "ACCESS_ATTRIBUTE",
    "ALLOWANCE_ATTRIBUTE",
    "AWARD_ATTRIBUTE",
    "MAX_ALLOWANCE_SECONDS",
    "PAID_SLEEP_ATTRIBUTE",
    "RestBonusError",
    "STREET_NAP_ATTRIBUTE",
    "STREET_REFUSAL_ATTRIBUTE",
    "SURFACES",
    "award_walking_allowance",
    "clear_access",
    "clear_award",
    "clear_paid_sleep",
    "clear_street_nap",
    "clear_street_refusals",
    "consume_walking_allowance",
    "paid_sleep_active",
    "read_access",
    "read_paid_sleep",
    "read_street_nap",
    "read_street_refusals",
    "read_walking_allowance",
    "record_street_refusal",
    "street_refused",
    "well_rested_active",
    "write_access",
    "write_paid_sleep",
    "write_street_nap",
    "write_walking_allowance",
]
