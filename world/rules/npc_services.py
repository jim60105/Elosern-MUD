"""Derived contextual service projection for one selected NPC (slice P).

One pure, read-only owner turns the selected NPC's capabilities and its source's
explicit dialogue-service associations into the bounded service entries a
player-facing card can show: a stable semantic key, a player label, honest
availability with a reason, and an exact route to an existing deterministic
flow. The projection is derived data — it is never persisted, never cached on
the NPC, and never duplicates authority: every route revalidates its exact
selected provider at submission.

Entry availability is not operation eligibility. Co-presence, binding,
schedule, control permission and the domain's own entry rules decide whether an
entry can be opened; product affordability, stock, quest eligibility and merit
stay inside the flow the entry opens (an unaffordable customer may inspect a
shop; a below-merit member may ask for the examination schedule).

A projection failure is reported as ``unreadable`` with zero entries — never as
an empty list, whose ``none`` state means a host genuinely offers nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from typeclasses.components import (
    ChurchHost,
    GuildExamReception,
    GuildStaff,
    Merchant,
    ScriptedDialogue,
)
from world.observability import log_warn
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import (
    REASON_MALFORMED_BINDING,
    REASON_OFF_ANCHOR,
    service_available,
)
from world.rules.service_messages import FALLBACK_MESSAGE, SERVICE_REASON_MESSAGES

STATE_NONE = "none"
STATE_READY = "ready"
STATE_UNREADABLE = "unreadable"
SERVICE_STATES = (STATE_NONE, STATE_READY, STATE_UNREADABLE)

MAX_SERVICE_ENTRIES = 16
MAX_SERVICE_KEY_CHARS = 64
MAX_SERVICE_LABEL_CODE_POINTS = 64
MAX_SERVICE_REASON_CODE_CHARS = 64
MAX_SERVICE_REASON_MESSAGE_CODE_POINTS = 240

#: The player-facing copy of the distinct unreadable state (the wire carries the
#: state, the client renders this sentence).
UNREADABLE_MESSAGE = "服務資訊暫時無法讀取。"

ROUTE_SERVICES = "services"
ROUTE_DIALOGUE = "dialogue"
ROUTE_COMMAND = "command"
ROUTE_KINDS = (ROUTE_SERVICES, ROUTE_DIALOGUE, ROUTE_COMMAND)
SERVICE_SECTIONS = ("shop", "registration", "board", "report", "rank")

#: The one text command an entry may pre-fill. The player still submits it.
CHURCH_JOIN_COMMAND = "church join"

PROJECTION_FAILED_EVENT = "npc_services_projection_failed"

#: The stable reason code of one locked dialogue topic.
REASON_TOPIC_LOCKED = "topic_locked"
TOPIC_LOCKED_MESSAGE = "這個話題目前還不能深入。"

#: Stable reason code of a control refusal (a possessed body may only use the
#: merchant counters, matching ``service_targets.require_service_mutation``).
REASON_POSSESSED = "possessed_service"
REASON_NOT_A_PLAYER = "not_a_player"
REASON_ALREADY_ENROLLED = "already_enrolled"
REASON_SCHEDULE_BLOCKED = "schedule_blocked"
REASON_SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass(frozen=True)
class ServiceReason:
    """One exact disabled reason: a stable code and its player-facing message."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.code, str)
            or not self.code
            or len(self.code) > MAX_SERVICE_REASON_CODE_CHARS
        ):
            raise ValueError(
                f"service reason code must be 1..{MAX_SERVICE_REASON_CODE_CHARS} characters"
            )
        if not isinstance(self.message, str) or not (
            1 <= len(self.message) <= MAX_SERVICE_REASON_MESSAGE_CODE_POINTS
        ):
            raise ValueError(
                "service reason message must be 1.."
                f"{MAX_SERVICE_REASON_MESSAGE_CODE_POINTS} code points"
            )

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class ServiceRoute:
    """The exact discriminated route one entry opens.

    ``services`` routes open the selected provider's existing drawer section,
    ``dialogue`` routes open that exact host and focus its associated topic
    without selecting it, and ``command`` routes only focus/pre-fill the text
    command. Every route names the selected provider; no route carries
    authority.
    """

    kind: str
    npc_id: int
    section: str | None = None
    topic_id: str | None = None
    command: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in ROUTE_KINDS:
            raise ValueError(f"unknown service route kind {self.kind!r}")
        if isinstance(self.npc_id, bool) or not isinstance(self.npc_id, int) or self.npc_id <= 0:
            raise ValueError("service route npc_id must be a positive integer")
        if self.kind == ROUTE_SERVICES:
            if self.section not in SERVICE_SECTIONS:
                raise ValueError("services route section is not a stable value")
            if self.topic_id is not None or self.command is not None:
                raise ValueError("a services route carries only its section")
        elif self.kind == ROUTE_DIALOGUE:
            if not isinstance(self.topic_id, str) or not self.topic_id:
                raise ValueError("a dialogue route requires a topic_id")
            if self.section is not None or self.command is not None:
                raise ValueError("a dialogue route carries only its topic_id")
        else:
            if self.command != CHURCH_JOIN_COMMAND:
                raise ValueError("a command route names the one supported command")
            if self.section is not None or self.topic_id is not None:
                raise ValueError("a command route carries only its command")

    def as_dict(self) -> dict[str, Any]:
        if self.kind == ROUTE_SERVICES:
            return {"kind": self.kind, "npc_id": self.npc_id, "section": self.section}
        if self.kind == ROUTE_DIALOGUE:
            return {"kind": self.kind, "npc_id": self.npc_id, "topic_id": self.topic_id}
        return {"kind": self.kind, "npc_id": self.npc_id, "command": self.command}


