"""Deterministic defeat aftermath (defeat-aftermath-core).

Runs inside ``settle_session``'s ``transaction.atomic()`` for every
hostile-mode ``outcome == "defeat"`` settlement, on the deterministic-core
side of the single-writer boundary (parent design §4.1). The writer floors
the defeated player at the nonlethal HP floor, marks the knockout, departs
the living violators (population despawn; quest-bound monsters retained with
precedence), mounts the weak debuff, and records the defeat EventLog kinds.
The violation-sequence hook point is guarded by ``DEFEAT_ADULT_SCENES`` and
its body is the defeat-aftermath-violation-sequence engine registered at the
module bottom (DA4 D-V6); with the flag off the hook is never called and the
core-only behavior is the entire settlement.

Rollback contract (design D-C5): the database rows restore through the
transaction, but Evennia's idmapper cache is not transaction-aware, so every
in-process surface the writer touches (actor trait/buff attributes, the
transient battlefield knockout set, the departed monsters' marker and
bookkeeping) is snapshotted at entry and restored by the idempotent
``undo`` closure on every exception boundary — the writer's own, the
settlement's commit/exit failure, and a later outer round-transaction
rollback (armed via :func:`register_pending_undo` because Django has no
rollback hook).

Departure contract (design D-C3, two-phase): the logical departure (marker
clear + bookkeeping drop) commits inside the settlement transaction; the
physical deletion is scheduled through ``transaction.on_commit`` so it runs
only after the outermost durable commit — a rolled-back round discards it.
A post-commit delete failure reverts the logical departure deterministically;
only a process crash in the post-commit window leaves a marker-less live
monster (the parent design's accepted restart-refresh risk).
"""

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from django.conf import settings

