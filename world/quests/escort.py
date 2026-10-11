"""Pure exact-identity escort completion predicates (escort design §6).

An ESCORT objective declares exactly one closed completion discriminator; this
module owns the two predicates that decide whether a stage is physically
satisfied, and nothing else. It writes no state, reads no world clock, spawns
nothing, and teleports nothing: every input is an already-published exact
identity (the record's retained ``protected_roles`` bindings and the caller's
resolution of the definition's meeting roles through the upstream published
role lookup), so a predicate can never adopt a nearby actor, clone one, or
substitute a same-name impostor.

Position identity is authoritative, never display identity:

* an ordinary, grid, anchor, or bound-instance actor is at its room's primary
  key — the room *is* the position;
* a wilderness actor is at its terrain room's live ``(x, y)`` for that
  wilderness provider, because the installed wilderness contrib pools and
  recycles room objects across coordinates — two actors whose ``location`` is
  the same recycled object at different coordinates are therefore explicitly
  *not* co-located.

Permanent locator resolution stays separate from the instance-only pin: an
``ANCHOR``/``GRID`` destination is matched through the room's own identity
attribute, while a ``BOUND_INSTANCE`` destination matches the accepted record's
``stage_room_id`` and never pretends a permanent room is a bound instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from evennia.objects.models import ObjectDB

from typeclasses.entities import LivingEntity

from .definitions import (
    DestinationKind,
    EscortCompletion,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    RoomLocator,
)


class EscortPredicateError(ValueError):
    """An escort predicate was asked about a definition it cannot evaluate."""


@dataclass(frozen=True)
class PositionKey:
    """The authoritative position identity of one actor.

    ``kind`` is ``"room"`` (an ordinary, grid, anchor, or bound-instance room
    identified by primary key) or ``"wilderness"`` (a terrain position
    identified by the wilderness provider name plus live coordinates), so a
    recycled wilderness room object can never prove co-location at a different
    coordinate.
    """

    kind: str
    room_id: int | None = None
    wilderness: str | None = None
    x: int | None = None
    y: int | None = None


def authoritative_position(entity: Any) -> PositionKey | None:
    """Return one actor's authoritative position key, or ``None``.

    An actor with no location, or a location whose wilderness coordinates are
    unavailable, has no provable position and therefore never satisfies a
    predicate. Read-only and never raises.
    """
    room = getattr(entity, "location", None)
    if room is None:
        return None
    wilderness_script = getattr(room, "wilderness", None)
    if wilderness_script is not None:
        # The actor's own registered coordinate is authoritative while it is in
        # the wilderness, because the contrib pools and recycles room objects:
        # two actors whose ``location`` is the same recycled object at different
        # registered coordinates are NOT co-located. The room's live coordinate
        # is the fallback for an actor the script has not registered.
        coordinates = _actor_wilderness_coordinates(entity, wilderness_script)
        if coordinates is None:
            coordinates = _wilderness_coordinates(room, wilderness_script)
        if coordinates is None:
            return None
        name = getattr(wilderness_script, "name", None)
        if not isinstance(name, str) or not name:
            return None
        return PositionKey(
            kind="wilderness", wilderness=name, x=coordinates[0], y=coordinates[1]
        )
    room_id = getattr(room, "pk", None)
    if not isinstance(room_id, int) or isinstance(room_id, bool):
        return None
    return PositionKey(kind="room", room_id=room_id)


def _actor_wilderness_coordinates(
    entity: Any, wilderness_script: Any
) -> tuple[int, int] | None:
    """The actor's own registered wilderness coordinates, or ``None``."""
    from collections.abc import Mapping

    itemcoordinates = getattr(wilderness_script, "itemcoordinates", None)
    if not isinstance(itemcoordinates, Mapping):
        return None
    value = itemcoordinates.get(entity)
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and _is_coordinate(value[0])
        and _is_coordinate(value[1])
    ):
        return int(value[0]), int(value[1])
    return None


def _wilderness_coordinates(room: Any, wilderness_script: Any) -> tuple[int, int] | None:
    """The room's live wilderness coordinates, or ``None`` when unavailable."""
    coordinates = getattr(room, "coordinates", None)
    if isinstance(coordinates, (tuple, list)) and len(coordinates) == 2:
        x, y = coordinates
        if _is_coordinate(x) and _is_coordinate(y):
            return int(x), int(y)
    rooms = getattr(getattr(wilderness_script, "db", None), "rooms", None)
    if isinstance(rooms, dict):
        for candidate, value in rooms.items():
            if candidate is not None and getattr(candidate, "pk", None) == getattr(
                room, "pk", None
            ):
                if (
                    isinstance(value, (tuple, list))
                    and len(value) == 2
                    and _is_coordinate(value[0])
                    and _is_coordinate(value[1])
                ):
                    return int(value[0]), int(value[1])
    return None


