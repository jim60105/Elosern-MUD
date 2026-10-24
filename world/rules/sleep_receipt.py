"""Durable per-body accepted sleep receipts (fix-body-sleep-lifecycle).

One body owns at most one accepted sleep episode. The receipt is the identity
the deterministic time-skip owner reuses across reload, reconnect and control
handoff: it names the declared mode and target, the committed progress and the
bounded identity/result of the latest settled interval. It is a plain
validated attribute value, never an object reference or process-only state, so
a reload reads exactly what the commit wrote.

Ownership stays with ``world/rules/time_skip.py`` (entry and continuation) and
``world/rules/clock.py`` (passive settlement). This module only serializes,
validates and derives pure boundary facts; it writes no clock, posture or
projection. It imports the fatigue policy (the sole physiology authority)
without importing the settlement owner, so the fatigue writer may create a
forced receipt from its own committed transition.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from world.rules.fatigue import FatigueActivity, get_policy
from world.rules.traits import GAUGE_KEYS

#: The body's own durable accepted-sleep record.
RECEIPT_ATTRIBUTE = "sleep_receipt"
#: Bounded identity of the latest accepted explicit all-party entry.
PARTY_OPERATION_ATTRIBUTE = "sleep_party_operation"

#: Durable attributes the sleep receipt owner can write.
SLEEP_RECEIPT_SURFACES: tuple[tuple[str, str | None], ...] = (
    (RECEIPT_ATTRIBUTE, None),
    (PARTY_OPERATION_ATTRIBUTE, None),
)

KIND_VOLUNTARY = "voluntary"
KIND_FORCED = "forced"
KINDS = (KIND_VOLUNTARY, KIND_FORCED)

MODE_DURATION = "duration"
MODE_RECOVERY = "recovery"
MODE_FORCED_THRESHOLD = "forced_threshold"
MODES = (MODE_DURATION, MODE_RECOVERY, MODE_FORCED_THRESHOLD)

STATE_SLEEPING = "sleeping"
STATE_INTERRUPTED = "interrupted"
STATE_COMPLETED = "completed"
STATES = (STATE_SLEEPING, STATE_INTERRUPTED, STATE_COMPLETED)

MISSING_RECEIPT_CODE = "missing_sleep_receipt"
CORRUPT_RECEIPT_CODE = "corrupt_sleep_receipt"
MISSING_RECEIPT_MESSAGE = "找不到這次睡眠的紀錄，無法繼續；請重新入睡。"
CORRUPT_RECEIPT_MESSAGE = "睡眠紀錄已損毀，無法繼續；請重新入睡。"

_REQUIRED_INT_FIELDS = (
    "body_id",
    "entry_tick",
    "target_tick",
    "limit_tick",
    "settled_through_tick",
    "revision",
    "accepted_seconds",
)
_RESULT_FIELDS = (
    "operation_id",
    "sleep_id",
    "revision",
    "requested_seconds",
    "elapsed_seconds",
    "tick_from",
    "tick_to",
    "woke",
    "completed",
    "partial",
    "summary",
)
_MAX_SUMMARY = 500
_MAX_ID = 128


class SleepReceiptError(RuntimeError):
    """One receipt is absent or unusable; the operation fails closed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SleepReceipt:
    """One immutable accepted sleep episode with its settled cursor."""

    sleep_id: str
    body_id: int
    owner_id: int | None
    kind: str
    mode: str
    entry_tick: int
    target_tick: int
    limit_tick: int
    settled_through_tick: int
    revision: int
    state: str
    accepted_seconds: int
    partial: bool
    entry_operation_id: str | None = None
    last_operation_id: str | None = None
    last_result: dict[str, Any] | None = None

    @property
    def sleeping(self) -> bool:
        return self.state == STATE_SLEEPING

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sleep_id": self.sleep_id,
            "body_id": int(self.body_id),
            "owner_id": None if self.owner_id is None else int(self.owner_id),
            "kind": self.kind,
            "mode": self.mode,
            "entry_tick": int(self.entry_tick),
            "target_tick": int(self.target_tick),
            "limit_tick": int(self.limit_tick),
            "settled_through_tick": int(self.settled_through_tick),
            "revision": int(self.revision),
            "state": self.state,
            "accepted_seconds": int(self.accepted_seconds),
            "partial": bool(self.partial),
            "entry_operation_id": self.entry_operation_id,
            "last_operation_id": self.last_operation_id,
            "last_result": (
                None if self.last_result is None else dict(self.last_result)
            ),
        }
        return payload

    def with_progress(
        self,
        *,
        settled_through_tick: int,
        target_tick: int | None = None,
        state: str | None = None,
        partial: bool | None = None,
    ) -> "SleepReceipt":
        """Return the receipt advanced to a later settled cursor."""
        return replace(
            self,
            settled_through_tick=max(int(settled_through_tick), self.settled_through_tick),
            target_tick=self.target_tick if target_tick is None else int(target_tick),
            revision=self.revision + 1,
            state=self.state if state is None else state,
            partial=self.partial if partial is None else bool(partial),
        )

    def with_result(self, result: dict[str, Any]) -> "SleepReceipt":
        """Return the receipt carrying one bounded committed interval result."""
        return replace(
            self,
            last_operation_id=str(result["operation_id"]),
            last_result=_validate_result(result),
        )