from world.observability import log_error, log_info, log_warn
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.sexual_vocab import SENSITIVITY_LEVELS, SHAME_LEVELS
from world.rules.action import (
    _apply_pleasure_gain,
    _attribute_snapshot,
    _restore_attribute,
    _stored_trait_value,
)
from world.rules.buffs import _add_buff
from world.rules.clock import (
    MAX_ADVANCE_SECONDS,
    AdvanceSource,
    _ADVANCE_ENTITY_SURFACES,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.player_messages import defeat_aftermath_template
from world.rules.sexual_act_effects import mutator_name_for
from world.rules.sexual_resist import resist_verdict
from world.rules.sexual_state import AROUSAL_LEVELS
from world.rules.state_derived_roll import derived_roll

_DEFEAT_AFTERMATH_PATH = Path(__file__).parent / "rulebook" / "defeat_aftermath.yaml"
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


def _validate_pg_lines(raw: dict[str, Any], path: Path) -> tuple[str, ...]:
    pg_lines = raw.get("pg_lines")
    if (
        not isinstance(pg_lines, list)
        or not pg_lines
        or any(not isinstance(line, str) or not line.strip() for line in pg_lines)
    ):
        raise ValueError(
            f"{path}: section 'pg_lines' must be a nonempty list of nonempty strings"
        )
    return tuple(pg_lines)


def _validate_weak_debuff(raw: dict[str, Any], path: Path) -> str:
    weak_debuff = raw.get("weak_debuff")
    if not isinstance(weak_debuff, dict) or not isinstance(
        weak_debuff.get("buff_key"), str
    ):
        raise ValueError(
            f"{path}: section 'weak_debuff' must be a mapping with a string 'buff_key'"
        )
    from world.rules.buffs import BUFF_DEFINITIONS

    if weak_debuff["buff_key"] not in BUFF_DEFINITIONS:
        raise ValueError(
            f"{path}: weak_debuff buff_key {weak_debuff['buff_key']!r} "
            "is not a rulebook buff"
        )
    return weak_debuff["buff_key"]


def _validate_recovery(raw: dict[str, Any], path: Path) -> RecoveryConfig:
    """Validate the ``recovery`` section fail-closed (delta requirement 3).

    ``regen_scale`` must be a finite real in ``(0, 1]``: a scale above 1 makes
    the real un-scaled advance heal less than the virtual solve, so the
    downward-only clamp could never pin the mandatory exact-target wake
    (rubber-duck plan review finding 7). ``max_recovery_seconds`` is bounded
    by the clock's one-advance day bound so the capped advance can never raise
    ``ClockAdvanceBoundError``.
    """
    recovery = raw.get("recovery")
    if not isinstance(recovery, dict):
        raise ValueError(f"{path}: section 'recovery' must be a mapping")
    scale = recovery.get("regen_scale")
    if (
        isinstance(scale, bool)
        or not isinstance(scale, (int, float))
        or not math.isfinite(scale)
        or not 0 < scale <= 1
    ):
        raise ValueError(
            f"{path}: recovery regen_scale must be a finite real in (0, 1], got {scale!r}"
        )
    cap = recovery.get("max_recovery_seconds")
    if (
        isinstance(cap, bool)
        or not isinstance(cap, int)
        or cap < 1
        or cap > MAX_ADVANCE_SECONDS
    ):
        raise ValueError(
            f"{path}: recovery max_recovery_seconds must be an integer in "
            f"[1, {MAX_ADVANCE_SECONDS}], got {cap!r}"
        )
    fraction = recovery.get("wake_fraction")
    if (
        isinstance(fraction, bool)
        or not isinstance(fraction, (int, float))
        or not math.isfinite(fraction)
        or not 0 < fraction < 1
    ):
        raise ValueError(
            f"{path}: recovery wake_fraction must be a finite real in (0, 1), got {fraction!r}"
        )
    return RecoveryConfig(
        regen_scale=float(scale),
        max_recovery_seconds=int(cap),
        wake_fraction=float(fraction),
    )


@dataclass(frozen=True)
class ViolationDeltas:
    """One attempt's declared pleasure-point deltas (defeat-aftermath-
    violation-sequence). Points ride the shipped ``_apply_pleasure_gain``
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


_SECTION_VALIDATORS: dict[str, Callable[[dict[str, Any], Path], Any]] = {}


def _register_section_validator(
    name: str, validator: Callable[[dict[str, Any], Path], Any]
) -> None:
    """Register one owned section's validator (design D-C8 seam)."""
    if name in _SECTION_VALIDATORS:
        raise ValueError(f"defeat-aftermath section validator {name!r} already registered")
    _SECTION_VALIDATORS[name] = validator


_register_section_validator("pg_lines", _validate_pg_lines)
_register_section_validator("weak_debuff", _validate_weak_debuff)
_register_section_validator("recovery", _validate_recovery)
_register_section_validator("violation", _validate_violation)
_register_section_validator("digest", _validate_digest)
_OWNED_SECTIONS = frozenset(_SECTION_VALIDATORS)


def load_defeat_aftermath_sections(path: Path) -> DefeatAftermathRulebook:
    """Load the defeat-aftermath rulebook, validating owned sections.

    Unknown sections belong to downstream changes and are ignored with one
    ``log_warn`` (design D-C8); each owned section is parsed by the validator
    registered for it in ``_SECTION_VALIDATORS``, and a malformed owned
    section fails closed at load like every other rulebook.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping of sections")
    unknown = sorted(str(key) for key in set(raw) - _OWNED_SECTIONS)
    if unknown:
        log_warn(
            "defeat_aftermath_unknown_section_ignored",
            context={"path": str(path), "sections": ", ".join(unknown)},
        )
    validated = {name: validator(raw, path) for name, validator in _SECTION_VALIDATORS.items()}
    return DefeatAftermathRulebook(
        pg_lines=validated["pg_lines"],
        weak_debuff_buff_key=validated["weak_debuff"],
        recovery=validated["recovery"],
        violation=validated["violation"],
        digest=validated["digest"],
    )


DEFEAT_AFTERMATH_RULEBOOK = load_defeat_aftermath_sections(_DEFEAT_AFTERMATH_PATH)

_VIOLATION_HOOK: Callable[..., None] | None = None
_PENDING_OUTER_UNDOS: list[Callable[[], None]] = []


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


def register_pending_undo(undo: Callable[[], None]) -> None:
    """Arm the aftermath undo for a later outer-transaction rollback.

    A defeat settled inside a nested round transaction (the ordinary
    submission path) can still be rolled back by the enclosing transaction
    AFTER ``settle_session`` returned, and Django has no rollback hook. The
    round wrapper drains and runs the armed undo on its failure boundary and
    discards it on success; ``undo`` is idempotent.
    """
    _PENDING_OUTER_UNDOS.append(undo)


def drain_pending_undos() -> list[Callable[[], None]]:
    """Return and clear every armed undo (run them, or discard on commit)."""
    pending = list(_PENDING_OUTER_UNDOS)
    _PENDING_OUTER_UNDOS.clear()
    return pending


def solve_recovery_seconds(
    current: float,
    carried: float,
    rate: float,
    scale: float,
    target: int,
    cap: int,
) -> tuple[int, bool]:
    """Solve the minimum whole seconds of scaled regen to reach ``target``.

    Pure settlement math over the stored gauge-regen model (D-R1/D-R2): the
    virtual scaled model is ``floor(current + carried + rate * scale * t)``,
    the exact float arithmetic ``_settle_gauge_regen`` uses. Returns
    ``(seconds, capped)``. ``t = 0`` when the stored state is already at or
    above the target. A non-positive scaled rate, or a solve whose minimum
    ``t`` exceeds ``cap`` (the closed form normalizes against the float
    model first), returns ``(cap, True)`` — the caller settles at the HP the
    capped virtual model produces and reports loudly (D-R3).
    """
    headroom = target - (current + carried)
    if headroom <= 0:
        return 0, False
    scaled_rate = rate * scale
    if scaled_rate <= 0:
        return cap, True
    seconds = min(max(math.ceil(headroom / scaled_rate), 0), cap)
    # Normalize the closed form against the clock's exact float model: the
    # guards move at most one step for floating-point boundary error.
    while seconds < cap and math.floor(current + carried + scaled_rate * seconds) < target:
        seconds += 1
    while seconds > 0 and math.floor(current + carried + scaled_rate * (seconds - 1)) >= target:
        seconds -= 1
    reached = math.floor(current + carried + scaled_rate * seconds) >= target
    return seconds, not reached


def _recovery_scope(actor: Any, battlefield: Any | None) -> list[Any]:
    """The recovery advance's entity scope: the actor's living allies.

    Mirror of the combat settlement's scope filter restricted to the actor's
    own team: living, non-fled teammates regen for the window exactly like
    any other clock advance (design D-R1), while foes — including a retained
    quest-bound winner and violators already logically departed — are never
    in scope, so the recovery window cannot mutate an opponent's gauges
    (rubber-duck plan review finding 4).
    """
    if battlefield is None:
        return [actor] if _stored_trait_value(actor.traits.hp) > 0 else []
    team = battlefield.team_of(str(actor.key))
    allies = battlefield.teams.get(team, set()) if team is not None else {str(actor.key)}
    return [
        battlefield.roster[key]
        for key in allies
        if key not in battlefield.fled
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
    ]


def register_violation_hook(hook: Callable[..., None]) -> None:
    """Register the violation-sequence body contributed by an adult change.

    A single registration point: a second distinct registration fails loudly
    instead of silently replacing an adult phase; re-registering the
    identical callable is accepted so idempotent boot registration stays
    possible.
    """
    global _VIOLATION_HOOK
    if not callable(hook):
        raise ValueError("the defeat violation hook must be callable")
    if _VIOLATION_HOOK is not None and _VIOLATION_HOOK is not hook:
        raise RuntimeError("the defeat violation hook is already registered")
    _VIOLATION_HOOK = hook


def _call_violation_hook(
    context: ViolationHookContext,
) -> dict[str, ViolationOutcome]:
    """Run the guarded violation hook point (design D-C4).

    Pure guard: with ``DEFEAT_ADULT_SCENES`` off the hook is never called and
    the core-only settlement is the entire behavior; with the flag on but no
    adult body registered the call is a no-op. The flag is read exactly once,
    at hook entry (no mid-sequence toggle semantics, DA4 delta requirement).
    """
    if not settings.DEFEAT_ADULT_SCENES:
        return {}
    if _VIOLATION_HOOK is None:
        return {}
    outcomes = _VIOLATION_HOOK(context)
    return outcomes if outcomes is not None else {}


def _violation_scope(actor: Any) -> list[Any]:
    """The attempt clock advance's entity scope: deliberately empty.

    The attempts spend world time as fiction over the atomic settlement —
    the downed body does not heal, decay, or climax-settle inside its own
    violation. The shipped settlement stages are accumulator-based, so
    every body (the victim included) is caught up unchanged at its next
    in-scope advance (the recovery phase's allies scope, or any later
    advance); boundary stages and world event sources still run, so
    deadlines and restocks cross exactly like any other clock window. An
    entity-scoped advance would regenerate the victim past the recovery
    wake target pinned by defeat-aftermath-recovery and mutate companions
    and violators the change declares untouched (rubber-duck plan review
    finding 2).
    """
    del actor
    return []


def _snapshot_sexual_surfaces(entity: Any) -> Callable[[], None]:
    """Snapshot every durable sexual surface one entity may expose (DA4).

    The clock's advance registry restores what each advance itself touched;
    the violation's deltas are applied between advances, so their surfaces
    are captured here and restored by the caller's undo on any failure —
    the transaction restores the database rows, the idmapper cache needs
    this explicit restore (design D-C5 discipline).
    """
    snapshots = tuple(
        (name, category, _attribute_snapshot(entity, name, category))
        for name, category in _ADVANCE_ENTITY_SURFACES
    )

    def _restore() -> None:
        for name, category, snapshot in snapshots:
            _restore_attribute(entity, name, snapshot, category=category)
        # Drop the materialized ``sexual`` handler so the next access re-mounts
        # from the restored attributes — the same cache invalidation
        # ``_restore_entity_state`` and the clock's advance restore perform
        # (the idmapper-cached handler would otherwise outlive the rollback).
        entity.__dict__.pop("sexual", None)

    return _restore


def _derived_resist_roll(
    session_id: str,
    violator: Any,
    victim_key: str,
    attempt_index: int,
    rolls: list[int],
) -> Callable[[], int]:
    """Build the state-derived d100 source for one resist contest (D-V4).

    The wrapper records every consumed value so the EventLog reports exactly
    the roll the contest used, and nothing when ``resist_verdict``'s shipped
    auto-comply branches return before the dice (finding 3).
    """
    violator_key = str(violator.pk)

    def _roll() -> int:
        value = derived_roll(
            session_id, violator_key, victim_key, attempt_index, "resist"
        )
        rolls.append(value)
        return value

    return _roll


def _apply_violation_deltas(
    victim: Any, aggressor: Any, deltas: ViolationDeltas
) -> None:
    """Apply one attempt's declared pleasure points through the shipped path."""
    if deltas.victim_pleasure:
        _apply_pleasure_gain(victim, deltas.victim_pleasure)
    if deltas.aggressor_pleasure:
        _apply_pleasure_gain(aggressor, deltas.aggressor_pleasure)


def _victim_climax_onset(
    victim: Any, aggressor: Any, deltas: ViolationDeltas
) -> bool:
    """Apply the deltas and report one climax onset.

    An onset is the victim's climax phase pushed into ``進行中`` by this very
    attempt — the digest's climax count and one ``climax: true`` flag on the
    attempt's ``violation_act`` entry, keeping outcome and EventLog counts
    equal by construction.
    """
    was_in_progress = victim.sexual.climax_phase.level == "進行中"
    _apply_violation_deltas(victim, aggressor, deltas)
    return not was_in_progress and victim.sexual.climax_phase.level == "進行中"


def _credit_violation_counters(
    victim: Any, violator: Any, counters: tuple[str, ...]
) -> None:
    """Credit every declared counter on BOTH bodies (DA3 shared convention)."""
    for name in counters:
        mutator = mutator_name_for(name)
        getattr(victim.sexual, mutator)()
        getattr(violator.sexual, mutator)()


def _advance_attempt_clock(
    clock: Any,
    seconds: int,
    scope: list[Any],
    restores: list[Callable[[], None]],
) -> None:
    """Advance the world clock by one attempt's declared duration (DA4).

    Same discipline as the recovery phase: the advance registry and the
    clock tick are snapshotted so the caller's failure boundary can restore
    both the database (through the transaction) and the idmapper cache.
    """
    registry = build_advance_snapshot_registry(
        clock, seconds, AdvanceSource.DEFEAT_AFTERMATH, scope
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    clock.advance(seconds, AdvanceSource.DEFEAT_AFTERMATH, scope)

    def _restore(
        clock=clock, registry=registry, tick=tick_snapshot, scope=tuple(scope)
    ) -> None:
        _restore_clock_tick(clock, tick)
        _restore_advance_registry(registry, scope)

    restores.append(_restore)


def _violation_attempt_entry(
    violator: Any,
    victim: Any,
    attempt_index: int,
    verdict: Any,
    rolls: list[int],
    *,
    player_victim: bool,
) -> EventEntry:
    """One ``violation_attempt`` entry: the contest exactly as it ran.

    ``actor`` is the violator, ``target`` the selected victim; the template
    follows the victim so the offline prose names whoever the attempt
    actually targeted (the player-facing lines stay byte-identical).
    """
    return EventEntry(
        kind="violation_attempt",
        actor=str(violator.key),
        target=str(victim.key),
        data={
            "attempt": attempt_index,
            "roll": rolls[-1] if rolls else None,
            "auto_comply": bool(verdict.auto_comply),
            "actor_score": verdict.actor_score,
            "resister_score": verdict.resister_score,
        },
        text_template=defeat_aftermath_template(
            "violation_attempt" if player_victim else "violation_attempt_companion"
        ),
    )


def _violation_resisted_entry(
    violator: Any, victim: Any, attempt_index: int, *, player_victim: bool
) -> EventEntry:
    """One ``violation_resisted`` entry: the contest outcome went to the prey."""
    return EventEntry(
        kind="violation_resisted",
        actor=str(violator.key),
        target=str(victim.key),
        data={"attempt": attempt_index},
        text_template=defeat_aftermath_template(
            "violation_resisted" if player_victim else "violation_resisted_companion"
        ),
    )


def _violation_act_entry(
    violator: Any, victim: Any, attempt_index: int, climax: bool, *, player_victim: bool
) -> EventEntry:
    """One ``violation_act`` entry: the landed attempt and its climax flag."""
    return EventEntry(
        kind="violation_act",
        actor=str(violator.key),
        target=str(victim.key),
        data={"attempt": attempt_index, "climax": climax},
        text_template=defeat_aftermath_template(
            "violation_act" if player_victim else "violation_act_companion"
        ),
    )


def _companion_wake_entry(victim: Any, outcome: ViolationOutcome) -> EventEntry:
    """One ``companion_wake`` entry: the knocked-out companion's observation.

    Observation-only (DA5 D-P4): the companion settles through the core's
    normal survivor path and is not re-floored; the entry reads the outcome
    and carries its counts for the digest phase, mutating nothing.
    """
    return EventEntry(
        kind="companion_wake",
        actor=str(victim.key),
        target=None,
        data={
            "selected": outcome.selected,
            "landed": outcome.landed,
            "resisted": outcome.resisted,
            "climax": outcome.climax_delta,
            "zero_landed": outcome.zero_landed,
        },
        text_template=defeat_aftermath_template("companion_wake"),
    )


def _rewrite_wake_line(entries: list[EventEntry], violated_wake_line: str) -> None:
    """Swap the ``defeat_settle`` wake prose for the violated variant (DA4).

    The replacement copies the entry's data mapping and changes only
    ``wake``, preserving the core contract's remaining fields (finding 7);
    the entry is rebuilt because ``EventEntry`` is frozen.
    """
    for index, entry in enumerate(entries):
        if entry.kind == "defeat_settle":
            entries[index] = replace(
                entry, data={**entry.data, "wake": violated_wake_line}
            )
            return


def _schedule_violation_boundary(
    actor: Any,
    clock: Any,
    attempts: int,
    landed: int,
    resisted: int,
    climaxes: int,
    victims: int,
) -> None:
    """Schedule the violation phase's boundary info event (observability).

    Fires only on the outermost durable commit, like the aftermath's own
    boundary event; the context is snapshotted as primitives so the callback
    carries no live objects. ``victims`` counts the distinct participants
    selected at least once (D-P3's returned outcome set), never the pool
    members no attempt targeted.
    """
    from django.db import transaction

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": clock.tick,
        "attempts": attempts,
        "landed": landed,
        "resisted": resisted,
        "climax": climaxes,
        "victims": victims,
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info(
            "defeat_aftermath_violation", context=boundary
        )
    )


def _max_sensitivity_label(entity: Any) -> str:
    """The entity's own most sensitive materialized channel (D-D1).

    Reads only the sensitivity traits already present — ``items()`` never
    lazily creates traits, so the digest performs no storage write. An
    entity with no seeded channel reads 普通.
    """
    traits = list(entity.sexual.sensitivity.items())
    if not traits:
        return SENSITIVITY_LEVELS[0]
    return SENSITIVITY_LEVELS[max(trait.value for _, trait in traits)]


def _digest_snapshot(entity: Any, outcome: "ViolationOutcome") -> dict[str, Any]:
    """One participant's terminal digest inputs (D-D1).

    Own-body observations only: the entity's sexual state plus the
    sequence's in-memory outcome handoff. No affinity value, no other
    entity's state, no persisted digest input.
    """
    return {
        "sensitivity_level": _max_sensitivity_label(entity),
        "shame_level": entity.sexual.shame.level,
        "arousal_ordinal": entity.sexual.arousal.value,
        "outcome.climax_count": outcome.climax_delta,
        "outcome.zero_landed": outcome.zero_landed,
    }


def _digest_row_matches(row: DigestRow, snapshot: dict[str, Any]) -> bool:
    """Evaluate one row's normalized conditions against the snapshot."""
    for key, condition in row.when.items():
        value = snapshot[key]
        if isinstance(condition, bool):
            if value is not condition:
                return False
        elif isinstance(condition[0], str):
            if value not in condition:
                return False
        else:
            low, high = condition
            if not low <= value <= high:
                return False
    return True


def _match_digest_row(entity: Any, outcome: "ViolationOutcome") -> DigestRow:
    """First matching digest row for one participant (D-D2).

    The loader guarantees the final row is the empty-``when`` fallback, so
    the loop below always returns; the ``LookupError`` documents the
    invariant rather than guarding a reachable path.
    """
    snapshot = _digest_snapshot(entity, outcome)
    for row in DEFEAT_AFTERMATH_RULEBOOK.digest.rows:
        if _digest_row_matches(row, snapshot):
            return row
    raise LookupError("digest rulebook shipped without its fallback row")


def _rewrite_companion_wake(
    entries: list[EventEntry], victim_key: str, wake_line: str
) -> None:
    """Reselect one selected companion's wake line by digest (D-D3).

    The ``companion_wake`` entry stays the companion's sole wake-up
    record; only its line family changes, so no duplicate wake entry is
    rendered (D-D5's no-duplication discipline). The entry is rebuilt
    because ``EventEntry`` is frozen.
    """
    for index, entry in enumerate(entries):
        if entry.kind == "companion_wake" and entry.actor == victim_key:
            entries[index] = replace(entry, text_template=wake_line)
            return


def _digest_bystanders(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    violation: dict[str, "ViolationOutcome"],
) -> list[Any]:
    """Conscious companions who were never selected (D-D7).

    Mirror of the violation pool's two resolution paths restricted to
    companions neither knocked out nor fled and absent from the outcome
    handoff: an untouched knocked-out companion was unconscious (D-P3's
    wake contract keeps it silent) and the defeated player's wake prose
    is the settlement's own, so neither can be a bystander.
    """
    selected = set(violation)
    actor_key = str(actor.key)
    if battlefield is not None:
        player_team = battlefield.team_of(actor_key)
        ally_keys = (
            battlefield.teams.get(player_team, set())
            if player_team is not None
            else set()
        )
        return [
            battlefield.roster[key]
            for key in ally_keys
            if key != actor_key
            and key not in battlefield.fled
            and key not in battlefield.knocked_out
            and key not in selected
            and key in battlefield.roster
        ]
    from evennia.objects.models import ObjectDB

    return [
        entity
        for dbref in session.player_ids
        if dbref != int(actor.pk)
        and dbref not in session.fled_ids
        and dbref not in session.knocked_out_ids
        for entity in (ObjectDB.objects.filter(id=dbref).first(),)
        if entity is not None and str(entity.key) not in selected
    ]


def _schedule_digest_boundary(
    actor: Any,
    digests: list[DigestOutcome],
    wake_observations: list[WakeObservation],
) -> None:
    """Schedule the digest phase's boundary info event (observability)."""
    from django.db import transaction

    from world.rules.clock import get_world_clock

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": get_world_clock().tick,
        "selected": len(digests),
        "residue": sum(digest.digest == "residue" for digest in digests),
        "humiliated": sum(digest.digest == "humiliated" for digest in digests),
        "none": sum(digest.digest == "none" for digest in digests),
        "bystanders": len(wake_observations),
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info(
            "defeat_aftermath_digest", context=boundary
        )
    )