def _is_coordinate(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_living(entity: Any) -> bool:
    """Whether one actor is a living entity above the nonlethal floor."""
    from world.rules.action import _stored_trait_value

    if not isinstance(entity, LivingEntity):
        return False
    try:
        return _stored_trait_value(entity.traits.hp) > 0
    except (AttributeError, KeyError, TypeError):
        return False


def escort_objective(definition: QuestDefinition, stage_index: int) -> QuestObjective:
    """Return the ESCORT objective of one stage, or raise for a non-escort stage."""
    if not (0 <= stage_index < len(definition.stages)):
        raise EscortPredicateError(
            f"definition {definition.key!r} has no stage {stage_index}"
        )
    objective = definition.stages[stage_index].objective
    if objective.kind is not ObjectiveKind.ESCORT:
        raise EscortPredicateError(
            f"definition {definition.key!r} stage {stage_index} is not an ESCORT "
            "objective"
        )
    return objective


def resolve_protected_actors(record: Any) -> tuple[tuple[str, Any], ...]:
    """Resolve the record's retained protected role bindings to live objects.

    The exact pairs the record retained at acceptance, in declaration order; a
    deleted actor is absent from the result, so the caller observes a missing
    role instead of a substituted one. Never spawns, adopts, or repairs.
    """
    resolved: list[tuple[str, Any]] = []
    for pair in getattr(record, "protected_roles", ()) or ():
        role_id, actor_id = pair
        actor = ObjectDB.objects.filter(id=int(actor_id)).first()
        if actor is not None:
            resolved.append((str(role_id), actor))
    return tuple(resolved)


def locator_matches(
    room: Any,
    locator: RoomLocator | None,
    stage_room_id: int | None,
) -> bool:
    """Whether ``room`` is the destination one validated locator names.

    ``ANCHOR`` and ``GRID`` match the room's own permanent identity attribute;
    ``BOUND_INSTANCE`` matches the accepted record's instance pin. A permanent
    room therefore never matches a bound-instance locator and vice versa.
    """
    if room is None or locator is None:
        return False
    if locator.kind is DestinationKind.ANCHOR:
        return getattr(room, "anchor_key", None) == locator.anchor_key
    if locator.kind is DestinationKind.GRID:
        return getattr(room, "xyz", None) == locator.xyz
    if locator.kind is DestinationKind.BOUND_INSTANCE:
        return stage_room_id is not None and int(getattr(room, "pk", -1)) == int(
            stage_room_id
        )
    return False


def destination_satisfied(
    record: Any,
    definition: QuestDefinition,
    room: Any,
) -> bool:
    """Whether every exact protected identity is alive at its validated locator.

    All-or-nothing: at least one protected binding is required, every retained
    actor must still exist, be living, and be at the locator room. An actor that
    is absent, dead, or elsewhere — and any same-name impostor — leaves the
    stage unsatisfied.
    """
    objective = escort_objective(definition, record.stage_index)
    if objective.completion is not EscortCompletion.DESTINATION:
        raise EscortPredicateError(
            f"definition {definition.key!r} stage {record.stage_index} is not a "
            "destination escort"
        )
    if not locator_matches(room, objective.destination, record.stage_room_id):
        return False
    protected = resolve_protected_actors(record)
    if len(protected) != len(objective.protected_role_refs):
        return False
    return all(
        is_living(actor) and getattr(actor, "location", None) is room
        for _, actor in protected
    )


def rendezvous_satisfied(
    record: Any,
    definition: QuestDefinition,
    meeting_actors: Iterable[Any],
) -> bool:
    """Whether the exact protected and meeting identities meet, live, together.

    ``meeting_actors`` are the exact live actors the caller resolved for the
    definition's declared meeting roles through the upstream published role
    lookup — never a proximity scan and never a clone. Every protected retained
    actor and every supplied meeting actor must be living at one shared
    authoritative position, and any declared typed relation must be satisfied by
    the two distinct endpoint actors. No destination and no original player body
    are required: possessing and moving a protected actor satisfies the same
    physical condition.
    """
    objective = escort_objective(definition, record.stage_index)
    if objective.completion is not EscortCompletion.RENDEZVOUS:
        raise EscortPredicateError(
            f"definition {definition.key!r} stage {record.stage_index} is not a "
            "rendezvous escort"
        )
    protected = resolve_protected_actors(record)
    if len(protected) != len(objective.protected_role_refs):
        return False
    meeting = tuple(meeting_actors)
    if len(meeting) != len(objective.meeting_role_refs):
        return False
    participants = (*protected, *((f"meeting:{position}", actor) for position, actor in enumerate(meeting)))
    if not participants:
        return False
    position = authoritative_position(participants[0][1])
    if position is None or not is_living(participants[0][1]):
        return False
    for _, actor in participants[1:]:
        if not is_living(actor) or authoritative_position(actor) != position:
            return False
    return _relation_satisfied(objective, protected, meeting)


def _relation_satisfied(
    objective: QuestObjective,
    protected: tuple[tuple[str, Any], ...],
    meeting: tuple[Any, ...],
) -> bool:
    """Whether the declared typed relation holds between its exact endpoint roles.

    The relation was validated against published roles at registration; at
    evaluation its two endpoints must be declared role references and must
    resolve to two *distinct* living actors among the participants, so a
    relation is never satisfied by one actor standing in for both roles.
    """
    relation = objective.relation
    if relation is None:
        return True
    kind, from_role, to_role = relation
    if kind is None or from_role == to_role:
        return False
    declared = set(objective.protected_role_refs) | set(objective.meeting_role_refs)
    if {from_role, to_role} - declared:
        return False
    actors: dict[str, Any] = {}
    for role_id, actor in protected:
        actors.setdefault(role_id, actor)
    # Meeting roles are declared as references; their exact actors arrive in
    # declaration order, so the caller's resolution order is the mapping.
    for position, role_id in enumerate(objective.meeting_role_refs):
        if position < len(meeting):
            actors.setdefault(role_id, meeting[position])
    if from_role not in actors or to_role not in actors:
        return False
    return actors[from_role] is not actors[to_role]


__all__ = [
    "EscortPredicateError",
    "PositionKey",
    "authoritative_position",
    "destination_satisfied",
    "escort_objective",
    "is_living",
    "locator_matches",
    "rendezvous_satisfied",
    "resolve_protected_actors",
]