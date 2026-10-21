"""Exact mental-reserve physiology and pure fatigue policy (mental-reserve).

Mental reserve (精神儲備) is a per-body, long-term physiology, independent of
HP/MP/SP and of account state: restoring SP never refills it, and an ordinary
long rest is the only authored way to recover it. One player character or
effective party companion owns its own reserve and sleep posture.

Storage contract
----------------
Reserve is exact integer units persisted as the ``mental_reserve_units``
attribute on the owning entity; one unit is 1/3600 percentage point, so
``3600`` units are one percentage point, ``0`` is empty and ``360000`` is
full. Posture is persisted as the ``sleep_posture`` attribute with the closed
values ``awake``, ``voluntary`` and ``forced``. Reads never create or repair
physiology: a missing, mistyped, out-of-range or unknown-posture value raises
:class:`FatigueStateError` and callers fail before they write effects or time.
Ordinary entity construction establishes the full/awake baseline once through
:func:`initialize_fatigue_state`; that function only fills a wholly absent
construction state and never refills a valid or malformed existing value.

Activity rates (exact net units per game second, already including the cost of
staying awake): ordinary awake activity, waiting and study ``-4``; foot travel
``-8``; awake combat ``-12``; actual sleep ``+12``. Effects clamp to
``[0, 360000]``. Terrain adds no exertion multiplier; it already lengthens
travel time.

Fatigue stages and travel
-------------------------
Awake reserve selects exclusive stages: normal ``252000..360000``, light
``144000..251999``, moderate ``72000..143999`` and severe ``1..71999``. The
latched forced-sleep posture replaces the ordinary stage; voluntary sleep
reports its own sleeping stage. :func:`fatigue_stage` answers the
instantaneous state, so reserve ``252000`` is normal, and
:func:`foot_speed_scale` answers that stage's scale (``1`` at ``252000``).
Movement integrates a segment through :func:`outgoing_foot_speed_scale`, the
scale governing the interval *beginning* at the state: at exactly ``252000``
the next unit consumed is already light, so that query returns ``9/10`` and a
full-reserve 6 h walk at 4.5 km/h covers 25,987.5 m, not 27,000 m. Travel and
actions are forbidden while any sleep posture is latched; targeting stays
permitted.

Prediction API for rules consumers
----------------------------------
:func:`next_fatigue_boundary` returns the next threshold, depletion or wake
event as an exact :class:`fractions.Fraction` offset in game seconds measured
from the supplied state; consumption reports the next lower stage floor
(strictly below the current reserve) or depletion at zero, and a forced
sleeper outside live combat reports the 20 percent wake offset (6000 s from
zero). :func:`predict_interval` returns the immutable start/end state for the
requested whole seconds, the next boundary and the transition reason. Its
``end`` always describes the full requested interval. ``applicable_seconds``
is what an interruptible caller may commit now: the first whole second at or
after the boundary (interactive advances round up), or the whole interval for
indivisible actions and terminal combat settlement, which never reinterpret
mid-interval exhaustion as retroactive sleep. Callers re-ask
:func:`predict_interval` for that accepted duration and commit the identical
duration and state. Neither prediction function writes anything.

Settlement
----------
:func:`settle_fatigue_intervals` is the sole fatigue writer for accepted
effects. It validates every affected member (state, activity/posture
compatibility, duplicate members and stale start states) and computes every
prediction before the first write, applies the writes in one
``transaction.atomic()`` block, restores every snapshotted attribute on
failure, and emits one ``fatigue_transition`` info event per committed
member whose state changed only after the durable commit. Technical failures
propagate; no success event is fabricated. ``FATIGUE_ATTRIBUTE_SURFACES``
declares the two durable surfaces to enclosing rollback owners.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import ceil
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from django.db import transaction

from world.observability import log_info
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    PHYSIOLOGICAL_PROTECTION,
    apply_buff,
    entity_active_buffs,
)
from world.rules.rulebook.schema import SectionedRule, load_sectioned_rules
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
)

RESERVE_ATTRIBUTE = "mental_reserve_units"
POSTURE_ATTRIBUTE = "sleep_posture"
#: The BuffHandler's own persisted cache attribute; a projection write and
#: every restore must cover it together with the two physiology attributes.
BUFF_CACHE_ATTRIBUTE = "buffs"

#: Durable attributes the fatigue writer can touch, for enclosing rollback owners.
FATIGUE_ATTRIBUTE_SURFACES: tuple[tuple[str, str | None], ...] = (
    (RESERVE_ATTRIBUTE, None),
    (POSTURE_ATTRIBUTE, None),
    (BUFF_CACHE_ATTRIBUTE, None),
)

RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "fatigue.yaml"

_MISSING = object()


class FatigueRulebookError(ValueError):
    """The fatigue rulebook violates the canonical policy contract."""


class FatigueRejectReason(StrEnum):
    """Stable rejection codes for malformed or ineligible fatigue operations."""

    MISSING = "missing_state"
    INVALID_TYPE = "invalid_type"
    OUT_OF_RANGE = "out_of_range"
    UNKNOWN_POSTURE = "unknown_posture"
    ACTIVITY_POSTURE_MISMATCH = "activity_posture_mismatch"
    STALE_START = "stale_start"
    INVALID_START_STATE = "invalid_start_state"
    DUPLICATE_MEMBER = "duplicate_member"
    INVALID_SECONDS = "invalid_seconds"
    INTERRUPTIBLE_OVERRUN = "interruptible_overrun"
    TRAVEL_FORBIDDEN = "travel_forbidden"


class FatigueStateError(ValueError):
    """One fatigue state or interval is not usable by a deterministic writer."""

    def __init__(self, reason: FatigueRejectReason, message: str) -> None:
        super().__init__(f"{reason.value}: {message}")
        self.reason = reason


class SleepPosture(StrEnum):
    """Persisted per-body posture; distinct from defeat, knockout and death."""

    AWAKE = "awake"
    VOLUNTARY = "voluntary"
    FORCED = "forced"


class FatigueActivity(StrEnum):
    """Declared activity over one settled interval."""

    AWAKE = "awake"
    FOOT_TRAVEL = "foot_travel"
    AWAKE_COMBAT = "awake_combat"
    SLEEP = "sleep"


class FatigueStage(StrEnum):
    """Exclusive fatigue projection of one body."""

    NORMAL = "normal"
    LIGHT = "light"
    MODERATE = "moderate"
    SEVERE = "severe"
    SLEEPING = "sleeping"
    FORCED_SLEEP = "forced_sleep"


class BoundaryKind(StrEnum):
    """What the next exact boundary is."""

    THRESHOLD = "threshold"
    DEPLETION = "depletion"
    WAKE = "wake"


class TransitionReason(StrEnum):
    """Why one accepted interval changed the body's fatigue state."""

    NONE = "none"
    THRESHOLD = "threshold"
    DEPLETION = "depletion"
    WAKE = "wake"
    SATURATION = "saturation"