def _run_digest_phase(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    entries: list[EventEntry],
    restores: list[Callable[[], None]],
    violation: dict[str, "ViolationOutcome"],
) -> tuple[tuple[DigestOutcome, ...], tuple[WakeObservation, ...]]:
    """The digest phase (defeat-aftermath-digest-narrative D-D1/D-D6).

    Runs after the recovery advance: one first-match rulebook row per
    selected participant reads only its own terminal sexual state plus the
    sequence's in-memory outcome handoff. ``residue``/``humiliated`` mount
    their buff through the shipped attach path (companion snapshots join
    the writer's undo registry; the actor's own buffs are already covered
    by the run-entry snapshot), every participant gets one
    ``digest_outcome`` entry, and a digest other than ``none`` reselects
    the participant's wake-line family. Conscious unselected companions
    get a ``wake_observation`` entry and a ``WakeObservation`` row —
    never a digest row or a buff (D-D7).
    """
    entities = {
        str(entity.key): entity
        for entity in _violation_pool(actor, session, battlefield)
    }
    digests: list[DigestOutcome] = []
    wake_observations: list[WakeObservation] = []
    for key, outcome in violation.items():
        entity = entities[key]
        row = _match_digest_row(entity, outcome)
        if row.buff is not None:
            if entity is not actor:
                snapshot = _attribute_snapshot(entity, "buffs")

                def _restore_digest_buffs(
                    entity=entity, snapshot=snapshot
                ) -> None:
                    _restore_attribute(entity, "buffs", snapshot)

                restores.append(_restore_digest_buffs)
            _add_buff(entity, row.buff)
        if entity is actor:
            if row.outcome != "none":
                _rewrite_wake_line(
                    entries,
                    defeat_aftermath_template(f"wake_self_{row.outcome}"),
                )
        elif row.outcome != "none":
            _rewrite_companion_wake(
                entries,
                key,
                defeat_aftermath_template(f"wake_companion_{row.outcome}"),
            )
        digests.append(
            DigestOutcome(participant=key, digest=row.outcome, buff=row.buff)
        )
        entries.append(
            EventEntry(
                kind="digest_outcome",
                actor=key,
                target=None,
                data={"digest": row.outcome, "buff": row.buff},
                text_template=defeat_aftermath_template(
                    "digest_outcome"
                    if entity is actor
                    else "digest_outcome_companion"
                ),
            )
        )
    for entity in _digest_bystanders(actor, session, battlefield, violation):
        key = str(entity.key)
        template = defeat_aftermath_template("wake_bystander")
        wake_observations.append(
            WakeObservation(
                participant=key,
                line=template.format(actor=key, target=None, data={}),
            )
        )
        entries.append(
            EventEntry(
                kind="wake_observation",
                actor=key,
                target=None,
                data={},
                text_template=template,
            )
        )
    _schedule_digest_boundary(actor, digests, wake_observations)
    return tuple(digests), tuple(wake_observations)