@dataclass(frozen=True)
class ServiceEntry:
    """One projected service entry: identity, label, availability, route."""

    key: str
    label: str
    enabled: bool
    disabled_reason: ServiceReason | None
    route: ServiceRoute

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str)
            or not self.key
            or len(self.key) > MAX_SERVICE_KEY_CHARS
            or not self.key.isascii()
        ):
            raise ValueError(
                f"service key must be 1..{MAX_SERVICE_KEY_CHARS} ASCII characters"
            )
        if not isinstance(self.label, str) or not (
            1 <= len(self.label) <= MAX_SERVICE_LABEL_CODE_POINTS
        ):
            raise ValueError(
                f"service label must be 1..{MAX_SERVICE_LABEL_CODE_POINTS} code points"
            )
        if not isinstance(self.enabled, bool):
            raise ValueError("service enabled must be a boolean")
        if self.enabled:
            if self.disabled_reason is not None:
                raise ValueError("an enabled service entry carries no reason")
        elif not isinstance(self.disabled_reason, ServiceReason):
            raise ValueError("a disabled service entry requires a reason")

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "enabled": self.enabled,
            "disabled_reason": (
                None if self.disabled_reason is None else self.disabled_reason.as_dict()
            ),
            "route": self.route.as_dict(),
        }


@dataclass(frozen=True)
class NpcServices:
    """The complete derived service information of one selected NPC."""

    state: str
    entries: tuple[ServiceEntry, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in SERVICE_STATES:
            raise ValueError(f"unknown service state {self.state!r}")
        if not isinstance(self.entries, tuple):
            raise TypeError("service entries must be a tuple")
        if len(self.entries) > MAX_SERVICE_ENTRIES:
            raise ValueError(
                f"a projection cannot exceed {MAX_SERVICE_ENTRIES} service entries"
            )
        if self.state == STATE_READY and not self.entries:
            raise ValueError("a ready projection requires at least one entry")
        if self.state != STATE_READY and self.entries:
            raise ValueError("an empty or unreadable projection carries no entry")

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "entries": [entry.as_dict() for entry in self.entries],
        }


#: The guild staff's three entries share one component and one gate.
_GUILD_STAFF_ROWS: tuple[tuple[str, str, str], ...] = (
    ("guild.register", "登記成為冒險者", "registration"),
    ("guild.board", "查看委託看板", "board"),
    ("guild.report", "回報委託", "report"),
)


def _reason(code: str) -> ServiceReason:
    return ServiceReason(code, SERVICE_REASON_MESSAGES.get(code, FALLBACK_MESSAGE))


def _gate_reason(verdict: Any) -> ServiceReason:
    """Map one availability-gate verdict onto the disabled reason."""
    if verdict.reason == REASON_OFF_ANCHOR:
        return _reason(REASON_OFF_ANCHOR)
    if verdict.reason == REASON_MALFORMED_BINDING:
        return _reason(REASON_MALFORMED_BINDING)
    return _reason(REASON_SERVICE_UNAVAILABLE)


def _component(npc: Any, component_class: type) -> Any | None:
    components = getattr(npc, "components", None)
    if components is None or not components.has(component_class.name):
        return None
    return components.get(component_class.get_component_slot())


