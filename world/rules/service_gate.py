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
- New service capabilities declare their binding in the capability core
  (``world/rules/npc_capabilities.py``) and wire their gate in HERE; they do
  not re-decide location semantics at the call site.

Availability comes exclusively from persisted component fields
(``service_binding`` / ``anchor_room_id``, written by the shared capability
assembly). Runtime gates read components, never the authored declaration.
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


@dataclass(frozen=True)
class ServiceBindingReport:
    """One component's stored binding, anchor and configuration facts.

    ``gate_malformed`` is the runtime admissibility answer that
    :func:`service_available` refuses on. ``anchor_on_person`` records the
    anchored ``person`` binding the capability importer rejects (the runtime
    gate stays permissive: it never checked this and admissibility must not
    change here). ``anchor_raw`` is the stored value exactly as written;
    ``anchor_room`` is populated only when a ``place`` binding's anchor was
    actually resolved. Read-only facts for configuration inspection; nothing
    in this module repairs or rejects authored data.
    """

    binding: str | None
    anchor_raw: Any
    anchor_room_id: int | None
    anchor_room: Any | None
    gate_malformed: bool
    anchor_on_person: bool


def read_service_binding(component: Any) -> ServiceBindingReport:
    """Read one component's binding and resolve its anchor room. Read-only.

    Reads only persisted component fields (``service_binding`` /
    ``anchor_room_id``) and answers the same questions the runtime gate asks,
    without its debounced warn event: an inspection read must not emit the
    gameplay malformed-binding reminder. A non-``place`` binding reports its
    stored anchor without resolving it — that reference is never used, so
    claiming it cannot resolve would be false.
    """
    binding = getattr(component, "service_binding", None)
    raw_anchor = getattr(component, "anchor_room_id", None)
    if binding == "person":
        # An anchor on a person binding is authored data the importer rejects;
        # the runtime gate never checked it, so it stays an inspection fact.
        return ServiceBindingReport(
            binding, raw_anchor, None, None, False, raw_anchor is not None
        )
    if binding != "place":
        return ServiceBindingReport(binding, raw_anchor, None, None, True, False)
    anchor_id = (
        None
        if isinstance(raw_anchor, bool) or not isinstance(raw_anchor, int)
        else raw_anchor
    )
    if anchor_id is None:
        return ServiceBindingReport(binding, raw_anchor, None, None, True, False)
    # The anchor lives whenever a ROOM row with that id exists (Evennia deletes
    # the location reference with the room, so no dangling-location state can
    # masquerade as at-anchor). The query converts each row to its stored
    # typeclass, so the isinstance gate rejects a stored id that points at a
    # non-room object (import-time resolution pins rooms; this is the
    # corruption defense in depth). A plain Room.objects filter would pin to
    # one typeclass path and blind subclass rooms — same constraint
    # world/maps/bootstrap.py documents.
    from evennia.objects.models import ObjectDB
    from typeclasses.rooms import Room

    anchor_row = next(iter(ObjectDB.objects.filter(pk=anchor_id)), None)
    if anchor_row is None or not isinstance(anchor_row, Room):
        return ServiceBindingReport(binding, raw_anchor, anchor_id, None, True, False)
    return ServiceBindingReport(
        binding, raw_anchor, anchor_id, anchor_row, False, False
    )


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
    3. Anything malformed in the stored data — a MISSING binding, an UNKNOWN
       binding value, or a ``place`` whose anchor room cannot resolve — is
       ``malformed_binding`` and fails closed.

    A bound service capability always carries a stored binding: the shared
    assembly writes one on every component it touches, and every service type
    requires a declared binding. An unset field therefore describes state the
    assembly never produced, and an unknown value describes corruption; both
    fail closed rather than defaulting open. Ordinary narrative dialogue is
    never queried here — it carries no service and keeps its own talk gates.
    """
    if actor.location is None or host.location != actor.location:
        return _REMOTE
    # The binding short circuits run before the anchor field is ever read: a
    # person binding and an unknown binding must answer exactly as before, even
    # when the stored anchor value is unreadable (design 2026-09-05-service-
    # anchoring §3).
    binding = getattr(component, "service_binding", None)
    if binding == "person":
        return _ALLOWED
    if binding != "place":
        _warn_malformed(host, component)
        return _MALFORMED
    report = read_service_binding(component)
    if report.gate_malformed:
        _warn_malformed(host, component)
        return _MALFORMED
    anchor_pk = getattr(host.location, "pk", None)
    if anchor_pk != report.anchor_room_id:
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
       function-locally from ``typeclasses.components`` (this module reads
       components, never the authored declaration).
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
        GuildExamReception,
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
    for component_class in (GuildStaff, GuildExamReception, Merchant, ScriptedDialogue):
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
    from world.rules.party import bound_owner_of, reasons_for

    owner = bound_owner_of(npc)
    if owner is not None and reasons_for(npc, owner):
        return True
    return off_anchor_place_service(npc) is not None
