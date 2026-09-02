"""Persisted deterministic quest records and lifecycle operations (D-2, D-6)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from world.observability import log_warn

from world.rules.clock import CLOCK_YAML, get_world_clock

from .definitions import QUEST_DEFINITION_REGISTRY, QuestDefinition
from .transitions import apply_quest_log_replacement, release_stage_binding


class QuestDataError(ValueError):
    """Persisted or supplied quest state violates the closed record contract."""


class QuestTransitionError(ValueError):
    """A lifecycle operation requested an invalid state transition."""


class QuestNotFound(KeyError):
    """A referenced quest ID or definition key is unknown."""


class QuestAlreadyActive(ValueError):
    """accept_quest called while an active record for the definition exists."""


class QuestState(StrEnum):
    """The three stored record states; unaccepted is represented by absence."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


_RECORD_FIELDS = frozenset(
    {
        "quest_id",
        "definition_key",
        "state",
        "stage_index",
        "stage_progress",
        "deadline_tick",
        "accepted_tick",
        "stage_room_id",
        "objective_target_ids",
        "protected_entity_ids",
        "failure_reason",
    }
)


@dataclass(frozen=True)
class QuestRecord:
    """One deterministic, JSON-safe quest record stored in ``db.quest_log``."""

    quest_id: str
    definition_key: str
    state: QuestState
    stage_index: int
    stage_progress: int
    deadline_tick: int | None
    accepted_tick: int
    stage_room_id: int | None
    objective_target_ids: tuple[int, ...]
    protected_entity_ids: tuple[int, ...]
    failure_reason: str | None


def to_storage(record: QuestRecord) -> dict[str, Any]:
    """Serialize one record into a JSON-safe storage dict with no live refs."""
    return {
        "quest_id": record.quest_id,
        "definition_key": record.definition_key,
        "state": record.state.value,
        "stage_index": record.stage_index,
        "stage_progress": record.stage_progress,
        "deadline_tick": record.deadline_tick,
        "accepted_tick": record.accepted_tick,
        "stage_room_id": record.stage_room_id,
        "objective_target_ids": list(record.objective_target_ids),
        "protected_entity_ids": list(record.protected_entity_ids),
        "failure_reason": record.failure_reason,
    }


def _require_int(data: dict[str, Any], key: str, *, nullable: bool = False) -> int | None:
    value = data.get(key)
    if nullable and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise QuestDataError(f"record field {key!r} must be an integer, got {value!r}")
    return value


def from_storage(data: dict[str, Any]) -> QuestRecord:
    """Strictly parse one storage dict, raising ``QuestDataError`` on any violation."""
    if not isinstance(data, dict):
        raise QuestDataError(f"quest-log entry must be a dict, got {type(data).__name__}")
    unknown = set(data) - _RECORD_FIELDS
    if unknown:
        raise QuestDataError(f"quest-log entry has unknown fields {sorted(unknown)}")
    missing = _RECORD_FIELDS - set(data)
    if missing:
        raise QuestDataError(f"quest-log entry is missing fields {sorted(missing)}")
    quest_id = data["quest_id"]
    definition_key = data["definition_key"]
    if not isinstance(quest_id, str) or not quest_id:
        raise QuestDataError("quest_id must be a non-empty string")
    if not isinstance(definition_key, str) or not definition_key:
        raise QuestDataError("definition_key must be a non-empty string")
    state_value = data["state"]
    if state_value not in {state.value for state in QuestState}:
        raise QuestDataError(f"unknown quest state {state_value!r}")
    state = QuestState(state_value)
    stage_index = _require_int(data, "stage_index")
    stage_progress = _require_int(data, "stage_progress")
    accepted_tick = _require_int(data, "accepted_tick")
    deadline_tick = _require_int(data, "deadline_tick", nullable=True)
    stage_room_id = _require_int(data, "stage_room_id", nullable=True)
    if stage_index < 0 or stage_progress < 0 or accepted_tick < 0:
        raise QuestDataError("stage_index, stage_progress, and accepted_tick must be non-negative")
    if deadline_tick is not None and deadline_tick < 0:
        raise QuestDataError("deadline_tick must be non-negative or None")
    failure_reason = data["failure_reason"]
    if failure_reason is not None and not isinstance(failure_reason, str):
        raise QuestDataError("failure_reason must be a string or None")
    objective_target_ids = _parse_id_list(data["objective_target_ids"], "objective_target_ids")
    protected_entity_ids = _parse_id_list(data["protected_entity_ids"], "protected_entity_ids")
    if set(objective_target_ids) & set(protected_entity_ids):
        raise QuestDataError(
            "persisted objective_target_ids and protected_entity_ids overlap; "
            "a bound target can never be a protected entity"
        )
    return QuestRecord(
        quest_id=quest_id,
        definition_key=definition_key,
        state=state,
        stage_index=stage_index,
        stage_progress=stage_progress,
        deadline_tick=deadline_tick,
        accepted_tick=accepted_tick,
        stage_room_id=stage_room_id,
        objective_target_ids=objective_target_ids,
        protected_entity_ids=protected_entity_ids,
        failure_reason=failure_reason,
    )


