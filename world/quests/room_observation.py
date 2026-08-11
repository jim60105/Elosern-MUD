"""Room-driven quest progress through supported persistent room hooks (D-5).

``GridRoom`` and ``InstanceRoom`` adopt ``QuestObservableRoomMixin`` (and
``AnchorRoom`` inherits it through ``GridRoom``); ``TerrainRoom`` deliberately
does not, because the installed wilderness contrib assigns ``.location``
directly on its ordinary entry/step path and never routes through
``at_object_receive``.
"""

from dataclasses import replace
from typing import Any

from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity

from .definitions import DestinationKind, ObjectiveKind, QuestDefinition, RoomLocator
from .runtime import (
    QuestRecord,
    QuestState,
    definition_for,
    fulfill_record,
    read_records,
)
from .transitions import apply_quest_log_replacement, release_stage_binding


def _reach_matches(room: Any, destination: RoomLocator, stage_room_id: int | None) -> bool:
    if destination.kind is DestinationKind.ANCHOR:
        return getattr(room, "anchor_key", None) == destination.anchor_key
    if destination.kind is DestinationKind.GRID:
        return getattr(room, "xyz", None) == destination.xyz
    if destination.kind is DestinationKind.BOUND_INSTANCE:
        return stage_room_id is not None and int(room.pk) == stage_room_id
    return False


def _escort_ready(room: Any, protected_entity_ids: tuple[int, ...]) -> bool:
    """Require at least one protected entity, all alive and present in ``room``."""
    if not protected_entity_ids:
        return False
    for entity_id in protected_entity_ids:
        entity = ObjectDB.objects.filter(id=entity_id).first()
        if entity is None or not isinstance(entity, LivingEntity):
            return False
        if entity.location is not room:
            return False
        from world.rules.action import _stored_trait_value

        if _stored_trait_value(entity.traits.hp) <= 0:
            return False
    return True


def _companion_present(room: Any, player: Any) -> bool:
    """Whether at least one bound companion of ``player`` is in ``room``.

    Co-presence is a safe-party read (party-quest D-2): stale, corrupt, or
    mismatched entries are skipped by ``live_companions``, so a broken binding
    can never block or falsely advance an arrival.
    """
    from world.rules.party import live_companions

    for npc in live_companions(player):
        if npc.location is room:
            return True
    return False


def _advance_arrival(record: QuestRecord, definition: QuestDefinition) -> QuestRecord:
    """Advance one REACH / ESCORT stage by exactly one arrival event.

    Progress is incremented by one and capped at the objective quantity: a
    single matching arrival can never jump to full completion, so even a
    non-1 quantity (should one slip through) accumulates instead of
    over-filling. Reaching the quantity fulfills the stage exactly as before
    (advancing to the next stage or completing the quest), so the shipped
    quantity-1 behavior is unchanged.
    """
    objective = definition.stages[record.stage_index].objective
    next_progress = record.stage_progress + 1
    if next_progress < objective.quantity:
        return replace(record, stage_progress=next_progress)
    return fulfill_record(record, definition)


def observe_room_entry(room: Any, obj: Any) -> None:
    """Advance a player's active REACH / ESCORT stages satisfied by this room.

    Arrival advances only when the player is the arriving object and at least
    one bound companion is present in the destination room -- already there or
    arriving with the player (party-quest D-2); there is no companion-alone
    entry point. Each quest transitions at most once per hook call; terminal
    records and non-matching destinations are ignored.
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(obj, PlayerCharacter):
        return
    records = read_records(obj)
    if not any(
        record.state is QuestState.IN_PROGRESS
        for record in records
    ):
        return
    if not _companion_present(room, obj):
        return
    replacements: dict[str, Any] = {}
    pin_operations = []
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        definition = definition_for(record)
        objective = definition.stages[record.stage_index].objective
        if objective.kind is ObjectiveKind.REACH:
            satisfied = _reach_matches(room, objective.destination, record.stage_room_id)
        elif objective.kind is ObjectiveKind.ESCORT:
            satisfied = (
                _reach_matches(room, objective.destination, record.stage_room_id)
                and _escort_ready(room, record.protected_entity_ids)
            )
        else:
            continue
        if not satisfied:
            continue
        advanced = _advance_arrival(record, definition)
        replacements[record.quest_id] = advanced
        if (
            advanced.state is QuestState.IN_PROGRESS
            and advanced.stage_index == record.stage_index
        ):
            continue
        pin_operations.extend(release_stage_binding(obj, record))
    if not replacements:
        return
    new_records = [replacements.get(record.quest_id, record) for record in records]
    apply_quest_log_replacement(obj, new_records, pin_operations)


class QuestObservableRoomMixin:
    """Room mixin that observes ``PlayerCharacter`` arrival for quest progress."""

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(obj, source_location, move_type=move_type, **kwargs)
        from typeclasses.characters import PlayerCharacter

        if isinstance(obj, PlayerCharacter):
            observe_room_entry(self, obj)