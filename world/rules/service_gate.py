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