_TARGET_PURPOSE = "target"
# The target draw's victim dimension is a constant marker: the victim is the
# draw's OUTPUT (a participant slot resolved through the pool), never an
# input, so the key space stays (session id, violator, attempt index,
# purpose) exactly as the companion-victims design D-P1 lists it.
_TARGET_POOL_KEY = "pool"


def _violation_pool(
    actor: Any, session: Any, battlefield: Any | None
) -> list[Any]:
    """The violation target pool: the player plus knocked-out companions.

    The pool is every non-fled allied participant (the defeated player plus
    each companion in the knocked-out set; conscious companions are not
    victims). Both resolution paths converge on one canonical order — the
    player first, companions by ascending ``pk`` — so the same durable
    session re-derives identical selection from either a reconstructed
    battlefield or the degraded record-only path. The player is always in
    the pool and always first.
    """
    companions: list[Any] = []
    if battlefield is not None:
        player_team = battlefield.team_of(str(actor.key))
        ally_keys = (
            battlefield.teams.get(player_team, set())
            if player_team is not None
            else set()
        )
        for key in ally_keys:
            if key == str(actor.key) or key in battlefield.fled:
                continue
            if key not in battlefield.knocked_out:
                continue
            entity = battlefield.roster.get(key)
            if entity is not None:
                companions.append(entity)
    else:
        from evennia.objects.models import ObjectDB

        for dbref in session.player_ids:
            if dbref == int(actor.pk) or dbref in session.fled_ids:
                continue
            if dbref not in session.knocked_out_ids:
                continue
            entity = ObjectDB.objects.filter(id=dbref).first()
            if entity is not None:
                companions.append(entity)
    companions.sort(key=lambda entity: int(entity.pk))
    return [actor, *companions]


