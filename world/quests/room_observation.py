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
    fulfill_record_for,
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


def resolve_room_anchor(room: Any) -> str | None:
    """Resolve a room to a registered ANCHOR_REGISTRY key, or None.

    Reuses the REACH anchor resolution attribute (anchor_key).
    """
    if room is None:
        return None
    anchor_key = getattr(room, "anchor_key", None)
    if anchor_key is None and hasattr(room, "db"):
        anchor_key = getattr(room.db, "anchor_key", None)
    if isinstance(anchor_key, str) and anchor_key:
        from world.lore.anchors import ANCHOR_REGISTRY

        if anchor_key in ANCHOR_REGISTRY:
            return anchor_key
    return None


def resolve_room_region(
    room: Any, coordinates: tuple[int, int] | None = None
) -> str | None:
    """Resolve a room or coordinates to a registered WILDERNESS_REGION_REGISTRY key, or None."""
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY

    if room is not None:
        region_key = getattr(room, "region_key", None)
        if region_key is None and hasattr(room, "db"):
            region_key = getattr(room.db, "region_key", None)
        if isinstance(region_key, str) and region_key in WILDERNESS_REGION_REGISTRY:
            return region_key

    coords = coordinates
    if coords is None and room is not None:
        coords = getattr(room, "coordinates", None)

    if coords is not None and isinstance(coords, (tuple, list)) and len(coords) == 2:
        try:
            x, y = coords
            if isinstance(x, int) and isinstance(y, int) and not isinstance(x, bool) and not isinstance(y, bool):
                from world.maps.wilderness_provider import (
                    WILDERNESS_MAX_X,
                    WILDERNESS_MAX_Y,
                    region_for_coordinates,
                )

                if 0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y:
                    reg_key = region_for_coordinates(x, y)
                    if reg_key in WILDERNESS_REGION_REGISTRY:
                        return reg_key
        except Exception:  # observability: ignore R2: invalid coordinates or non-wilderness room is treated as non-resolving
            pass
    return None


def observe_arrival_lore(
    character: Any,
    room: Any = None,
    *,
    wilderness_coordinates: tuple[int, int] | None = None,
) -> None:
    """Observe character arrival at a room/coordinate and schedule lore reveals.

    Called from multiple movement hooks (``observe_room_entry``,
    ``after_successful_movement``, and ``PlayerCharacter.at_post_move``) whose
    ordering is not guaranteed. Deduplication relies solely on the idempotent
    ``record_lore_reveal`` writer: scheduling the same ``on_commit`` callback
    twice is harmless because the second reveal finds the entry already present
    and returns without writing. No ``ndb`` marker is used because setting it
    before ``transaction.on_commit`` means a rollback discards the callback but
    leaves the marker, silently suppressing the reveal on the next attempt.

    Best-effort: any unexpected exception during resolution or scheduling is
    logged through the facade and never bubbles into movement.
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(character, PlayerCharacter):
        return
    target_room = room if room is not None else getattr(character, "location", None)
    try:
        anchor_key = resolve_room_anchor(target_room)
        region_key = resolve_room_region(target_room, wilderness_coordinates)

        from world.rules.lore_knowledge import schedule_lore_reveal_best_effort

        if anchor_key:
            schedule_lore_reveal_best_effort(character, "anchor", anchor_key)
        if region_key:
            schedule_lore_reveal_best_effort(character, "region", region_key)
    except Exception as exc:
        from world.observability import log_warn

        log_warn(
            "lore_reveal_failed",
            exc=exc,
            context={
                "char": str(getattr(character, "key", character)),
                "category": "arrival",
                "key": str(getattr(target_room, "key", target_room)),
            },
        )


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


def _advance_arrival(
    player: Any, record: QuestRecord, definition: QuestDefinition
) -> QuestRecord:
    """Advance one REACH / ESCORT stage by exactly one arrival event.

    Progress is incremented by one and capped at the objective quantity: a
    single matching arrival can never jump to full completion, so even a
    non-1 quantity (should one slip through) accumulates instead of
    over-filling. Reaching the quantity fulfills the stage exactly as before
    (advancing to the next stage or completing the quest), so the shipped
    quantity-1 behavior is unchanged. A completion is dispatched to the
    quest-completion observers (change G nomination seam).
    """
    objective = definition.stages[record.stage_index].objective
    next_progress = record.stage_progress + 1
    if next_progress < objective.quantity:
        return replace(record, stage_progress=next_progress)
    return fulfill_record_for(player, record, definition)


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
    observe_arrival_lore(obj, room)
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
        advanced = _advance_arrival(obj, record, definition)
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