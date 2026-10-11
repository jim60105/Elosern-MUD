"""Retained named-role identity and its permanent retention destination.

A published named role outlives stage release and every terminal quest state
(design §7): its binding, persona, history and phase are never deleted by quest
teardown. An instance package declares a validated permanent retention locator
for each role, and the maps-owned reclamation transfers any such actor still
inside a due instance to that locator *before* destructively cleaning the room.

This module owns the retention declaration read and the transfer itself; the
maps reclamation calls :func:`transfer_retained_role` so the movement hooks and
the ownership removal stay in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn

from . import scene_store
from .definitions import DestinationKind
from .scene_package import validate_scene_package


class RetentionTransferError(RuntimeError):
    """A retained actor could not be transferred to its declared destination."""

    def __init__(self, message: str, *, destinations: tuple[Any, ...] = ()) -> None:
        super().__init__(message)
        #: The destination rooms already written by this reclaim pass, so the
        #: caller can reconcile their cached contents after a rollback.
        self.destinations = destinations


@dataclass(frozen=True)
class RetainedRole:
    """One retained package role bound to an exact live actor."""

    package_id: str
    role_id: str
    npc_id: int
    locator: Any


def retained_role_for(npc_id: int) -> RetainedRole | None:
    """Return the retention declaration naming one actor, or ``None``.

    Read-only: a bound role whose package declares a validated permanent
    retention locator is a retained named role. An unbound actor is not.
    """
    binding = scene_store.get_role_binding_for_npc(int(npc_id))
    if binding is None:
        return None
    row = scene_store.read_package(binding.package.package_id)
    if row is None:
        return None
    roles = row.payload.get("roles") or []
    entry = next(
        (
            role
            for role in roles
            if isinstance(role, dict) and role.get("role_id") == binding.role_id
        ),
        None,
    )
    if entry is None or not isinstance(entry.get("retention"), dict):
        return None
    definition = validate_scene_package(row.payload)
    role = definition.role(binding.role_id)
    if role is None:
        return None
    return RetainedRole(
        package_id=binding.package.package_id,
        role_id=binding.role_id,
        npc_id=binding.npc_id,
        locator=role.retention,
    )


def resolve_retention_room(locator: Any) -> Any | None:
    """Resolve one validated retention locator to its existing permanent room."""
    from typeclasses.rooms import AnchorRoom, GridRoom

    if locator.kind is DestinationKind.ANCHOR:
        for room in AnchorRoom.objects.all():
            if room.db.anchor_key == locator.anchor_key:
                return room
        return None
    if locator.kind is DestinationKind.GRID:
        return GridRoom.objects.filter_xyz(xyz=locator.xyz).first()
    return None


def validate_retention_destination(retained: RetainedRole) -> Any:
    """Return the retained actor's destination room, or raise a named error."""
    room = resolve_retention_room(retained.locator)
    if room is None:
        raise RetentionTransferError(
            f"retention destination for role {retained.role_id!r} of package "
            f"{retained.package_id!r} is not materialized"
        )
    return room


def transfer_retained_role(
    entity: Any,
    retained: RetainedRole,
    *,
    room: Any = None,
    source_room: Any = None,
    tick: int = 0,
) -> bool:
    """Move one retained actor to its declared destination and drop ownership.

    The actor keeps its identity, persona, phase, memories and actual living
    state: this never clones, resurrects, or resets it. An actor already outside
    the room is left exactly where it is. The ephemeral ownership entry that
    marked it for despawn is removed, so a later reclaim pass cannot delete a
    retained role. Raises :class:`RetentionTransferError` when the destination is
    unavailable or the movement hook refuses.
    """
    destination = room if room is not None else validate_retention_destination(retained)
    if room is not None and destination is None:
        raise RetentionTransferError(
            f"retention destination for role {retained.role_id!r} is unavailable"
        )
    if getattr(entity, "location", None) is None:
        return False
    if entity.location.pk == destination.pk:
        _drop_ownership(entity, source_room)
        return True
    moved = entity.move_to(destination, quiet=True)
    if moved is False:
        raise RetentionTransferError(
            f"retained actor {retained.npc_id} could not move to its retention "
            "destination"
        )
    _drop_ownership(entity, source_room)
    log_info(
        "retained_role_transferred",
        context={
            "package": retained.package_id,
            "role": retained.role_id,
            "npc": str(retained.npc_id),
            "room": str(getattr(destination, "pk", "")),
            "tick": str(tick),
        },
    )
    return True


def _drop_ownership(entity: Any, source_room: Any = None) -> None:
    """Remove one entity from the ephemeral ownership registry.

    The reclaim pass knows the source room, so the common path touches exactly
    that row; the full scan is only the fallback for a caller that does not.
    """
    for room in ([source_room] if source_room is not None else _rooms_owning(entity)):
        if room is None:
            continue
        owned = [entry for entry in (room.db.owned_entities or []) if entry and entry.pk]
        if any(entry.pk == entity.pk for entry in owned):
            remaining = [entry for entry in owned if entry.pk != entity.pk]
            room.db.owned_entities = remaining


def _rooms_owning(entity: Any) -> list[Any]:
    from typeclasses.rooms import InstanceRoom

    owners = []
    for room in InstanceRoom.objects.all():
        owned = room.db.owned_entities or []
        if any(entry is not None and getattr(entry, "pk", None) == entity.pk for entry in owned):
            owners.append(room)
    return owners


def unavailable_retention_reason(npc_id: int) -> str | None:
    """Return a named reason when one actor's retention cannot be honoured."""
    retained = retained_role_for(npc_id)
    if retained is None:
        return None
    try:
        validate_retention_destination(retained)
    except RetentionTransferError as error:
        log_warn(
            "retention_destination_unavailable",
            context={"package": retained.package_id, "role": retained.role_id, "npc": str(npc_id)},
            exc=error,
        )
        return "retention_destination_unavailable"
    return None


__all__ = [
    "RetainedRole",
    "RetentionTransferError",
    "resolve_retention_room",
    "retained_role_for",
    "transfer_retained_role",
    "unavailable_retention_reason",
    "validate_retention_destination",
]