def _select_violation_victim(
    pool: list[Any], session_id: str, violator: Any, attempt_index: int
) -> Any:
    """One attempt's victim: a pure derived draw over the pool (D-P1).

    A solo pool short-circuits to the player without touching the dice —
    the pinned player-only baseline stays byte-identical and an
    auto-complying victim still consumes no roll. Otherwise the state-
    derived helper keys on (session id, violator, attempt index,
    purpose="target") and the draw resolves a participant slot, so a
    rolled-back retry re-derives the identical victim. Fled companions are
    filtered out of the pool before the draw and can never be selected.
    """
    if len(pool) == 1:
        return pool[0]
    draw = derived_roll(
        session_id,
        str(violator.pk),
        _TARGET_POOL_KEY,
        attempt_index,
        _TARGET_PURPOSE,
    )
    return pool[draw % len(pool)]


def run_violation_sequence(
    context: ViolationHookContext,
) -> dict[str, ViolationOutcome]:
    """The registered body of the core's guarded hook (DA4 D-V6, DA5 D-P1).

    Runs between the core's ``defeat_settle`` and ``violator_depart`` phases:
    victory arousal -> archetype threshold gate -> the attempt loop (one
    state-derived victim draw and one state-derived resist contest per
    attempt through the shipped pure ``resist_verdict``, declared deltas
    through the shipped pleasure path onto the selected victim's own
    records, symmetric counter credits, one ``defeat_aftermath``-source
    world-clock advance per attempt, first successful resistance ends that
    violator's pursuit) -> the violated wake line when attempts landed on
    the player and one observation-only wake line per selected companion
    victim. A sequence in which zero attempts landed is the PG variant.
    Every die is a pure function of durable record state (D-V4, D-P1), so a
    rolled-back retry re-derives the identical sequence; the sequence
    persists only its state writes, counter credits, EventLog entries, and
    the clock advances themselves.
    """
    actor = context.actor
    session = context.session
    battlefield = context.battlefield
    entries = context.entries
    restores = context.restores
    rulebook = DEFEAT_AFTERMATH_RULEBOOK.violation
    candidates = sorted(
        _living_foes(actor, session, battlefield),
        key=lambda violator: int(violator.pk),
    )
    if not candidates:
        return {}
    pool = _violation_pool(actor, session, battlefield)
    from world.rules.clock import get_world_clock

    clock = get_world_clock()
    scope = _violation_scope(actor)

    # Undo layering: every pool member's sexual surfaces are snapshotted
    # before any write (any companion may be selected); each row-carrying
    # violator joins right before its victory arousal. Reversed-order undo
    # then unwinds the advances before the deltas, converging on the
    # pre-sequence state.
    restores.append(_snapshot_sexual_surfaces(actor))
    for victim in pool[1:]:
        restores.append(_snapshot_sexual_surfaces(victim))
    # Per-participant tallies (D-P3): participant key -> [selected, landed,
    # resisted, climaxes]. Only participants targeted at least once appear.
    tallies: dict[str, list[int]] = {}
    for violator in candidates:
        row = rulebook.rows.get(str(violator.key))
        if row is None:
            # observability: ignore R3: a missing archetype row is the designed PG degradation (design §5), not an error; no exception object exists to chain
            log_warn(
                "defeat_aftermath_violation_archetype_missing",
                context={
                    "archetype": str(violator.key),
                    "tick": clock.tick,
                    "char": str(actor.key),
                },
            )
            continue
        restores.append(_snapshot_sexual_surfaces(violator))
        # Victory arousal (parent design §3.1 step 2): the delta lands on top
        # of whatever the fight raised, clamped by the pleasure gauge.
        _apply_pleasure_gain(violator, row.victory_pleasure_delta)
        if violator.sexual.arousal < row.threshold_ordinal:
            continue
        for attempt_index in range(row.attempt_cap):
            victim = _select_violation_victim(
                pool, session.session_id, violator, attempt_index
            )
            tally = tallies.setdefault(str(victim.key), [0, 0, 0, 0])
            tally[0] += 1
            rolls: list[int] = []
            verdict = resist_verdict(
                violator,
                victim,
                rng=_derived_resist_roll(
                    session.session_id, violator, str(victim.pk), attempt_index, rolls
                ),
            )
            player_victim = victim is actor
            entries.append(
                _violation_attempt_entry(
                    violator,
                    victim,
                    attempt_index,
                    verdict,
                    rolls,
                    player_victim=player_victim,
                )
            )
            if verdict.resisted:
                tally[2] += 1
                _apply_violation_deltas(victim, violator, row.resisted)
                entries.append(
                    _violation_resisted_entry(
                        violator,
                        victim,
                        attempt_index,
                        player_victim=player_victim,
                    )
                )
                _advance_attempt_clock(
                    clock, row.attempt_duration_seconds, scope, restores
                )
                # D-V5: the first successful resistance cancels this
                # violator's remaining attempts; the shrunk deltas and the
                # spent duration of the resisted attempt are its last.
                break
            tally[1] += 1
            climax = _victim_climax_onset(victim, violator, row.landed)
            tally[3] += int(climax)
            _credit_violation_counters(victim, violator, row.credited_counters)
            entries.append(
                _violation_act_entry(
                    violator,
                    victim,
                    attempt_index,
                    climax,
                    player_victim=player_victim,
                )
            )
            _advance_attempt_clock(
                clock, row.attempt_duration_seconds, scope, restores
            )
    outcomes = {
        key: ViolationOutcome(
            participant=key,
            selected=tally[0],
            landed=tally[1],
            resisted=tally[2],
            climax_delta=tally[3],
            zero_landed=tally[1] == 0,
        )
        for key, tally in tallies.items()
    }
    # The player's wake prose keys on the player's own landed attempts: a
    # sequence that only landed on companions leaves the PG wake line.
    player_outcome = outcomes.get(str(actor.key))
    if player_outcome is not None and not player_outcome.zero_landed:
        _rewrite_wake_line(entries, rulebook.violated_wake_line)
    for victim in pool[1:]:
        outcome = outcomes.get(str(victim.key))
        if outcome is not None:
            entries.append(_companion_wake_entry(victim, outcome))
    if not outcomes:
        return {}
    _schedule_violation_boundary(
        actor,
        clock,
        sum(outcome.selected for outcome in outcomes.values()),
        sum(outcome.landed for outcome in outcomes.values()),
        sum(outcome.resisted for outcome in outcomes.values()),
        sum(outcome.climax_delta for outcome in outcomes.values()),
        len(outcomes),
    )
    return outcomes