class IntervalCompletion(StrEnum):
    """How a consumer treats an exhaustion boundary inside a long interval."""

    INTERRUPTIBLE = "interruptible"
    INDIVISIBLE = "indivisible"
    TERMINAL_COMBAT = "terminal_combat"


@dataclass(frozen=True)
class StageBand:
    """One authored exclusive awake stage band with its exact travel scale."""

    stage: FatigueStage
    minimum_units: int
    maximum_units: int
    foot_speed_scale: Fraction


@dataclass(frozen=True)
class FatiguePolicy:
    """The validated, immutable fatigue policy loaded from ``fatigue.yaml``."""

    units_per_percent: int
    max_units: int
    wake_units: int
    rates: Mapping[FatigueActivity, int]
    bands: tuple[StageBand, ...]

    def band_for(self, reserve_units: int) -> StageBand:
        """Return the band owning ``reserve_units`` (reserve zero reads severe)."""
        for band in self.bands:
            if reserve_units >= band.minimum_units:
                return band
        return self.bands[-1]

    def outgoing_band(self, reserve_units: int) -> StageBand:
        """Return the band governing the interval that starts at the state.

        A reserve exactly on a band floor is still that band's last instant,
        but the next unit consumed belongs to the lower band, so the outgoing
        travel scale is the lower band's. Reserve zero stays in the severe band
        (a body at zero has not been latched yet only in a transient state).
        """
        probe = 0 if reserve_units <= 0 else reserve_units - 1
        return self.band_for(probe)


@dataclass(frozen=True)
class FatigueState:
    """One validated body's exact reserve and posture."""

    reserve_units: int
    posture: SleepPosture


@dataclass(frozen=True)
class FatigueBoundary:
    """The next exact fatigue event, offset in game seconds from a state."""

    offset_seconds: Fraction
    kind: BoundaryKind
    reserve_units: int


@dataclass(frozen=True)
class FatiguePrediction:
    """One immutable interval prediction; nothing here touches persistent state.

    ``end`` is the state after the full requested ``seconds``.
    ``applicable_seconds`` is the duration an interruptible caller may commit
    now (the first whole second at or after the next boundary), or the whole
    requested duration for an indivisible completion or terminal settlement.
    """

    activity: FatigueActivity
    seconds: int
    completion: IntervalCompletion
    start: FatigueState
    end: FatigueState
    boundary: FatigueBoundary | None
    transition: TransitionReason
    applicable_seconds: int


@dataclass(frozen=True)
class FatigueInterval:
    """One member's accepted interval, with the state the caller predicted from."""

    entity: Any
    activity: FatigueActivity
    seconds: int
    start_state: FatigueState
    completion: IntervalCompletion = IntervalCompletion.INTERRUPTIBLE