def _clamp_text(value: Any, limit: int = _MAX_ID) -> str:
    text = str(value)
    return text[:limit]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise ValueError("sleep result must be a mapping")
    if set(result) != set(_RESULT_FIELDS):
        raise ValueError("sleep result carries unexpected fields")
    clean: dict[str, Any] = {
        "operation_id": _clamp_text(result["operation_id"]),
        "sleep_id": _clamp_text(result["sleep_id"]),
        "revision": result["revision"],
        "requested_seconds": result["requested_seconds"],
        "elapsed_seconds": result["elapsed_seconds"],
        "tick_from": result["tick_from"],
        "tick_to": result["tick_to"],
        "woke": bool(result["woke"]),
        "completed": bool(result["completed"]),
        "partial": bool(result["partial"]),
        "summary": _clamp_text(result["summary"], _MAX_SUMMARY),
    }
    for key in (
        "revision",
        "requested_seconds",
        "elapsed_seconds",
        "tick_from",
        "tick_to",
    ):
        if not _is_int(clean[key]) or clean[key] < 0:
            raise ValueError(f"sleep result {key} is not a non-negative integer")
    return clean


def validate_receipt(payload: Any) -> SleepReceipt:
    """Validate one stored receipt mapping, raising on any malformed shape."""
    if not isinstance(payload, Mapping):
        raise SleepReceiptError(
            CORRUPT_RECEIPT_CODE, CORRUPT_RECEIPT_MESSAGE
        )
    try:
        if payload.get("kind") not in KINDS:
            raise ValueError("unknown sleep kind")
        if payload.get("mode") not in MODES:
            raise ValueError("unknown sleep mode")
        if payload.get("state") not in STATES:
            raise ValueError("unknown sleep state")
        owner_id = payload.get("owner_id")
        if owner_id is not None and (not _is_int(owner_id) or owner_id <= 0):
            raise ValueError("invalid owner identity")
        for field in _REQUIRED_INT_FIELDS:
            value = payload.get(field)
            if not _is_int(value) or value < 0:
                raise ValueError(f"invalid {field}")
        if payload["body_id"] <= 0:
            raise ValueError("invalid body identity")
        if payload["limit_tick"] < payload["entry_tick"]:
            raise ValueError("sleep limit precedes entry")
        if payload["target_tick"] < payload["entry_tick"]:
            raise ValueError("sleep target precedes entry")
        sleep_id = payload.get("sleep_id")
        if not isinstance(sleep_id, str) or not sleep_id or len(sleep_id) > _MAX_ID:
            raise ValueError("invalid sleep identity")
        entry_operation_id = payload.get("entry_operation_id")
        if entry_operation_id is not None and not isinstance(
            entry_operation_id, str
        ):
            raise ValueError("invalid entry operation identity")
        last_operation_id = payload.get("last_operation_id")
        if last_operation_id is not None and not isinstance(
            last_operation_id, str
        ):
            raise ValueError("invalid interval operation identity")
        last_result = payload.get("last_result")
        if last_result is not None:
            last_result = _validate_result(last_result)
        return SleepReceipt(
            sleep_id=_clamp_text(sleep_id),
            body_id=int(payload["body_id"]),
            owner_id=None if owner_id is None else int(owner_id),
            kind=str(payload["kind"]),
            mode=str(payload["mode"]),
            entry_tick=int(payload["entry_tick"]),
            target_tick=int(payload["target_tick"]),
            limit_tick=int(payload["limit_tick"]),
            settled_through_tick=int(payload["settled_through_tick"]),
            revision=int(payload["revision"]),
            state=str(payload["state"]),
            accepted_seconds=int(payload["accepted_seconds"]),
            partial=bool(payload.get("partial")),
            entry_operation_id=entry_operation_id,
            last_operation_id=last_operation_id,
            last_result=last_result,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SleepReceiptError(
            CORRUPT_RECEIPT_CODE, CORRUPT_RECEIPT_MESSAGE
        ) from error


def _attributes(entity: Any) -> Any:
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        raise SleepReceiptError(MISSING_RECEIPT_CODE, MISSING_RECEIPT_MESSAGE)
    return attributes


def read_sleep_receipt(entity: Any) -> SleepReceipt | None:
    """Return the body's validated receipt, or ``None`` when none was written.

    A malformed stored value raises :class:`SleepReceiptError`; callers never
    repair, refill or fabricate a replacement.
    """
    attributes = _attributes(entity)
    if not callable(getattr(attributes, "has", None)):
        return None
    if not attributes.has(RECEIPT_ATTRIBUTE):
        return None
    return validate_receipt(attributes.get(RECEIPT_ATTRIBUTE))


def write_sleep_receipt(entity: Any, receipt: SleepReceipt) -> SleepReceipt:
    """Persist one validated receipt through the attribute surface."""
    _attributes(entity).add(RECEIPT_ATTRIBUTE, receipt.as_dict())
    return receipt


def clear_sleep_receipt(entity: Any) -> None:
    """Remove one body's receipt (used only by explicit construction reset)."""
    _attributes(entity).remove(RECEIPT_ATTRIBUTE)


def read_party_operation(entity: Any) -> dict[str, Any] | None:
    """Return the bounded latest explicit party-entry identity, or ``None``."""
    attributes = _attributes(entity)
    if not attributes.has(PARTY_OPERATION_ATTRIBUTE):
        return None
    payload = attributes.get(PARTY_OPERATION_ATTRIBUTE)
    if not isinstance(payload, Mapping):
        raise SleepReceiptError(CORRUPT_RECEIPT_CODE, CORRUPT_RECEIPT_MESSAGE)
    operation_id = payload.get("operation_id")
    body_ids = payload.get("body_ids")
    if (
        not isinstance(operation_id, str)
        or isinstance(body_ids, (str, bytes))
        or not isinstance(body_ids, Sequence)
        or any(not _is_int(item) for item in body_ids)
    ):
        raise SleepReceiptError(CORRUPT_RECEIPT_CODE, CORRUPT_RECEIPT_MESSAGE)
    return {
        "operation_id": operation_id[: _MAX_ID],
        "body_ids": [int(item) for item in body_ids][:64],
    }


def write_party_operation(
    entity: Any, operation_id: str, body_ids: list[int]
) -> dict[str, Any]:
    """Persist the latest accepted explicit party-entry identity."""
    payload = {
        "operation_id": _clamp_text(operation_id),
        "body_ids": [int(item) for item in body_ids][:64],
    }
    _attributes(entity).add(PARTY_OPERATION_ATTRIBUTE, payload)
    return payload


def full_recovery_seconds(entity: Any) -> int:
    """Return the uncapped seconds to full HP/MP/SP and mental reserve.

    The caller owns the configured cap; the uncapped value is what lets a
    capped recovery report a truthful partial target instead of claiming full
    restoration. A body without constructed physiology contributes no mental
    requirement, matching the existing calculation.
    """
    seconds = 0
    traits = getattr(entity, "traits", None)
    if traits is not None:
        for key in GAUGE_KEYS:
            gauge = getattr(traits, key, None)
            if gauge is None:
                continue
            rate = float(getattr(gauge, "rate", 0))
            value = float(getattr(gauge, "value", getattr(gauge, "current", 0)))
            maximum = float(getattr(gauge, "max", value))
            if rate > 0 and value < maximum:
                seconds = max(seconds, math.ceil((maximum - value) / rate))
    state = _mental_state(entity)
    if state is not None:
        policy = get_policy()
        gap = max(0, policy.max_units - state.reserve_units)
        sleep_rate = policy.rates[FatigueActivity.SLEEP]
        if sleep_rate > 0:
            seconds = max(seconds, math.ceil(gap / sleep_rate))
    return seconds


def _mental_state(entity: Any) -> Any:
    from world.rules.fatigue import read_optional_fatigue_state

    return read_optional_fatigue_state(entity)


def forced_wake_seconds(entity: Any) -> int:
    """Return the bounded seconds until a forced sleeper's natural wake."""
    state = _mental_state(entity)
    if state is None:
        return 0
    policy = get_policy()
    gap = max(0, policy.wake_units - state.reserve_units)
    rate = policy.rates[FatigueActivity.SLEEP]
    if rate <= 0:
        return 0
    return math.ceil(gap / rate)


def recovery_target_tick(entity: Any, receipt: SleepReceipt, tick: int) -> int:
    """Return the next recovery boundary under the receipt's unchanged cap.

    A recovery target is reevaluated against the body's current unmet needs, so
    an accepted external effect that changed recovery requirements moves the
    next boundary without extending ``limit_tick`` or replacing the sleep
    identity. The cap always wins.
    """
    if receipt.mode == MODE_DURATION:
        return receipt.target_tick
    if receipt.mode == MODE_FORCED_THRESHOLD:
        return min(receipt.limit_tick, tick + forced_wake_seconds(entity))
    return min(receipt.limit_tick, tick + full_recovery_seconds(entity))


def next_sleep_offset(
    entity: Any, receipt: SleepReceipt, tick: int
) -> int | None:
    """Return whole seconds until this sleeper's own next wake target.

    ``None`` means the body has no accepted plan (a completed/interrupted
    receipt never declares one).
    """
    if not receipt.sleeping:
        return None
    target = recovery_target_tick(entity, receipt, tick)
    return max(0, int(target) - int(tick))


def is_recovery_satisfied(entity: Any, receipt: SleepReceipt) -> bool:
    """Whether a recovery-mode sleeper has actually reached its declared target."""
    if receipt.mode != MODE_RECOVERY:
        return False
    return full_recovery_seconds(entity) == 0


__all__ = [
    "CORRUPT_RECEIPT_CODE",
    "CORRUPT_RECEIPT_MESSAGE",
    "KIND_FORCED",
    "KIND_VOLUNTARY",
    "KINDS",
    "MISSING_RECEIPT_CODE",
    "MISSING_RECEIPT_MESSAGE",
    "MODES",
    "MODE_DURATION",
    "MODE_FORCED_THRESHOLD",
    "MODE_RECOVERY",
    "PARTY_OPERATION_ATTRIBUTE",
    "RECEIPT_ATTRIBUTE",
    "SLEEP_RECEIPT_SURFACES",
    "STATES",
    "STATE_COMPLETED",
    "STATE_INTERRUPTED",
    "STATE_SLEEPING",
    "SleepReceipt",
    "SleepReceiptError",
    "clear_sleep_receipt",
    "forced_wake_seconds",
    "full_recovery_seconds",
    "is_recovery_satisfied",
    "next_sleep_offset",
    "read_party_operation",
    "read_sleep_receipt",
    "recovery_target_tick",
    "validate_receipt",
    "write_party_operation",
    "write_sleep_receipt",
]