def run_defeat_aftermath(
    actor: Any,
    session: Any,
    battlefield: Any | None,
) -> DefeatAftermathResult:
    """Apply the deterministic defeat aftermath inside the caller's transaction.

    Phase order (tasks 1.2): HP floor + knockout mark -> guarded violation
    hook -> violator departure -> weak debuff -> recovery advance ->
    digest -> EventLog. The caller persists
    the returned session record and clears the session afterwards. Every die
    the writer and its registered violation body use is a pure function of
    durable record state, so a rolled-back retry re-derives the identical
    aftermath (design D-C5, DA4 D-V4). Returns a :class:`DefeatAftermathResult`: the
    knockout-marked session record, the aftermath EventLog the caller
    appends to the settlement result, and an idempotent callable that undoes
    every in-process surface the writer touched. The caller MUST run
    ``undo`` on its own failure boundary before the exception propagates:
    the transaction restores the database rows, but the idmapper cache is
    not transaction-aware, and a failure after this writer returns (the
    marker persist, the session clear) must still leave no half-applied
    aftermath (design D-C5).
    """
    hp_before = _stored_trait_value(actor.traits.hp)
    trait_snapshot = _attribute_snapshot(actor, "traits", "traits")
    buff_snapshot = _attribute_snapshot(actor, "buffs")
    knocked_out_before = (
        str(actor.key) in battlefield.knocked_out
        if battlefield is not None
        else False
    )
    restores: list[Callable[[], None]] = []
    entries: list[EventEntry] = []
    departed: list[Any] = []
    recovery_seconds = 0
    hp_wake = 1

    def undo() -> None:
        """Undo every in-process aftermath surface; idempotent on re-run."""
        for restore in reversed(restores):
            restore()
        _restore_aftermath_surfaces(
            actor,
            battlefield,
            hp_before,
            trait_snapshot,
            buff_snapshot,
            knocked_out_before,
        )

    try:
        # Phase 1: the nonlethal floor (design D-C1). Unconditional on every
        # hostile defeat: a defeated or surrendered player is never persisted
        # at 0 HP, and the floor is the declared writer-owned write.
        actor.traits.hp.current = 1
        if battlefield is not None:
            battlefield.knocked_out.add(str(actor.key))
        if int(actor.pk) not in session.knocked_out_ids:
            session = replace(
                session,
                knocked_out_ids=(*session.knocked_out_ids, int(actor.pk)),
            )
        entries.append(
            EventEntry(
                kind="defeat_settle",
                actor=str(actor.key),
                target=None,
                data={
                    "wake": DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0],
                    "hp_after": 1,
                },
                text_template=defeat_aftermath_template("defeat_settle"),
            )
        )
        # Phase 2: the guarded violation hook point (design D-C4). No core
        # on-branch; the body is contributed by the adult changes and its
        # entries splice between defeat_settle and violator_depart.
        violation = _call_violation_hook(
            ViolationHookContext(
                actor=actor,
                session=session,
                battlefield=battlefield,
                entries=entries,
                restores=restores,
            )
        )
        # Phase 3: violator departure (design D-C3).
        entries.extend(
            _depart_violators(actor, session, battlefield, restores, departed)
        )
        # Phase 4: the weak debuff (design D-C2).
        _add_buff(actor, DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key)
        entries.append(
            EventEntry(
                kind="weak_granted",
                actor=str(actor.key),
                target=None,
                data={"buff": DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key},
                text_template=defeat_aftermath_template("weak_granted"),
            )
        )
        # Phase 5: the recovery advance (defeat-aftermath-recovery D-R1/D-R2).
        # One world-clock advance priced by the virtual scaled-rate solve,
        # then the player's wake value is pinned: clamped down to exactly the
        # target when the real un-scaled advance overshot, or written to the
        # capped virtual-model value when the target was unreachable. Both
        # writes are declared aftermath writes (design D-R2).
        gauge = actor.traits.hp
        target = math.ceil(float(gauge.max) * DEFEAT_AFTERMATH_RULEBOOK.recovery.wake_fraction)
        solve_current = _stored_trait_value(gauge)
        solve_carried = float(getattr(gauge, "regen_remainder", 0.0) or 0.0)
        solve_rate = float(getattr(gauge, "rate", 0) or 0)
        seconds, capped = solve_recovery_seconds(
            solve_current,
            solve_carried,
            solve_rate,
            DEFEAT_AFTERMATH_RULEBOOK.recovery.regen_scale,
            target,
            DEFEAT_AFTERMATH_RULEBOOK.recovery.max_recovery_seconds,
        )
        if seconds > 0:
            # Local import: the test suite patches world.rules.clock's
            # binding, so the clock lookup must resolve at call time.
            from world.rules.clock import get_world_clock

            clock = get_world_clock()
            scope = _recovery_scope(actor, battlefield)
            registry = build_advance_snapshot_registry(
                clock, seconds, AdvanceSource.DEFEAT_AFTERMATH, scope
            )
            tick_snapshot = _snapshot_clock_tick(clock)
            clock.advance(seconds, AdvanceSource.DEFEAT_AFTERMATH, scope)
            def _restore_recovery(
                clock=clock, registry=registry, tick=tick_snapshot, scope=tuple(scope)
            ):
                _restore_clock_tick(clock, tick)
                _restore_advance_registry(registry, scope)
            restores.append(
                _restore_recovery
            )
            wake = _stored_trait_value(gauge)
            if not capped and wake > target:
                gauge.current = target
            elif capped:
                # Settle the stored gauge at the virtual capped state:
                # current AND carried remainder, mirroring
                # ``_settle_gauge_regen``'s storage (final duck finding 1) —
                # keeping the real un-scaled remainder would let a later
                # advance regenerate earlier than the capped model permits.
                continuous = (
                    solve_current
                    + solve_carried
                    + solve_rate * DEFEAT_AFTERMATH_RULEBOOK.recovery.regen_scale * seconds
                )
                maximum = float(gauge.max)
                if continuous >= maximum:
                    gauge.current = round(maximum)
                    gauge.regen_remainder = 0.0
                else:
                    whole = math.floor(continuous)
                    gauge.current = whole
                    gauge.regen_remainder = continuous - whole
            wake = _stored_trait_value(gauge)
            recovery_seconds = seconds
            hp_wake = int(wake)
            entries.append(
                EventEntry(
                    kind="recovery_advance",
                    actor=str(actor.key),
                    target=None,
                    data={"seconds": seconds, "hp_wake": int(wake)},
                    text_template=defeat_aftermath_template("recovery_advance"),
                )
            )
            if capped:
                # observability: ignore R3: the cap hit is a designed bounded outcome (D-R3), not a failure; no exception object exists to chain
                log_error(
                    "defeat_aftermath_recovery_capped",
                    context={
                        "char": str(actor.key),
                        "tick": clock.tick,
                        "target": target,
                        "capped": True,
                    },
                )
        else:
            hp_wake = int(_stored_trait_value(gauge))
        # Phase 6: the digest (defeat-aftermath-digest-narrative D-D6). The
        # body wakes at its settled HP first; the digest then reads what it
        # remembers. Gated on the violation handoff: with no sequence there
        # is nothing to digest and no bystander observing a violation.
        digests: tuple[DigestOutcome, ...] = ()
        wake_observations: tuple[WakeObservation, ...] = ()
        if violation:
            digests, wake_observations = _run_digest_phase(
                actor, session, battlefield, entries, restores, violation
            )
    except Exception:
        undo()
        raise
    _schedule_boundary_event(actor, recovery_seconds, hp_wake)
    return DefeatAftermathResult(
        session=session,
        logs=(
            EventLog(
                actor=str(actor.key),
                skill_key="defeat_aftermath",
                targets=(),
                entries=tuple(entries),
                time_cost_seconds=0,
            ),
        ),
        undo=undo,
        departed=tuple(departed),
        violation=violation,
        digests=digests,
        wake_observations=wake_observations,
    )


