"""Data records for the deterministic defeat aftermath.

The frozen result/outcome/observation handoffs, the validated rulebook
section value types, and the violation hook context shape.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from world.rules.event_log import EventEntry, EventLog


class RecoveryConfig:
    """The validated ``recovery`` section (defeat-aftermath-recovery D-R2)."""

    __slots__ = ("regen_scale", "max_recovery_seconds", "wake_fraction")

    def __init__(
        self, regen_scale: float, max_recovery_seconds: int, wake_fraction: float
    ) -> None:
        self.regen_scale = regen_scale
        self.max_recovery_seconds = max_recovery_seconds
        self.wake_fraction = wake_fraction


@dataclass(frozen=True)
class DigestOutcome:
    """One selected participant's digest result (D-D1/D-D7).

    ``digest`` is the first matching rulebook row's outcome; ``buff`` is
    the mounted rulebook buff key, ``None`` for the ``none`` outcome.
    """

    participant: str
    digest: str
    buff: str | None


@dataclass(frozen=True)
class WakeObservation:
    """One conscious unselected bystander's observation line (D-D7).

    A separate shape from :class:`DigestOutcome`, so a bystander digest —
    a digest row or a buff for an entity the sequence never selected — is
    unrepresentable.
    """

    participant: str
    line: str


@dataclass(frozen=True)
class DefeatAftermathResult:
    """The writer's full handoff to ``settle_session``.

    ``session`` and ``logs`` feed the persisted record and the settlement
    result; ``undo`` is the caller's failure-boundary restoration hook;
    ``departed`` lists the violators whose departure committed and whose
    physical deletion runs post-commit (exam-opponent shape); ``violation``
    is the per-participant outcome mapping keyed by participant key
    (defeat-aftermath-companion-victims D-P3).
    """

    session: Any
    logs: tuple[EventLog, ...]
    undo: Callable[[], None]
    departed: tuple[Any, ...]
    violation: dict[str, "ViolationOutcome"] = field(default_factory=dict)
    digests: tuple[DigestOutcome, ...] = ()
    wake_observations: tuple[WakeObservation, ...] = ()


class DefeatAftermathRulebook:
    """Validated per-section rulebook data owned by this change."""

    __slots__ = (
        "pg_lines",
        "weak_debuff_buff_key",
        "recovery",
        "violation",
        "digest",
    )

    def __init__(
        self,
        pg_lines: tuple[str, ...],
        weak_debuff_buff_key: str,
        recovery: RecoveryConfig,
        violation: "ViolationConfig",
        digest: "DigestConfig",
    ) -> None:
        self.pg_lines = pg_lines
        self.weak_debuff_buff_key = weak_debuff_buff_key
        self.recovery = recovery
        self.violation = violation
        self.digest = digest


@dataclass(frozen=True)
class ViolationDeltas:
    """One attempt's declared pleasure-point deltas (defeat-aftermath-
    violation-sequence). Points ride the shipped ``apply_pleasure_gain``
    path, so wetness, arousal bands, and climax-phase edges follow for free.
    """

    victim_pleasure: int
    aggressor_pleasure: int


@dataclass(frozen=True)
class ArchetypeViolationRow:
    """One monster species' violation scene family (design §4.1)."""

    archetype: str
    victory_pleasure_delta: int
    threshold_ordinal: int
    attempt_cap: int
    attempt_duration_seconds: int
    landed: ViolationDeltas
    resisted: ViolationDeltas
    credited_counters: tuple[str, ...]


@dataclass(frozen=True)
class ViolationConfig:
    """The validated ``violation`` section owned by
    defeat-aftermath-violation-sequence."""

    rows: MappingProxyType
    violated_wake_line: str



@dataclass(frozen=True)
class DigestRow:
    """One first-match digest row (D-D2).

    ``when`` holds the normalized conditions keyed by the closed
    vocabulary: label-list conditions are tuples of canonical labels,
    range conditions are ``(min, max)`` ordinal pairs, and
    ``outcome.zero_landed`` is a bool.
    """

    id: str
    when: MappingProxyType
    outcome: str
    buff: str | None


@dataclass(frozen=True)
class DigestConfig:
    """The validated ``digest`` section owned by
    defeat-aftermath-digest-narrative."""

    rows: tuple[DigestRow, ...]



@dataclass(frozen=True)
class ViolationHookContext:
    """The settlement context the guarded violation body receives (DA4).

    ``entries`` is the aftermath's own EventLog sink, so entries the body
    appends splice in exactly between ``defeat_settle`` and
    ``violator_depart``; ``restores`` is the writer's undo registry, so the
    body's snapshot/restore closures join the aftermath's failure boundary.
    """

    actor: Any
    session: Any
    battlefield: Any | None
    entries: list[EventEntry]
    restores: list[Callable[[], None]]


@dataclass(frozen=True)
class ViolationOutcome:
    """The in-memory per-participant digest handoff (DA4 D-V7).

    ``participant`` is the selected victim (a pool member targeted at least
    once); ``selected``/``landed``/``resisted``/``climax_delta`` count
    exactly that victim's ``violation_attempt``/``violation_act``/
    ``violation_resisted`` EventLog entries (the entries whose ``target`` is
    this participant) and the climax flags on the acts, so the digest phase
    can consume either surface. ``zero_landed`` is the PG-variant signal for
    this victim. The outcome is never persisted: it is a pure derivation of
    the state-derived dice and declared rows, reproduced by any replay.
    """

    participant: str
    selected: int
    landed: int
    resisted: int
    climax_delta: int
    zero_landed: bool