@dataclass(frozen=True)
class FatigueCommit:
    """One interval committed by :func:`settle_fatigue_intervals`."""

    entity: Any
    activity: FatigueActivity
    seconds: int
    completion: IntervalCompletion
    start: FatigueState
    end: FatigueState
    transition: TransitionReason


@dataclass(frozen=True)
class FatigueSettlement:
    """The committed fatigue intervals, in caller order."""

    commits: tuple[FatigueCommit, ...]


_SCALE_FIELDS = frozenset({"value"})
_RATE_FIELDS = frozenset({"activity", "units_per_second"})
_STAGE_FIELDS = frozenset(
    {
        "stage",
        "minimum_units",
        "maximum_units",
        "foot_speed_numerator",
        "foot_speed_denominator",
    }
)
_SCALE_IDS = frozenset(
    {"reserve_units_per_percent", "reserve_max_units", "wake_threshold_units"}
)
_AWAKE_STAGES = (
    FatigueStage.NORMAL,
    FatigueStage.LIGHT,
    FatigueStage.MODERATE,
    FatigueStage.SEVERE,
)


def _rulebook_error(message: str) -> FatigueRulebookError:
    return FatigueRulebookError(f"fatigue.yaml: {message}")


def _require_int(where: str, data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _rulebook_error(f"{where}: {key} must be an integer")
    return value


def _require_text(where: str, data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _rulebook_error(f"{where}: {key} must be a non-empty string")
    return value


def _require_fields(
    where: str, data: Mapping[str, Any], allowed: frozenset[str]
) -> None:
    missing = allowed - set(data)
    if missing:
        raise _rulebook_error(f"{where}: missing fields {sorted(missing)}")
    unknown = set(data) - allowed
    if unknown:
        raise _rulebook_error(f"{where}: unknown fields {sorted(unknown)}")


def _build_policy(rows: Iterable[SectionedRule]) -> FatiguePolicy:
    scales: dict[str, int] = {}
    rates: dict[FatigueActivity, int] = {}
    bands: list[StageBand] = []
    for row in rows:
        where = f"row {row.id!r}"
        if row.section == "scale":
            _require_fields(where, row.data, _SCALE_FIELDS)
            if row.id in scales:
                raise _rulebook_error(f"duplicate scale row {row.id!r}")
            scales[row.id] = _require_int(where, row.data, "value")
        elif row.section == "rate":
            _require_fields(where, row.data, _RATE_FIELDS)
            raw = _require_text(where, row.data, "activity")
            try:
                activity = FatigueActivity(raw)
            except ValueError as error:
                raise _rulebook_error(
                    f"{where}: unknown activity {raw!r}"
                ) from error
            if activity in rates:
                raise _rulebook_error(f"duplicate rate row for activity {raw!r}")
            rates[activity] = _require_int(where, row.data, "units_per_second")
        elif row.section == "stage":
            _require_fields(where, row.data, _STAGE_FIELDS)
            raw = _require_text(where, row.data, "stage")
            try:
                stage = FatigueStage(raw)
            except ValueError as error:
                raise _rulebook_error(f"{where}: unknown stage {raw!r}") from error
            if stage not in _AWAKE_STAGES:
                raise _rulebook_error(
                    f"{where}: stage {raw!r} is not an awake reserve stage"
                )
            if any(band.stage is stage for band in bands):
                raise _rulebook_error(f"duplicate stage row for {raw!r}")
            numerator = _require_int(where, row.data, "foot_speed_numerator")
            denominator = _require_int(where, row.data, "foot_speed_denominator")
            if denominator <= 0 or numerator <= 0 or numerator > denominator:
                raise _rulebook_error(
                    f"{where}: foot-speed scale must be a positive fraction <= 1"
                )
            bands.append(
                StageBand(
                    stage=stage,
                    minimum_units=_require_int(where, row.data, "minimum_units"),
                    maximum_units=_require_int(where, row.data, "maximum_units"),
                    foot_speed_scale=Fraction(numerator, denominator),
                )
            )
        else:
            raise _rulebook_error(f"row {row.id!r}: unknown section {row.section!r}")

    if set(scales) != _SCALE_IDS:
        raise _rulebook_error(
            f"scale rows must be exactly {sorted(_SCALE_IDS)}, got {sorted(scales)}"
        )
    units_per_percent = scales["reserve_units_per_percent"]
    max_units = scales["reserve_max_units"]
    wake_units = scales["wake_threshold_units"]
    if units_per_percent <= 0:
        raise _rulebook_error("reserve_units_per_percent must be positive")
    if max_units != units_per_percent * 100:
        raise _rulebook_error(
            "reserve_max_units must equal reserve_units_per_percent * 100"
        )
    if not 0 < wake_units < max_units:
        raise _rulebook_error("wake_threshold_units must lie inside the reserve range")
    if wake_units % units_per_percent:
        raise _rulebook_error(
            "wake_threshold_units must be a whole percentage point"
        )

    if set(rates) != set(FatigueActivity):
        raise _rulebook_error(
            "rate rows must cover exactly "
            f"{sorted(activity.value for activity in FatigueActivity)}"
        )
    for activity, rate in rates.items():
        if rate == 0:
            raise _rulebook_error(f"rate for {activity.value!r} must be non-zero")
        if activity is FatigueActivity.SLEEP and rate < 0:
            raise _rulebook_error("the sleep rate must restore reserve")
        if activity is not FatigueActivity.SLEEP and rate > 0:
            raise _rulebook_error(
                f"the {activity.value!r} rate must consume reserve"
            )

    if len(bands) != len(_AWAKE_STAGES):
        raise _rulebook_error(
            "stage rows must cover exactly the four awake reserve stages"
        )
    bands.sort(key=lambda band: band.minimum_units, reverse=True)
    if tuple(band.stage for band in bands) != _AWAKE_STAGES:
        raise _rulebook_error(
            "stage bands must be authored normal, light, moderate, severe"
        )
    if bands[0].maximum_units != max_units:
        raise _rulebook_error("the normal band must start at full reserve")
    if bands[-1].minimum_units != 1:
        raise _rulebook_error("the severe band must end at one unit")
    for higher, lower in zip(bands, bands[1:]):
        if lower.maximum_units != higher.minimum_units - 1:
            raise _rulebook_error(
                f"stage bands {higher.stage.value!r} and {lower.stage.value!r} "
                "are not contiguous"
            )
    if any(
        not (0 < band.foot_speed_scale <= 1) for band in bands
    ):
        raise _rulebook_error("foot-speed scales must lie inside (0, 1]")
    if bands[0].foot_speed_scale != 1:
        raise _rulebook_error("the normal stage foot-speed scale must be 1")
    for higher, lower in zip(bands, bands[1:]):
        if lower.foot_speed_scale > higher.foot_speed_scale:
            raise _rulebook_error("foot-speed scales must not increase as reserve falls")
    wake_band = next(
        band
        for band in bands
        if band.minimum_units <= wake_units <= band.maximum_units
    )
    if wake_band.stage is not FatigueStage.MODERATE or (
        wake_band.minimum_units != wake_units
    ):
        raise _rulebook_error(
            "the wake threshold must be the moderate band's floor"
        )

    return FatiguePolicy(
        units_per_percent=units_per_percent,
        max_units=max_units,
        wake_units=wake_units,
        rates=MappingProxyType(dict(rates)),
        bands=tuple(bands),
    )


def load_policy(path: Path | None = None) -> FatiguePolicy:
    """Load and fail-closed validate one fatigue rulebook file."""
    rulebook_path = RULEBOOK_PATH if path is None else Path(path)
    try:
        rows = load_sectioned_rules(rulebook_path)
    except (OSError, yaml.YAMLError, ValueError) as error:
        raise _rulebook_error(str(error)) from error
    return _build_policy(rows)


_POLICY: FatiguePolicy | None = None


def get_policy() -> FatiguePolicy:
    """Return the validated fatigue policy singleton."""
    global _POLICY
    if _POLICY is None:
        _POLICY = load_policy()
    return _POLICY


def _resolve_policy(policy: FatiguePolicy | None) -> FatiguePolicy:
    return get_policy() if policy is None else policy


def validate_fatigue_state(
    reserve_units: Any,
    posture: Any,
    policy: FatiguePolicy | None = None,
) -> FatigueState:
    """Validate one reserve/posture pair without writing anything."""
    resolved = _resolve_policy(policy)
    if isinstance(reserve_units, bool) or not isinstance(reserve_units, int):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_TYPE,
            f"mental reserve must be an integer, got {reserve_units!r}",
        )
    if not 0 <= reserve_units <= resolved.max_units:
        raise FatigueStateError(
            FatigueRejectReason.OUT_OF_RANGE,
            f"mental reserve {reserve_units} is outside 0..{resolved.max_units}",
        )
    if isinstance(posture, SleepPosture):
        resolved_posture = posture
    else:
        try:
            resolved_posture = SleepPosture(posture)
        except ValueError as error:
            raise FatigueStateError(
                FatigueRejectReason.UNKNOWN_POSTURE,
                f"unknown sleep posture {posture!r}",
            ) from error
    return FatigueState(reserve_units=reserve_units, posture=resolved_posture)


def _attributes_of(entity: Any) -> Any:
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        raise FatigueStateError(
            FatigueRejectReason.MISSING,
            "entity exposes no attribute store",
        )
    return attributes


def read_fatigue_state(
    entity: Any, policy: FatiguePolicy | None = None
) -> FatigueState:
    """Read and validate one body's fatigue state; never writes physiology."""
    attributes = _attributes_of(entity)
    if not attributes.has(RESERVE_ATTRIBUTE) or not attributes.has(POSTURE_ATTRIBUTE):
        raise FatigueStateError(
            FatigueRejectReason.MISSING,
            "entity has no constructed mental-reserve state",
        )
    reserve_units = attributes.get(RESERVE_ATTRIBUTE, default=_MISSING)
    posture = attributes.get(POSTURE_ATTRIBUTE, default=_MISSING)
    if reserve_units is _MISSING or posture is _MISSING:
        raise FatigueStateError(
            FatigueRejectReason.MISSING,
            "entity mental-reserve state is absent",
        )
    return validate_fatigue_state(reserve_units, posture, policy)


def write_fatigue_state(
    entity: Any,
    reserve_units: Any,
    posture: Any,
    policy: FatiguePolicy | None = None,
) -> FatigueState:
    """Persist one validated reserve/posture pair through the fatigue writer."""
    state = validate_fatigue_state(reserve_units, posture, policy)
    attributes = _attributes_of(entity)
    attributes.add(RESERVE_ATTRIBUTE, state.reserve_units)
    attributes.add(POSTURE_ATTRIBUTE, state.posture.value)
    return state


def initialize_fatigue_state(
    entity: Any, policy: FatiguePolicy | None = None
) -> bool:
    """Establish the full/awake construction baseline only when wholly absent.

    Returns ``True`` when the baseline was written. Any already-present value
    (valid or malformed) is left untouched: this initializer is a construction
    step, never a repair or a refill, and reads still reject malformed state.
    """
    resolved = _resolve_policy(policy)
    attributes = _attributes_of(entity)
    if attributes.has(RESERVE_ATTRIBUTE) or attributes.has(POSTURE_ATTRIBUTE):
        return False
    write_fatigue_state(entity, resolved.max_units, SleepPosture.AWAKE, resolved)
    return True


def _require_state(state: Any, policy: FatiguePolicy) -> FatigueState:
    if not isinstance(state, FatigueState):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_START_STATE,
            f"expected a FatigueState, got {state!r}",
        )
    return validate_fatigue_state(
        state.reserve_units, state.posture, policy
    )