def _living_foes(actor: Any, session: Any, battlefield: Any | None) -> list[Any]:
    """Return the living, non-fled foe-team members of the settled session.

    The battlefield roster is preferred; the degraded recovery path (no
    reconstructible battlefield) resolves the durable record's enemy dbrefs
    instead, discarding missing, fled, or dead objects, so a recovered defeat
    still departs its resolvable population winner (review D4).
    """
    if battlefield is not None:
        player_team = battlefield.team_of(str(actor.key))
        foe_team = next(
            team for team in battlefield.teams if team != player_team
        )
        return [
            entity
            for key in battlefield.teams[foe_team]
            if key in battlefield.roster
            and key not in battlefield.fled
            and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
            for entity in (battlefield.roster[key],)
        ]
    from evennia.objects.models import ObjectDB

    foes: list[Any] = []
    for enemy_id in session.enemy_ids:
        if enemy_id in session.fled_ids:
            continue
        entity = ObjectDB.objects.filter(id=enemy_id).first()
        if entity is None or _stored_trait_value(entity.traits.hp) <= 0:
            continue
        foes.append(entity)
    return foes


def _depart_violators(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    restores: list[Callable[[], None]],
    departed: list[Any],
) -> list[EventEntry]:
    """Depart every living winning violator (design D-C3).

    Quest-bound monsters (pk in the settling player's persisted quest
    records' ``objective_target_ids``) are never removed: quest retention
    outranks the population marker, and removing an extermination target
    would be disguised record loss. Marker-carrying population monsters
    departure through the population service's public primitive; foreign
    monsters stay untouched. One ``violator_depart`` entry is recorded per
    departure; the physical deletion of the departed runs post-commit via
    :func:`finalize_departure`.
    """
    from world.quests.runtime import read_records

    quest_bound = {
        target_id
        for record in read_records(actor)
        for target_id in record.objective_target_ids
    }
    entries: list[EventEntry] = []
    for violator in _living_foes(actor, session, battlefield):
        if int(violator.pk) in quest_bound:
            continue
        if not violator.db.population_key:
            continue
        from world.maps.wilderness_population import depart_population_monster

        wilderness = getattr(
            getattr(violator, "location", None), "wilderness", None
        )
        if wilderness is None:
            log_warn(
                "defeat_aftermath_despawn_without_wilderness",
                context={"monster": str(violator), "char": str(actor.key)},
            )
            continue
        ticket = depart_population_monster(wilderness, violator)
        restores.append(ticket.revert)
        departed.append(ticket)
        entries.append(
            EventEntry(
                kind="violator_depart",
                actor=str(violator.key),
                target=str(actor.key),
                data={"mode": "population"},
                text_template=defeat_aftermath_template("violator_depart"),
            )
        )
    return entries