def _entry(
    key: str,
    label: str,
    route: ServiceRoute,
    reason: ServiceReason | None,
) -> ServiceEntry:
    return ServiceEntry(
        key=key,
        label=label,
        enabled=reason is None,
        disabled_reason=reason,
        route=route,
    )


def _service_gate_reason(
    actor: Any,
    npc: Any,
    component: Any,
    *,
    schedule_kind: str,
) -> ServiceReason | None:
    """The gate + schedule refusal of one native capability, or ``None``."""
    verdict = service_available(actor, npc, component)
    if not verdict.allowed:
        return _gate_reason(verdict)
    blocked = interaction_reason(npc, schedule_kind)
    if blocked is not None:
        return ServiceReason(REASON_SCHEDULE_BLOCKED, blocked)
    return None


def _possessed_by_control(actor: Any) -> bool:
    from world.rules.possession import is_possessed_actor

    return is_possessed_actor(actor)


def _native_entries(actor: Any, npc: Any) -> list[ServiceEntry]:
    """Project every native capability entry, in the fixed mapping order."""
    npc_id = int(getattr(npc, "pk", 0) or 0)
    entries: list[ServiceEntry] = []
    possessed = _possessed_by_control(actor)
    control_reason = _reason(REASON_POSSESSED) if possessed else None

    merchant = _component(npc, Merchant)
    if merchant is not None:
        # A closed shop stays inspectable: the shop's own ``open`` flag and its
        # product reasons belong to the flow this entry opens.
        reason = _service_gate_reason(
            actor, npc, merchant, schedule_kind="service_shop"
        )
        entries.append(
            _entry(
                "shop",
                "商店",
                ServiceRoute(ROUTE_SERVICES, npc_id, section="shop"),
                reason,
            )
        )

    staff = _component(npc, GuildStaff)
    if staff is not None:
        reason = control_reason or _service_gate_reason(
            actor, npc, staff, schedule_kind="service_guild"
        )
        for key, label, section in _GUILD_STAFF_ROWS:
            entries.append(
                _entry(
                    key,
                    label,
                    ServiceRoute(ROUTE_SERVICES, npc_id, section=section),
                    reason,
                )
            )

    reception = _component(npc, GuildExamReception)
    if reception is not None:
        # Entry only: registration, branch and next-rank eligibility stay inside
        # the rank flow, and merit or an absent qualified adventurer never
        # disables the request (schedule-first result).
        reason = control_reason or _service_gate_reason(
            actor, npc, reception, schedule_kind="service_guild"
        )
        entries.append(
            _entry(
                "guild.exam",
                "參加升階考核",
                ServiceRoute(ROUTE_SERVICES, npc_id, section="rank"),
                reason,
            )
        )

    church = _component(npc, ChurchHost)
    if church is not None:
        entries.append(
            _entry(
                "church.enroll",
                "入教",
                ServiceRoute(ROUTE_COMMAND, npc_id, command=CHURCH_JOIN_COMMAND),
                control_reason or _church_reason(actor, npc, church),
            )
        )
    return entries


def _church_reason(actor: Any, npc: Any, component: Any) -> ServiceReason | None:
    """The enrollment entry's own availability, or ``None`` when it is open."""
    from typeclasses.characters import PlayerCharacter
    from world.rules.church import read_ledger

    if not isinstance(actor, PlayerCharacter):
        return _reason(REASON_NOT_A_PLAYER)
    reason = _service_gate_reason(
        actor, npc, component, schedule_kind="service_church"
    )
    if reason is not None:
        return reason
    if read_ledger(actor) is not None:
        return _reason(REASON_ALREADY_ENROLLED)
    return None


