"""Exact selected-provider resolution for NPC service flows.

Every browser service flow names the provider NPC it was opened from. This
module is the single admission seam that turns that identity into one exact
live, co-present, visible NPC and its service component, or a stable reason.
It never enumerates hosts, so a second provider standing in the same room can
never change the answer and no caller can fall back to a different provider.

Identity admission (used by the read path) checks the id form, the exploring
actor's room, the shared exploration visibility rule and the
capability/binding/schedule gates. Mutation admission adds the actor-level
authority the deterministic commands already enforce: no provider operation
while a combat session is active, and no guild or reception operation from a
possessed body (the merchant counters stay available to it). Reads never
authorize a write, and no client-supplied flag participates.
"""

from enum import StrEnum
from typing import Any

from typeclasses.components import GuildExamReception, GuildStaff, Merchant
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import (
    REASON_MALFORMED_BINDING,
    REASON_OFF_ANCHOR,
    service_available,
)

#: The largest integer a browser can address without losing precision.
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class ServiceTargetReason(StrEnum):
    """Stable rejection reasons of one selected provider."""

    #: No such object stands in the actor's room, or it is not visible to them.
    UNKNOWN_TARGET = "no_such_target"
    #: The selected NPC does not carry the capability the flow needs.
    WRONG_CAPABILITY = "wrong_capability"
    #: Co-located but the shared gate refused (remote/off-anchor/malformed).
    OFF_ANCHOR = REASON_OFF_ANCHOR
    MALFORMED_BINDING = REASON_MALFORMED_BINDING
    #: The provider's schedule blocks this interaction right now.
    SCHEDULE_BLOCKED = "schedule_blocked"
    #: An active combat session suppresses provider operations.
    ACTIVE_COMBAT = "active_combat"
    #: A possessed body may only use the merchant counters.
    POSSESSED = "possessed_service"


class ServiceTargetError(ValueError):
    """One selected provider is unusable; ``args[0]`` is the stable reason."""


#: Every capability a player service flow can target, in declaration order.
SERVICE_COMPONENT_CLASSES = (GuildStaff, GuildExamReception, Merchant)

#: The schedule interaction kind one component's provider answers.
_SCHEDULE_KINDS = {
    GuildStaff.name: "service_guild",
    GuildExamReception.name: "service_guild",
    Merchant.name: "service_shop",
}


def visible_room_entity(actor: Any, identity: Any) -> Any | None:
    """Return the actor's visible co-present object for ``identity``, or ``None``.

    Applies the shared exploration rules: the actor's own room contents, then
    Evennia's ``filter_visible`` view-permission filter — the same rule every
    exploration target selection uses. A bool, non-integer, non-positive or
    out-of-range identity never resolves.
    """
    if (
        isinstance(identity, bool)
        or not isinstance(identity, int)
        or not 1 <= identity <= MAX_SAFE_INTEGER
    ):
        return None
    location = getattr(actor, "location", None)
    if location is None:
        return None
    candidates = [obj for obj in location.contents if int(obj.pk) == identity]
    for obj in location.filter_visible(candidates, actor):
        return obj
    return None


def _service_component(npc: Any, component_class: type) -> Any | None:
    components = getattr(npc, "components", None)
    if components is None or not components.has(component_class.name):
        return None
    return components.get(component_class.get_component_slot())


def _admit(actor: Any, npc: Any, component_class: type) -> Any:
    """Return the npc's exact component or raise the stable refusal."""
    component = _service_component(npc, component_class)
    if component is None:
        raise ServiceTargetError(ServiceTargetReason.WRONG_CAPABILITY)
    verdict = service_available(actor, npc, component)
    if not verdict.allowed:
        raise ServiceTargetError(_verdict_reason(verdict.reason))
    if interaction_reason(npc, _SCHEDULE_KINDS[component_class.name]) is not None:
        raise ServiceTargetError(ServiceTargetReason.SCHEDULE_BLOCKED)
    return component