def _require_activity(activity: Any) -> FatigueActivity:
    if not isinstance(activity, FatigueActivity):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_TYPE,
            f"unknown fatigue activity {activity!r}",
        )
    return activity


def _require_seconds(seconds: Any) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise FatigueStateError(
            FatigueRejectReason.INVALID_SECONDS,
            f"interval seconds must be a non-negative integer, got {seconds!r}",
        )
    return seconds


def _require_completion(completion: Any) -> IntervalCompletion:
    if not isinstance(completion, IntervalCompletion):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_TYPE,
            f"unknown interval completion {completion!r}",
        )
    return completion


def _require_compatible(state: FatigueState, activity: FatigueActivity) -> None:
    if state.posture is SleepPosture.AWAKE:
        if activity is FatigueActivity.SLEEP:
            raise FatigueStateError(
                FatigueRejectReason.ACTIVITY_POSTURE_MISMATCH,
                "an awake body cannot settle a sleeping interval",
            )
    elif activity is not FatigueActivity.SLEEP:
        raise FatigueStateError(
            FatigueRejectReason.ACTIVITY_POSTURE_MISMATCH,
            f"a {state.posture.value} body cannot settle a {activity.value} interval",
        )


def fatigue_stage(
    state: FatigueState, policy: FatiguePolicy | None = None
) -> FatigueStage:
    """Return the exclusive instantaneous fatigue stage of one body."""
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    if state.posture is SleepPosture.FORCED:
        return FatigueStage.FORCED_SLEEP
    if state.posture is SleepPosture.VOLUNTARY:
        return FatigueStage.SLEEPING
    return resolved.band_for(state.reserve_units).stage