def finalize_departure(actor: Any, tickets: tuple[Any, ...]) -> None:
    """Delete the departed violators after the OUTERMOST transaction committed.

    Scheduled through ``transaction.on_commit`` from inside the settlement
    transaction, so the physical deletion runs only after the durable commit
    and a rolled-back outer round discards it. Best effort with deterministic
    recovery: a failed delete reverts the logical departure (marker and
    bookkeeping restored, the monster stays a normal reconcilable population
    monster) and logs at error level; only a process crash in the post-commit
    window leaves a marker-less live monster — the accepted restart-refresh
    risk the parent design already carries.
    """
    for ticket in tickets:
        try:
            ticket.monster.delete()
        except Exception as error:
            try:
                ticket.revert()
            except Exception as revert_error:
                log_error(
                    "defeat_aftermath_depart_revert_failed",
                    exc=revert_error,
                    context={
                        "char": str(actor.key),
                        "monster": str(ticket.monster),
                    },
                )
            log_error(
                "defeat_aftermath_depart_delete_failed",
                exc=error,
                context={"char": str(actor.key), "monster": str(ticket.monster)},
            )


def _restore_aftermath_surfaces(
    actor: Any,
    battlefield: Any | None,
    hp_before: float,
    trait_snapshot: tuple[bool, Any],
    buff_snapshot: tuple[bool, Any],
    knocked_out_before: bool,
) -> None:
    """Undo every in-process surface the writer touched after a rollback.

    The database rows restore through the transaction; the idmapper cache is
    not transaction-aware, so each surface is put back explicitly before the
    exception propagates (design D-C5).
    """
    _restore_attribute(actor, "buffs", buff_snapshot)
    _restore_attribute(actor, "traits", trait_snapshot, category="traits")
    # The trait handler caches its data dict; rebind it to the restored
    # attribute and drop the per-trait cache (same reset as _restore_entity_state).
    actor.traits.trait_data = actor.attributes.get(
        "traits", default={}, category="traits"
    )
    actor.traits._cache.clear()
    if battlefield is not None and not knocked_out_before:
        battlefield.knocked_out.discard(str(actor.key))


def _schedule_boundary_event(actor: Any, seconds: int, hp_wake: int) -> None:
    """Schedule the ``defeat_aftermath`` boundary info event (design D-C6).

    Fires only on the outermost durable commit, like ``settlement_done``; the
    context is snapshotted as primitives so the callback carries no live
    objects. The recovery phase widens the context with ``seconds`` and
    ``hp_wake`` (defeat-aftermath-recovery D-R5).
    """
    from django.db import transaction

    from world.rules.clock import get_world_clock

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": get_world_clock().tick,
        "hp_after": _stored_trait_value(actor.traits.hp),
        "seconds": seconds,
        "hp_wake": hp_wake,
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info("defeat_aftermath", context=boundary)
    )


# The DA4 violation sequence is the shipped body of the core's guarded hook:
# registration happens at import, so the wiring needs no startup step and is
# exercised by every defeat settlement, while the single-registration guard
# still fails loudly on any second adult body. ``DEFEAT_ADULT_SCENES`` stays
# the only switch — with it off the hook is never called and this
# registration is structurally invisible (DA4 D-V6).
register_violation_hook(run_violation_sequence)