def _verdict_reason(reason: str | None) -> ServiceTargetReason:
    """Map one gate verdict onto the target vocabulary.

    A visible room occupant is co-located by construction, so the gate's
    ``remote`` verdict can only describe a provider that left between the
    resolution and the gate; it reads as an unknown target rather than a
    second, addressable state.
    """
    if reason == REASON_MALFORMED_BINDING:
        return ServiceTargetReason.MALFORMED_BINDING
    if reason == REASON_OFF_ANCHOR:
        return ServiceTargetReason.OFF_ANCHOR
    return ServiceTargetReason.UNKNOWN_TARGET


def require_service_target(
    actor: Any, npc_id: Any, component_class: type
) -> tuple[Any, Any]:
    """Return ``(npc, component)`` for the exact selected provider.

    Raises :class:`ServiceTargetError` for an unknown/invisible/departed id, a
    wrong capability, a refused binding, or a blocked schedule. Read-only.
    """
    npc = visible_room_entity(actor, npc_id)
    if npc is None:
        raise ServiceTargetError(ServiceTargetReason.UNKNOWN_TARGET)
    return npc, _admit(actor, npc, component_class)


def admitted_service_components(actor: Any, npc: Any) -> dict[type, Any]:
    """Return every capability on ``npc`` that this actor may use right now.

    One selected NPC can carry several capabilities with different outcomes:
    a functioning reception beside a merchant whose binding is broken. Each
    capability answers for itself through the same gate and schedule check a
    targeted flow applies, so an admitted capability never authorizes the
    presentation of another one.
    """
    admitted: dict[type, Any] = {}
    for component_class in SERVICE_COMPONENT_CLASSES:
        component = _service_component(npc, component_class)
        if component is None:
            continue
        if not service_available(actor, npc, component).allowed:
            continue
        if interaction_reason(npc, _SCHEDULE_KINDS[component_class.name]) is not None:
            continue
        admitted[component_class] = component
    return admitted


def require_service_provider(actor: Any, npc_id: Any) -> Any:
    """Return the exact selected NPC when it carries any supported surface.

    The read path's identity admission: it proves the selected NPC is real,
    visible, co-present and authorised for at least one service surface. The
    read model then admits each surface on its own, so a capability the actor
    may not use never ships its section.
    """
    npc = visible_room_entity(actor, npc_id)
    if npc is None:
        raise ServiceTargetError(ServiceTargetReason.UNKNOWN_TARGET)
    carried = [
        component_class
        for component_class in SERVICE_COMPONENT_CLASSES
        if _service_component(npc, component_class) is not None
    ]
    if not carried:
        raise ServiceTargetError(ServiceTargetReason.WRONG_CAPABILITY)
    if admitted_service_components(actor, npc):
        return npc
    reasons: list[ServiceTargetReason] = []
    for component_class in carried:
        component = _service_component(npc, component_class)
        verdict = service_available(actor, npc, component)
        if verdict.allowed:
            # The gate admits it; only the schedule refused.
            raise ServiceTargetError(ServiceTargetReason.SCHEDULE_BLOCKED)
        reasons.append(_verdict_reason(verdict.reason))
    raise ServiceTargetError(reasons[0])


def require_service_mutation(
    actor: Any, npc_id: Any, component_class: type
) -> tuple[Any, Any]:
    """Mutation admission: the exact provider plus the actor-level authority.

    On top of :func:`require_service_target`, a provider operation is refused
    while a combat session is active, and a possessed body may only reach the
    merchant counters. Both refusals read canonical state, never a payload.
    """
    from world.rules.combat_session import is_in_active_session
    from world.rules.possession import is_possessed_actor

    npc, component = require_service_target(actor, npc_id, component_class)
    if is_in_active_session(actor):
        raise ServiceTargetError(ServiceTargetReason.ACTIVE_COMBAT)
    if component_class is not Merchant and is_possessed_actor(actor):
        raise ServiceTargetError(ServiceTargetReason.POSSESSED)
    return npc, component


__all__ = [
    "MAX_SAFE_INTEGER",
    "SERVICE_COMPONENT_CLASSES",
    "ServiceTargetError",
    "ServiceTargetReason",
    "admitted_service_components",
    "require_service_mutation",
    "require_service_provider",
    "require_service_target",
    "visible_room_entity",
]