def foot_speed_scale(
    state: FatigueState, policy: FatiguePolicy | None = None
) -> Fraction:
    """Return the exact foot-speed scale of the state's instantaneous stage.

    Sleeping bodies cannot travel (``TRAVEL_FORBIDDEN``). A movement segment
    that starts exactly on a stage floor consumes the lower stage's speed for
    its whole first unit, so callers integrating an interval use
    :func:`outgoing_foot_speed_scale` instead.
    """
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    if state.posture is not SleepPosture.AWAKE:
        raise FatigueStateError(
            FatigueRejectReason.TRAVEL_FORBIDDEN,
            f"a {state.posture.value} body cannot travel",
        )
    return resolved.band_for(state.reserve_units).foot_speed_scale


def outgoing_foot_speed_scale(
    state: FatigueState, policy: FatiguePolicy | None = None
) -> Fraction:
    """Return the scale governing the travel interval that starts at ``state``.

    The instantaneous stage of a reserve exactly on a band floor is the higher
    band, but the next unit consumed belongs to the lower band, so movement
    segments that begin on a floor travel at the lower band's scale. This is
    the scale a movement consumer applies to one accepted whole-second segment.
    """
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    if state.posture is not SleepPosture.AWAKE:
        raise FatigueStateError(
            FatigueRejectReason.TRAVEL_FORBIDDEN,
            f"a {state.posture.value} body cannot travel",
        )
    return resolved.outgoing_band(state.reserve_units).foot_speed_scale