def _parse_id_list(values: Any, field: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise QuestDataError(f"record field {field!r} must be a list of integer dbrefs")
    items = list(values)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in items):
        raise QuestDataError(f"record field {field!r} must be a list of integer dbrefs")
    return tuple(items)


def read_records(actor: Any) -> list[QuestRecord]:
    """Parse and validate every quest-log entry before any transaction.

    Entries are copied to plain dicts first (Evennia serves stored dicts as
    ``_SaverDict`` wrappers), then each record is checked for duplicates and
    definition/state-machine consistency. Any violation raises
    ``QuestDataError`` so no lifecycle operation can write against corrupted
    data (D-2).
    """
    records = [
        from_storage(_coerce_entry(entry))
        for entry in (actor.db.quest_log or [])
    ]
    seen: set[str] = set()
    for record in records:
        if record.quest_id in seen:
            raise QuestDataError(
                f"duplicate quest id {record.quest_id!r} in quest log"
            )
        seen.add(record.quest_id)
        validate_record_runtime(record)
    return records


def _coerce_entry(entry: Any) -> dict[str, Any]:
    try:
        return dict(entry)
    except (TypeError, ValueError) as error:
        raise QuestDataError(
            f"quest-log entry is not a dict-like value: {error}"
        ) from error


def validate_record_runtime(record: QuestRecord) -> None:
    """Validate one record against the definition state machine.

    Every record must reference a known definition whose ``stage_index`` is in
    range and still matches its definition, with progress within the current
    objective's quantity. A terminal record must additionally be final (no
    runtime bindings) and, when failed, must carry a reason. Violations raise
    ``QuestDataError`` instead of silently reinterpreting the record.
    """
    definition = definition_for(record)
    if not (0 <= record.stage_index < len(definition.stages)):
        raise QuestDataError(
            f"quest {record.quest_id!r} stage index {record.stage_index} "
            f"is outside definition {record.definition_key!r}"
        )
    stage = definition.stages[record.stage_index]
    if stage.index != record.stage_index:
        raise QuestDataError(
            f"quest {record.quest_id!r} stage {record.stage_index} does not "
            "match its definition"
        )
    if record.state is not QuestState.IN_PROGRESS:
        if (
            record.stage_room_id is not None
            or record.objective_target_ids
            or record.protected_entity_ids
        ):
            raise QuestDataError(
                f"terminal quest {record.quest_id!r} still has runtime bindings"
            )
        if record.state is QuestState.FAILED and not record.failure_reason:
            raise QuestDataError(
                f"failed quest {record.quest_id!r} lacks a failure reason"
            )
        return
    objective = stage.objective
    if not (0 <= record.stage_progress <= objective.quantity):
        raise QuestDataError(
            f"quest {record.quest_id!r} progress {record.stage_progress} "
            f"exceeds objective quantity {objective.quantity}"
        )


def find_record(records: list[QuestRecord], quest_id: str) -> QuestRecord | None:
    return next((record for record in records if record.quest_id == quest_id), None)


def fail_record(record: QuestRecord, reason: str) -> QuestRecord:
    """Return a failed copy with bindings cleared and the reason recorded."""
    return replace(
        record,
        state=QuestState.FAILED,
        failure_reason=reason,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
    )


def fulfill_record(record: QuestRecord, definition: QuestDefinition) -> QuestRecord:
    """Return the record after its current stage is fully satisfied.

    Advances to the next contiguous stage (resetting progress and clearing
    bindings), or marks the quest COMPLETED on its final stage with progress
    capped at the objective quantity.
    """
    stage_index = record.stage_index
    if stage_index + 1 < len(definition.stages):
        return replace(
            record,
            stage_index=stage_index + 1,
            stage_progress=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
        )
    objective = definition.stages[stage_index].objective
    return replace(
        record,
        state=QuestState.COMPLETED,
        stage_progress=objective.quantity,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
    )


