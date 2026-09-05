"""The single read-only service-availability resolver (service-anchoring D3/D4).

Every service gate (shop trade, guild registration, examiner authority, and
every future profession surface) asks ONE question here: can this actor use
this host's service, given the component's authored ``person | place``
binding and, for ``place``, the persisted anchor room? The resolver answers
with a frozen :class:`ServiceVerdict` whose reason vocabulary is exactly
``remote | off_anchor | malformed_binding``.

Contract:

- READ-ONLY. The resolver writes no game state (its only side effect is a
  bounded, debounced warn event on malformed data).
- PER-COMPONENT semantics. Gates ask about the one component they serve; a
  caller holding several service components on one host asks once per
  component. Rules never mix components.
- FAIL CLOSED. Missing or unknown stored bindings, and ``place`` bindings
  whose anchor room cannot be resolved, refuse service
  (``malformed_binding``) — the resolver never defaults open, mirroring the
  equipment fail-closed normalization idiom.
- New professions with new service surfaces wire their gate in HERE; they do
  not re-decide location semantics at the call site.

Availability comes exclusively from persisted component fields
(``service_binding`` / ``anchor_room_id``, written by the shared profession
assembly). This module must never import ``profession_config`` — runtime
gates read components, never the blueprint table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.observability import log_warn

#: Not co-located with the host — today's remote-merchant semantics.
REASON_REMOTE = "remote"
#: Co-located, but a ``place``-bound host stands away from its anchor room.
REASON_OFF_ANCHOR = "off_anchor"
#: The stored binding is unknown, missing on a converged component, or a
#: ``place`` binding whose anchor room no longer resolves. Fails closed.
REASON_MALFORMED_BINDING = "malformed_binding"

#: Registry-owned fixed player-facing lines. Callers that need the same
#: refusal wording map their own reason codes onto these constants — the
#: prose belongs to the gate module, not to any single command surface.
MESSAGE_OFF_ANCHOR = "他的服務不在這裡營業。"


@dataclass(frozen=True)
class ServiceVerdict:
    """One availability answer: allowed plus a nullable stable reason code."""

    allowed: bool
    reason: str | None = None


_ALLOWED = ServiceVerdict(True)
_REMOTE = ServiceVerdict(False, REASON_REMOTE)
_OFF_ANCHOR = ServiceVerdict(False, REASON_OFF_ANCHOR)
_MALFORMED = ServiceVerdict(False, REASON_MALFORMED_BINDING)


def _warn_malformed(host: Any, component: Any) -> None:
    """Emit at most ONE malformed-binding warn per host per process (ndb flag).

    The debounce flag lives on ``host.ndb`` (design 2026-09-05-service-
    anchoring D3 — in-memory, never-persistent, keyed by object id): request
    flows refetch typeclass instances, so a plain Python attribute would
    re-arm per instance and spam the log. A repeatedly-queried corrupt
    component emits exactly one warn per process; a restart re-arms one
    reminder. The resolver's only write remains this bounded log flag.
    """
    ndb = host.ndb
    if getattr(ndb, "service_gate_malformed_warned", None):
        return
    ndb.service_gate_malformed_warned = True
    log_warn(
        "service_gate_malformed_binding",
        context={
            "char": getattr(host, "key", None),
            "component": type(component).__name__,
            "binding": getattr(component, "service_binding", None),
        },
    )


def service_available(actor: Any, host: Any, component: Any) -> ServiceVerdict:
    """Answer whether ``actor`` may use the service ``component`` on ``host``.

    Rule order (design 2026-09-05-service-anchoring §3):

    1. Co-location first — a host in another room is ``remote`` regardless
       of binding, preserving every existing gate's refusal lineage.
    2. ``person``-bound components serve anywhere the host stands beside the
       actor; ``place``-bound components additionally require the host to
       stand in their anchor room (else ``off_anchor``).
    3. Anything malformed in the stored data — an UNKNOWN binding value, or
       a ``place`` whose anchor room cannot resolve — is ``malformed_binding``
       and fails closed.

    An UNSET binding (``None``) reads as the design-D1 default co-presence:
    convergence writes an authored value on every component it touches, so an
    unset field is by construction a component the assembly never ran for —
    hand-built NPCs, never shipped service data. The delta carves exactly
    these out ("missing … on a converged component" is the malformed row;
    converged components structurally cannot lack the field). An UNKNOWN
    value (``"portable"``) is the fail-closed row.
    """
    if actor.location is None or host.location != actor.location:
        return _REMOTE
    binding = getattr(component, "service_binding", None)
    if binding is None or binding == "person":
        return _ALLOWED
    if binding != "place":
        _warn_malformed(host, component)
        return _MALFORMED
    anchor_room_id = getattr(component, "anchor_room_id", None)
    if isinstance(anchor_room_id, bool) or not isinstance(anchor_room_id, int):
        _warn_malformed(host, component)
        return _MALFORMED
    # The anchor lives whenever a ROOM row with that id exists (Evennia
    # deletes the location reference with the room, so no dangling-location
    # state can masquerade as at-anchor). The query converts each row to its
    # stored typeclass, so the isinstance gate rejects a stored id that
    # points at a non-room object (import-time resolution pins rooms; this
    # is the corruption defense in depth). A plain Room.objects filter would
    # pin to one typeclass path and blind subclass rooms — same constraint
    # world/maps/bootstrap.py documents.
    from evennia.objects.models import ObjectDB
    from typeclasses.rooms import Room

    anchor_row = next(iter(ObjectDB.objects.filter(pk=anchor_room_id)), None)
    if anchor_row is None or not isinstance(anchor_row, Room):
        _warn_malformed(host, component)
        return _MALFORMED
    anchor_pk = getattr(host.location, "pk", None)
    if anchor_pk != anchor_room_id:
        return _OFF_ANCHOR
    return _ALLOWED


def off_anchor_place_service(npc: Any) -> str | None:
    """Name the npc's place-bound service component that strands it, if any.

    Returns the component class name of the first ``place``-bound service
    component whose resolved anchor room does NOT cover the npc's current
    location — or ``None`` when no such component exists. Exact legs, in
    cost order:

    1. a BOUND party companion (design 2026-09-05-service-anchoring D6):
       the cheap raw ``npc.db.party_member`` mirror read gates the leg, and
       the party module's authoritative ``bound_owner_of`` verifies it — a
       stale, non-reciprocated, or dead-owner back-reference is NOT a
       binding, so a corrupt leftover can never silence an NPC that no
       longer travels with anyone. One membership interpretation, owned by
       the party module (the same safe read ``typeclasses/npcs.py`` uses).
    2. the npc carries at least one component with persisted
       ``service_binding == "place"`` — component classes are imported
       function-locally from ``typeclasses.components`` (this module never
       imports ``profession_config``; it reads components, never the table).
    3. the component's anchor does not cover the npc's current room. An
       UNRESOLVABLE anchor (corrupt id, deleted or non-room row) counts as
       off-anchor here: unlike the interaction resolver this predicate
       guards a POLICY (skip settlement), where failing closed silences a
       schedule rather than letting it teleport a companion away from the
       party. A ``None`` location likewise reads as off-anchor — the
       predicate is total and never raises.

    Multiple place-bound components with differing anchors is unreachable
    in authored data (one anchor per profession record); the rule is pinned
    as "any place-bound component off its anchor strands the npc".
    """
    from typeclasses.components import (
        GuildExaminer,
        GuildStaff,
        Merchant,
        ScriptedDialogue,
    )
    from world.rules.party import bound_owner_of

    db = getattr(npc, "db", None)
    if db is None or db.party_member is None:
        return None
    if bound_owner_of(npc) is None:
        return None
    components = getattr(npc, "components", None)
    if components is None:
        return None
    location_pk = getattr(getattr(npc, "location", None), "pk", None)
    for component_class in (GuildStaff, GuildExaminer, Merchant, ScriptedDialogue):
        if not components.has(component_class.name):
            continue
        component = components.get(component_class.get_component_slot())
        if component is None:  # vocabulary class without a live slot
            continue
        if getattr(component, "service_binding", None) != "place":
            continue
        anchor_room_id = getattr(component, "anchor_room_id", None)
        if isinstance(anchor_room_id, bool) or not isinstance(anchor_room_id, int):
            return component_class.name  # corrupt anchor strands (fail closed)
        # Room-typed existence check, the service_available idiom: the
        # ObjectDB row converts to the stored typeclass, so a non-room row
        # is corrupt; a plain Room.objects filter would blind subclasses.
        from evennia.objects.models import ObjectDB
        from typeclasses.rooms import Room

        anchor_row = next(iter(ObjectDB.objects.filter(pk=anchor_room_id)), None)
        if anchor_row is None or not isinstance(anchor_row, Room):
            return component_class.name  # unresolvable anchor strands
        if location_pk != anchor_room_id:
            return component_class.name
    return None


def schedule_silenced(npc: Any) -> bool:
    """Whether the npc's authored schedule must settle NOTHING this window.

    True iff the npc is a bound party companion carrying a ``place``-bound
    service component outside its anchor room: the traveling clerk keeps
    walking with the party instead of being teleported back to the
    storefront mid-shift (design 2026-09-05-service-anchoring D6). Skipped
    windows are tolerated by the settlement's boundary arithmetic, so
    returning to the anchor (e.g. dismissal there) resumes settlement
    normally. This is the SINGLE gate slot where the companion-possession
    change will OR in its second trigger (possessed NPCs go silent too);
    callers never re-decide silence at the call site.
    """
    if getattr(getattr(npc, "db", None), "possessed_by", None) is not None:
        return True
    return off_anchor_place_service(npc) is not None