def travel_allowed(state: FatigueState) -> bool:
    """Whether the body may travel at all (sleep forbids it, targeting does not)."""
    return state.posture is SleepPosture.AWAKE


def actions_allowed(state: FatigueState) -> bool:
    """Whether the body may take ordinary actions (sleep forbids them)."""
    return state.posture is SleepPosture.AWAKE


def sleep_blocks_actions(entity: Any) -> bool:
    """Whether one body's stored posture currently forbids ordinary actions.

    A no-create query for preflight and presentation: it reads the persisted
    posture directly and never validates or materializes physiology, so a
    body with no fatigue state (an authoring fixture or a non-physiological
    creature) is not blocked. A malformed stored posture fails closed
    (forbidden) rather than letting an unrecognizable body act.
    """
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return False
    posture = attributes.get(POSTURE_ATTRIBUTE, default=None)
    if posture is None:
        return False
    if isinstance(posture, SleepPosture):
        return posture is not SleepPosture.AWAKE
    try:
        return SleepPosture(posture) is not SleepPosture.AWAKE
    except (TypeError, ValueError):  # observability: ignore R2: a malformed stored posture fails closed as forbidden; this read touches no state and has no I/O to report
        return True


def reserve_percent(
    state: FatigueState, policy: FatiguePolicy | None = None
) -> int:
    """Return the display-only rounded percentage of one exact reserve.

    Eligibility always reads the stored units; this helper exists only for
    presentation. Half-up integer rounding keeps the result independent of
    floating point, and a reserve one unit below a threshold can round to that
    threshold's displayed percent while its stage still comes from the exact
    units.
    """
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    return (state.reserve_units * 100 + resolved.max_units // 2) // resolved.max_units


#: The exclusive physiological projection: one buff key per projected stage.
#: ``NORMAL`` has no projection and ordinary sleep has none either; the
#: persisted posture, not a buff, is what forbids their actions.
PROJECTION_BUFF_KEYS: Mapping[FatigueStage, str] = MappingProxyType(
    {
        FatigueStage.LIGHT: "fatigue_light",
        FatigueStage.MODERATE: "fatigue_moderate",
        FatigueStage.SEVERE: "fatigue_severe",
        FatigueStage.FORCED_SLEEP: "fatigue_forced_sleep",
    }
)

#: Every buff key the projection owns; external removal must exclude these.
PHYSIOLOGICAL_BUFF_KEYS: frozenset[str] = frozenset(PROJECTION_BUFF_KEYS.values())

_PROJECTION_DEFINITIONS_VALIDATED = False


def _validate_projection_definitions() -> None:
    """Fail closed unless every projection key is a protected debuff definition."""
    global _PROJECTION_DEFINITIONS_VALIDATED
    if _PROJECTION_DEFINITIONS_VALIDATED:
        return
    for key in PROJECTION_BUFF_KEYS.values():
        definition = BUFF_DEFINITIONS.get(key)
        if definition is None:
            raise FatigueRulebookError(
                f"buffs.yaml: fatigue projection key {key!r} is not defined"
            )
        if definition.protection != PHYSIOLOGICAL_PROTECTION:
            raise FatigueRulebookError(
                f"buffs.yaml: fatigue projection key {key!r} must declare "
                f"protection {PHYSIOLOGICAL_PROTECTION!r}"
            )
    _PROJECTION_DEFINITIONS_VALIDATED = True


def projected_buff_key(
    state: FatigueState, policy: FatiguePolicy | None = None
) -> str | None:
    """Return the one protected buff key the state projects, or ``None``."""
    return PROJECTION_BUFF_KEYS.get(fatigue_stage(state, policy))


def project_fatigue_status(
    entity: Any,
    state: FatigueState | None = None,
    policy: FatiguePolicy | None = None,
) -> str | None:
    """Reconcile one body's exclusive protected status inside the current write.

    Reads (and validates) the body's persisted state when ``state`` is
    omitted, removes every other live projection, then mounts the desired one
    through the public :func:`world.rules.buffs.apply_buff` entry point so the
    grant-time guards stay binding. A body without a BuffHandler (a pure
    attribute double) has nothing to project. Callers own the enclosing
    transaction; :func:`settle_fatigue_intervals` calls this for every accepted
    interval before the transaction commits.
    """
    resolved = _resolve_policy(policy)
    current = read_fatigue_state(entity, resolved) if state is None else _require_state(state, resolved)
    desired = projected_buff_key(current, resolved)
    buffs = getattr(entity, "buffs", None)
    if buffs is None:
        return desired
    _validate_projection_definitions()
    active = entity_active_buffs(entity)
    for key in PHYSIOLOGICAL_BUFF_KEYS:
        if key != desired and key in active:
            buffs.remove(key, dispel=True)
    if desired is not None and desired not in active:
        # Reserve/posture are canonical: a threshold crossing is not an
        # action outcome, so the projection must not fire the authored
        # ``negative_buff_added`` reactions (which could write unrelated
        # pleasure state outside this settlement's rollback surfaces).
        apply_buff(entity, desired, dispatch_reaction=False)
    return desired


def next_fatigue_boundary(
    state: FatigueState,
    activity: FatigueActivity,
    policy: FatiguePolicy | None = None,
    *,
    in_combat: bool = False,
) -> FatigueBoundary | None:
    """Return the next exact boundary of the declared activity, or ``None``.

    Consumption reports the next lower stage floor (strictly below the
    current reserve) or depletion at zero; sleep reports the forced-sleep wake
    threshold outside live combat (immediately when the reserve already
    qualifies), and nothing for voluntary sleep or while a battle is live.
    """
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    activity = _require_activity(activity)
    _require_compatible(state, activity)
    if activity is FatigueActivity.SLEEP:
        if state.posture is SleepPosture.VOLUNTARY or in_combat:
            return None
        offset = Fraction(
            max(0, resolved.wake_units - state.reserve_units),
            resolved.rates[activity],
        )
        return FatigueBoundary(offset, BoundaryKind.WAKE, resolved.wake_units)
    # Leaving each awake band happens at that band's floor (the floor is the
    # band's last instant, and the next consumed unit is already the lower
    # band's; ``foot_speed_scale`` is directional for exactly that reason).
    # The severe band has no lower band: its next boundary is depletion at
    # zero, so its own floor of one unit is not a reported threshold.
    threshold = max(
        [
            band.minimum_units
            for band in resolved.bands[:-1]
            if band.minimum_units < state.reserve_units
        ]
        + [0]
    )
    rate = -resolved.rates[activity]
    kind = (
        BoundaryKind.DEPLETION if threshold == 0 else BoundaryKind.THRESHOLD
    )
    return FatigueBoundary(
        Fraction(state.reserve_units - threshold, rate), kind, threshold
    )


def predict_interval(
    state: FatigueState,
    activity: FatigueActivity,
    seconds: int,
    policy: FatiguePolicy | None = None,
    *,
    in_combat: bool = False,
    completion: IntervalCompletion = IntervalCompletion.INTERRUPTIBLE,
) -> FatiguePrediction:
    """Predict one interval's exact effect without writing or reading the world.

    ``end`` is the state after the full requested ``seconds``; exhaustion
    inside an indivisible action or terminal combat settlement is therefore a
    completion fact, never retroactive sleeping time. ``applicable_seconds``
    is what an interruptible caller may commit now.
    """
    resolved = _resolve_policy(policy)
    state = _require_state(state, resolved)
    activity = _require_activity(activity)
    seconds = _require_seconds(seconds)
    completion = _require_completion(completion)
    _require_compatible(state, activity)
    suppress_wake = in_combat or completion is IntervalCompletion.TERMINAL_COMBAT
    rate = resolved.rates[activity]
    reserve = min(resolved.max_units, max(0, state.reserve_units + rate * seconds))
    boundary = next_fatigue_boundary(
        state, activity, resolved, in_combat=suppress_wake
    )

    posture = state.posture
    transition = TransitionReason.NONE
    if activity is FatigueActivity.SLEEP:
        if state.posture is SleepPosture.FORCED and not suppress_wake and (
            state.reserve_units >= resolved.wake_units
            or reserve >= resolved.wake_units
        ):
            posture = SleepPosture.AWAKE
            transition = TransitionReason.WAKE
        elif reserve == resolved.max_units and state.reserve_units < resolved.max_units:
            transition = TransitionReason.SATURATION
    else:
        if reserve == 0:
            posture = SleepPosture.FORCED
            transition = TransitionReason.DEPLETION
        elif (
            resolved.band_for(reserve).stage
            is not resolved.band_for(state.reserve_units).stage
        ):
            transition = TransitionReason.THRESHOLD

    end = FatigueState(reserve_units=reserve, posture=posture)
    if completion is IntervalCompletion.INTERRUPTIBLE and boundary is not None:
        applicable = min(seconds, max(0, ceil(boundary.offset_seconds)))
    else:
        applicable = seconds
    return FatiguePrediction(
        activity=activity,
        seconds=seconds,
        completion=completion,
        start=state,
        end=end,
        boundary=boundary,
        transition=transition,
        applicable_seconds=applicable,
    )


def _plan_interval(
    interval: FatigueInterval,
    policy: FatiguePolicy,
    in_combat: bool,
) -> FatiguePrediction:
    if not isinstance(interval, FatigueInterval):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_TYPE,
            f"expected a FatigueInterval, got {interval!r}",
        )
    current = read_fatigue_state(interval.entity, policy)
    if not isinstance(interval.start_state, FatigueState):
        raise FatigueStateError(
            FatigueRejectReason.INVALID_START_STATE,
            f"interval declares no usable start state: {interval.start_state!r}",
        )
    if validate_fatigue_state(
        interval.start_state.reserve_units, interval.start_state.posture, policy
    ) != current:
        raise FatigueStateError(
            FatigueRejectReason.STALE_START,
            "interval start state no longer matches the member's state",
        )
    prediction = predict_interval(
        current,
        interval.activity,
        interval.seconds,
        policy,
        in_combat=in_combat,
        completion=interval.completion,
    )
    if (
        interval.completion is IntervalCompletion.INTERRUPTIBLE
        and prediction.applicable_seconds < interval.seconds
    ):
        raise FatigueStateError(
            FatigueRejectReason.INTERRUPTIBLE_OVERRUN,
            "an interruptible interval crosses a fatigue boundary; commit "
            "only the accepted whole seconds",
        )
    return prediction


