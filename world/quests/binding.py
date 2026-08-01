"""Runtime instance and entity binding for an active quest stage (D-3).

Change 21 will call ``bind_stage_runtime()`` after SceneBuilder creates the
room and NPCs; this change only binds already-existing rooms. Binding is a
fully preflighted, atomic quest-log-plus-pin transition like every other
lifecycle operation.
"""

from dataclasses import replace
from typing import Any

from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity
from typeclasses.rooms import InstanceRoom

from .runtime import (
    QuestNotFound,
    QuestState,
    QuestTransitionError,
    definition_for,
    find_record,
    read_records,
)
from .transitions import (
    apply_quest_log_replacement,
    stage_pin_reason,
)


def _is_living(entity: Any) -> bool:
    from world.rules.action import _stored_trait_value

    try:
        return _stored_trait_value(entity.traits.hp) > 0
    except (AttributeError, KeyError, TypeError):
        return False


def _entity_dbrefs(entities: tuple[Any, ...], field: str) -> tuple[int, ...]:
    return tuple(int(entity.pk) for entity in entities)


def bind_stage_runtime(
    actor: Any,
    quest_id: str,
    *,
    room: Any = None,
    objective_targets: tuple[Any, ...] = (),
    protected_entities: tuple[Any, ...] = (),
) -> Any:
    """Bind one current active stage to an existing room and entity identities.

    Preflights every input before any mutation: the record must be active and
    its stage still current, a supplied room must be an ``InstanceRoom``, every
    supplied entity must be a live ``LivingEntity``, and objective targets and
    protected entities must be disjoint. Repeating an identical binding is
    idempotent; replacing any existing binding raises before anything changes.
    """
    current = read_records(actor)
    record = find_record(current, quest_id)
    if record is None:
        raise QuestNotFound(quest_id)
    if record.state is not QuestState.IN_PROGRESS:
        raise QuestTransitionError(
            f"quest {quest_id!r} is not active; only an active current stage can be bound"
        )
    definition = definition_for(record)
    current_stage = definition.stages[record.stage_index]
    if current_stage.index != record.stage_index:
        raise QuestTransitionError(
            f"quest {quest_id!r} stage {record.stage_index} no longer matches its definition"
        )

    room_id = None
    if room is not None:
        if not isinstance(room, InstanceRoom):
            raise QuestTransitionError(
                "bind_stage_runtime requires an InstanceRoom, "
                f"got {type(room).__name__}"
            )
        room_id = int(room.pk)

    objective_targets = tuple(objective_targets)
    protected_entities = tuple(protected_entities)
    for entity in (*objective_targets, *protected_entities):
        if not isinstance(entity, LivingEntity):
            raise QuestTransitionError(
                "bound targets must be LivingEntity instances, "
                f"got {type(entity).__name__}"
            )
        if not _is_living(entity):
            raise QuestTransitionError(
                f"bound target {entity.key!r} is not alive"
            )

    objective_ids = _entity_dbrefs(objective_targets, "objective_targets")
    protected_ids = _entity_dbrefs(protected_entities, "protected_entities")
    overlap = set(objective_ids) & set(protected_ids)
    if overlap:
        raise QuestTransitionError(
            f"entity dbrefs {sorted(overlap)} appear in both objective targets "
            "and protected entities"
        )

    identical = (
        room_id == record.stage_room_id
        and set(objective_ids) == set(record.objective_target_ids)
        and set(protected_ids) == set(record.protected_entity_ids)
    )
    if identical:
        return record
    already_bound = (
        record.stage_room_id is not None
        or bool(record.objective_target_ids)
        or bool(record.protected_entity_ids)
    )
    if already_bound:
        raise QuestTransitionError(
            f"quest {quest_id!r} is already bound; replacing a binding is not allowed"
        )

    new_record = replace(
        record,
        stage_room_id=room_id,
        objective_target_ids=objective_ids,
        protected_entity_ids=protected_ids,
    )
    pin_operations = ()
    if room is not None:
        reason = stage_pin_reason(actor.pk, quest_id, record.stage_index)
        pin_operations = ((room, (reason,), ()),)
    new_records = [new_record if candidate.quest_id == quest_id else candidate for candidate in current]
    apply_quest_log_replacement(actor, new_records, pin_operations)
    return new_record