def _dialogue_entries(actor: Any, npc: Any) -> list[ServiceEntry]:
    """Project the host's explicit dialogue-service associations."""
    from world.rules.dialogue import authorized_dialogue_open
    from world.rules.dialogue_availability import (
        TOPIC_LOCKED,
        availability_context,
        project_topics,
    )
    from world.rules.dialogue_sources import dialogue_source_for_host

    source = dialogue_source_for_host(npc)
    if source is None or not source.dialogue.services:
        return []
    npc_id = int(getattr(npc, "pk", 0) or 0)
    component = _component(npc, ScriptedDialogue)
    if component is None:
        return []
    gate = _service_gate_reason(actor, npc, component, schedule_kind="talk")
    if gate is None and not authorized_dialogue_open(actor, npc):
        gate = _reason(REASON_POSSESSED)
    rows = {
        row.topic_id: row for row in project_topics(availability_context(actor, npc))
    }
    entries: list[ServiceEntry] = []
    for service in sorted(source.dialogue.services, key=lambda service: service.key):
        row = rows.get(service.topic_id)
        if row is None:
            # Hidden by canonical disclosure/permission: the entry is omitted
            # entirely, exactly like the topic it advertises.
            continue
        reason = gate
        if reason is None and row.availability == TOPIC_LOCKED:
            reason = ServiceReason(
                REASON_TOPIC_LOCKED, row.requirement_hint or TOPIC_LOCKED_MESSAGE
            )
        entries.append(
            _entry(
                f"dialogue.{service.key}",
                service.label,
                ServiceRoute(ROUTE_DIALOGUE, npc_id, topic_id=service.topic_id),
                reason,
            )
        )
    return entries


def project_npc_services(actor: Any, viewer: Any, npc: Any) -> NpcServices:
    """Project one selected NPC's contextual services for ``actor``.

    ``actor`` is the acting body whose presence, control permission and
    enrollment/registration state decide availability; ``viewer`` is the player
    whose canonical paperwork the presentation describes (the possession owner
    when the actor is a possessed companion, else the actor itself). Every
    caller currently passes the acting body as ``viewer``; the parameter keeps
    the owner-aware presentation contract explicit.

    A failure inside the projection is reported as ``unreadable`` with zero
    entries, so no stale actionable row can outlive the data it described.
    """
    del viewer
    npc_id = int(getattr(npc, "pk", 0) or 0)
    if npc_id <= 0:
        return NpcServices(STATE_NONE)
    try:
        entries = _native_entries(actor, npc) + _dialogue_entries(actor, npc)
    except Exception as error:
        log_warn(
            PROJECTION_FAILED_EVENT,
            context={
                "npc": npc_id,
                "actor": int(getattr(actor, "pk", 0) or 0),
                "error": type(error).__name__,
            },
            exc=error,
        )
        return NpcServices(STATE_UNREADABLE)
    if not entries:
        return NpcServices(STATE_NONE)
    if len(entries) > MAX_SERVICE_ENTRIES:
        # Authored assembly rejects an oversized combination before publication;
        # a runtime overflow is an integrity failure, never a silent truncation.
        log_warn(
            PROJECTION_FAILED_EVENT,
            context={
                "npc": npc_id,
                "actor": int(getattr(actor, "pk", 0) or 0),
                "reason": "entry_overflow",
            },
        )
        return NpcServices(STATE_UNREADABLE)
    return NpcServices(STATE_READY, tuple(entries))


def native_entry_count(type_keys: Any) -> int:
    """The number of native capability entries one host's types project."""
    keys = frozenset(type_keys or ())
    count = 0
    if "merchant" in keys:
        count += 1
    if "guild_staff" in keys:
        count += len(_GUILD_STAFF_ROWS)
    if "guild_exam_reception" in keys:
        count += 1
    if "church_host" in keys:
        count += 1
    return count


def validate_service_capacity(type_keys: Any, associated_count: int) -> None:
    """Reject a host whose native plus associated entries exceed the bound.

    Rejection is atomic at the caller (publication/assembly); the runtime never
    truncates an accepted list.
    """
    if isinstance(associated_count, bool) or not isinstance(associated_count, int):
        raise TypeError("associated_count must be an integer")
    if associated_count < 0:
        raise ValueError("associated_count must not be negative")
    total = native_entry_count(type_keys) + associated_count
    if total > MAX_SERVICE_ENTRIES:
        raise ValueError(
            f"a host may declare at most {MAX_SERVICE_ENTRIES} service entries, "
            f"got {total}"
        )


__all__ = [
    "CHURCH_JOIN_COMMAND",
    "MAX_SERVICE_ENTRIES",
    "NpcServices",
    "PROJECTION_FAILED_EVENT",
    "ROUTE_COMMAND",
    "ROUTE_DIALOGUE",
    "ROUTE_KINDS",
    "ROUTE_SERVICES",
    "SERVICE_SECTIONS",
    "SERVICE_STATES",
    "STATE_NONE",
    "STATE_READY",
    "STATE_UNREADABLE",
    "ServiceEntry",
    "ServiceReason",
    "ServiceRoute",
    "UNREADABLE_MESSAGE",
    "native_entry_count",
    "project_npc_services",
    "validate_service_capacity",
]