def _transition_event_context(
    entity: Any, prediction: FatiguePrediction, context: Mapping[str, Any]
) -> dict[str, Any]:
    payload: dict[str, Any] = dict(context)
    payload["char"] = str(getattr(entity, "key", None) or getattr(entity, "pk", ""))
    location = getattr(entity, "location", None)
    room = getattr(location, "key", None) if location is not None else None
    if room is not None:
        payload["room"] = str(room)
    payload["reason"] = (
        prediction.transition.value
        if prediction.transition is not TransitionReason.NONE
        else "reserve_change"
    )
    return payload


def settle_fatigue_intervals(
    intervals: Iterable[FatigueInterval],
    *,
    context: Mapping[str, Any] | None = None,
    in_combat: bool = False,
) -> FatigueSettlement:
    """Commit accepted intervals atomically and emit committed transitions.

    Every affected member is validated and predicted before the first write.
    Any failure restores every snapshotted reserve/posture attribute (durable
    rows roll back with the transaction) and re-raises, so no success event is
    ever emitted for a rolled-back write.
    """
    policy = get_policy()
    planned: list[tuple[FatigueInterval, FatiguePrediction]] = []
    seen: set[int] = set()
    for interval in intervals:
        entity = getattr(interval, "entity", None)
        if entity is None:
            raise FatigueStateError(
                FatigueRejectReason.MISSING, "interval carries no entity"
            )
        if id(entity) in seen:
            raise FatigueStateError(
                FatigueRejectReason.DUPLICATE_MEMBER,
                "one settlement cannot list the same member twice",
            )
        seen.add(id(entity))
        planned.append((interval, _plan_interval(interval, policy, in_combat)))

    caller_context = dict(context or {})
    snapshots: list[tuple[Any, dict[str, tuple[bool, Any]]]] = []
    for interval, _ in planned:
        entity = interval.entity
        snapshots.append(
            (
                entity,
                {
                    key: attribute_snapshot(entity, key, category)
                    for key, category in FATIGUE_ATTRIBUTE_SURFACES
                },
            )
        )
    try:
        with transaction.atomic():
            for interval, prediction in planned:
                if prediction.end == prediction.start:
                    continue
                write_fatigue_state(
                    interval.entity,
                    prediction.end.reserve_units,
                    prediction.end.posture,
                    policy,
                )
                # Reconcile the projection in the same atomic unit as the
                # reserve/posture write, so no observer sees a stage that
                # disagrees with the persisted physiology.
                project_fatigue_status(interval.entity, prediction.end, policy)
            for interval, prediction in planned:
                if prediction.end == prediction.start:
                    continue
                payload = _transition_event_context(
                    interval.entity, prediction, caller_context
                )
                transaction.on_commit(
                    lambda payload=payload: log_info(
                        "fatigue_transition", context=payload
                    )
                )
    except Exception:
        for entity, snapshots_by_key in snapshots:
            for key, snapshot in snapshots_by_key.items():
                restore_attribute_best_effort(entity, key, snapshot)
        raise
    return FatigueSettlement(
        commits=tuple(
            FatigueCommit(
                entity=interval.entity,
                activity=prediction.activity,
                seconds=prediction.seconds,
                completion=prediction.completion,
                start=prediction.start,
                end=prediction.end,
                transition=prediction.transition,
            )
            for interval, prediction in planned
        )
    )