# ---------------------------------------------------------------------------
# Completion observers (title-system change G trigger seam).
# ---------------------------------------------------------------------------
# The three quest-log writers (DEFEAT planner, acquisition observer, room
# observation) all converge on ``fulfill_record``; ``fulfill_record_for`` is
# the entity-aware wrapper that fires the registered observers exactly when a
# transition lands on COMPLETED. Observers are scheduling seams only: they
# must defer side effects through ``transaction.on_commit`` and an exception
# they raise is isolated and logged — a broken observer can never change
# quest settlement (the deterministic game stays fully playable offline).

_QUEST_COMPLETION_OBSERVERS: list[Callable[[Any, QuestRecord, QuestDefinition], None]] = []


def register_quest_completion_observer(
    observer: Callable[[Any, QuestRecord, QuestDefinition], None],
) -> None:
    """Idempotently install one quest-completion observer."""
    if observer not in _QUEST_COMPLETION_OBSERVERS:
        _QUEST_COMPLETION_OBSERVERS.append(observer)


def _notify_quest_completion(
    entity: Any, record: QuestRecord, definition: QuestDefinition
) -> None:
    for observer in tuple(_QUEST_COMPLETION_OBSERVERS):
        try:
            observer(entity, record, definition)
        except Exception as error:  # noqa: BLE001 - isolation is the contract
            log_warn(
                "quest_observer_failed",
                context={
                    "char": str(getattr(entity, "pk", None)),
                    "observer": type(observer).__qualname__,
                },
                exc=error,
            )


def fulfill_record_for(
    entity: Any, record: QuestRecord, definition: QuestDefinition
) -> QuestRecord:
    """``fulfill_record`` plus the COMPLETED-transition observer dispatch."""
    result = fulfill_record(record, definition)
    if result.state is QuestState.COMPLETED:
        _notify_quest_completion(entity, result, definition)
    return result


def definition_for(record: QuestRecord) -> QuestDefinition:
    """Return the referenced definition or raise for a missing active record."""
    definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
    if definition is None:
        raise QuestDataError(
            f"quest {record.quest_id!r} references missing definition "
            f"{record.definition_key!r}"
        )
    return definition


def _current_tick() -> int:
    """The persisted world tick at the moment an operation runs."""
    return get_world_clock().tick


def accept_quest(actor: Any, definition_key: str) -> QuestRecord:
    """Create one deterministic stage-zero active record for ``definition_key``."""
    definition = QUEST_DEFINITION_REGISTRY.get(definition_key)
    if definition is None:
        raise QuestNotFound(f"unknown definition {definition_key!r}")
    current = read_records(actor)
    if any(
        record.definition_key == definition_key
        and record.state is QuestState.IN_PROGRESS
        for record in current
    ):
        raise QuestAlreadyActive(definition_key)
    acceptance_number = (
        sum(1 for record in current if record.definition_key == definition_key) + 1
    )
    quest_id = f"{definition_key}:{acceptance_number}"
    accepted_tick = _current_tick()
    deadline_tick = (
        None
        if definition.deadline_hours is None
        else accepted_tick + definition.deadline_hours * CLOCK_YAML["seconds_per_hour"]
    )
    record = QuestRecord(
        quest_id=quest_id,
        definition_key=definition_key,
        state=QuestState.IN_PROGRESS,
        stage_index=0,
        stage_progress=0,
        deadline_tick=deadline_tick,
        accepted_tick=accepted_tick,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason=None,
    )
    apply_quest_log_replacement(actor, [*current, record])
    return record


def abandon_quest(actor: Any, quest_id: str) -> QuestRecord:
    """Fail an active record with reason ``abandoned`` and release its binding."""
    current = read_records(actor)
    record = find_record(current, quest_id)
    if record is None:
        raise QuestNotFound(quest_id)
    if record.state is not QuestState.IN_PROGRESS:
        return record
    failed = replace(
        record,
        state=QuestState.FAILED,
        failure_reason="abandoned",
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
    )
    pin_operations = release_stage_binding(actor, record)
    new_records = [failed if candidate.quest_id == quest_id else candidate for candidate in current]
    apply_quest_log_replacement(actor, new_records, pin_operations)
    return failed