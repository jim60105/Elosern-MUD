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
from typing import Any, Callable

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

#: The management inventory's availability answer: no player body is selected,
#: so the shared projection's actor-specific verdict cannot be asserted.
CONTEXT_REQUIRED = "context_required"
#: The exact reason every management entry carries in place of a player verdict.
CONTEXT_REQUIRED_MESSAGE = "未選擇玩家角色，無法判斷此服務是否可用。"

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


def _control_reason(actor: Any) -> ServiceReason | None:
    """The possession control refusal a capability group inherits, or ``None``."""
    return _reason(REASON_POSSESSED) if _possessed_by_control(actor) else None


def _native_rows(
    npc: Any,
) -> list[tuple[list[tuple[str, str, ServiceRoute]], Callable[[Any], ServiceReason | None]]]:
    """The host's native capabilities, in the fixed mapping order.

    Each group is the entries one component projects plus the one availability
    evaluation they share: the guild staff's three rows read the same
    component, gate and schedule. The caller decides whether to evaluate it
    (the player projection) or treat every entry as context-required (the
    management inventory).
    """
    npc_id = int(getattr(npc, "pk", 0) or 0)
    groups: list[
        tuple[list[tuple[str, str, ServiceRoute]], Callable[[Any], ServiceReason | None]]
    ] = []

    merchant = _component(npc, Merchant)
    if merchant is not None:
        # A closed shop stays inspectable: the shop's own ``open`` flag and its
        # product reasons belong to the flow this entry opens.
        groups.append(
            (
                [("shop", "商店", ServiceRoute(ROUTE_SERVICES, npc_id, section="shop"))],
                lambda actor: _service_gate_reason(
                    actor, npc, merchant, schedule_kind="service_shop"
                ),
            )
        )

    staff = _component(npc, GuildStaff)
    if staff is not None:
        groups.append(
            (
                [
                    (key, label, ServiceRoute(ROUTE_SERVICES, npc_id, section=section))
                    for key, label, section in _GUILD_STAFF_ROWS
                ],
                lambda actor: _control_reason(actor)
                or _service_gate_reason(
                    actor, npc, staff, schedule_kind="service_guild"
                ),
            )
        )

    reception = _component(npc, GuildExamReception)
    if reception is not None:
        # Entry only: registration, branch and next-rank eligibility stay inside
        # the rank flow, and merit or an absent qualified adventurer never
        # disables the request (schedule-first result).
        groups.append(
            (
                [
                    (
                        "guild.exam",
                        "參加升階考核",
                        ServiceRoute(ROUTE_SERVICES, npc_id, section="rank"),
                    )
                ],
                lambda actor: _control_reason(actor)
                or _service_gate_reason(
                    actor, npc, reception, schedule_kind="service_guild"
                ),
            )
        )

    church = _component(npc, ChurchHost)
    if church is not None:
        groups.append(
            (
                [
                    (
                        "church.enroll",
                        "入教",
                        ServiceRoute(ROUTE_COMMAND, npc_id, command=CHURCH_JOIN_COMMAND),
                    )
                ],
                lambda actor: _control_reason(actor)
                or _church_reason(actor, npc, church),
            )
        )
    return groups


def _native_entries(actor: Any, npc: Any) -> list[ServiceEntry]:
    """Project every native capability entry, in the fixed mapping order."""
    entries: list[ServiceEntry] = []
    for rows, reason_for in _native_rows(npc):
        reason = reason_for(actor)
        entries.extend(_entry(key, label, route, reason) for key, label, route in rows)
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


def read_dialogue_source(npc: Any) -> tuple[Any | None, bool]:
    """The host's resolved dialogue source and whether one was declared.

    ``dialogue_source_for_host`` returns ``None`` both when the host declares
    no dialogue source at all and when a declared one cannot resolve (an
    unknown static key, an unresolved generated phase). Management inspection
    must tell those apart: an unresolvable declared source leaves the service
    inventory unknown rather than silently empty.
    """
    from world.rules.dialogue_context import host_dialogue_binding
    from world.rules.dialogue_sources import dialogue_source_for_host

    source = dialogue_source_for_host(npc)
    if source is not None:
        return source, True
    _host_key, identity = host_dialogue_binding(npc)
    return None, identity is not None


def _dialogue_service_rows(
    source: Any, npc: Any
) -> list[tuple[str, str, ServiceRoute]]:
    """Every authored dialogue-service association, in stable key order."""
    npc_id = int(getattr(npc, "pk", 0) or 0)
    return [
        (
            f"dialogue.{service.key}",
            service.label,
            ServiceRoute(ROUTE_DIALOGUE, npc_id, topic_id=service.topic_id),
        )
        for service in sorted(source.dialogue.services, key=lambda service: service.key)
    ]


def _dialogue_entries(actor: Any, npc: Any) -> list[ServiceEntry]:
    """Project the host's explicit dialogue-service associations."""
    from world.rules.dialogue import authorized_dialogue_open
    from world.rules.dialogue_availability import (
        TOPIC_LOCKED,
        availability_context,
        project_topics,
    )

    component = _component(npc, ScriptedDialogue)
    if component is None:
        return []
    source, _declared = read_dialogue_source(npc)
    if source is None or not source.dialogue.services:
        return []
    gate = _service_gate_reason(actor, npc, component, schedule_kind="talk")
    if gate is None and not authorized_dialogue_open(actor, npc):
        gate = _reason(REASON_POSSESSED)
    rows = {
        row.topic_id: row for row in project_topics(availability_context(actor, npc))
    }
    entries: list[ServiceEntry] = []
    for key, label, route in _dialogue_service_rows(source, npc):
        row = rows.get(route.topic_id)
        if row is None:
            # Hidden by canonical disclosure/permission: the entry is omitted
            # entirely, exactly like the topic it advertises.
            continue
        reason = gate
        if reason is None and row.availability == TOPIC_LOCKED:
            reason = ServiceReason(
                REASON_TOPIC_LOCKED, row.requirement_hint or TOPIC_LOCKED_MESSAGE
            )
        entries.append(_entry(key, label, route, reason))
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


def inspect_npc_services(npc: Any) -> NpcServices:
    """The host's actor-independent service inventory, for management reads.

    The same capability mapping, labels and routes as
    :func:`project_npc_services`, but no player body is selected: every entry
    answers ``context_required`` with the exact reason that player context is
    absent, so no enabled player operation — and no fabricated player verdict —
    is ever presented. A caller must not use this as a player projection.

    Dialogue associations are filtered by the same actorless disclosure the
    shared availability semantics apply: an unconditional topic is enumerated,
    a guarded or predecessor-locked one is withheld, so a hidden association
    never appears in this inventory. A declared dialogue source that cannot
    resolve leaves the inventory unknown and is reported as ``unreadable``,
    never as an empty list.
    """
    from world.rules.dialogue_availability import (
        availability_context,
        project_topics,
    )

    npc_id = int(getattr(npc, "pk", 0) or 0)
    if npc_id <= 0:
        return NpcServices(STATE_NONE)
    try:
        rows = [
            row
            for group, _reason_for in _native_rows(npc)
            for row in group
        ]
        if _component(npc, ScriptedDialogue) is not None:
            source, declared = read_dialogue_source(npc)
            if source is None:
                if declared:
                    # An authored association list may exist; without the
                    # resolved source the complete inventory cannot be stated.
                    return NpcServices(STATE_UNREADABLE)
            elif source.dialogue.services:
                disclosed = {
                    row.topic_id
                    for row in project_topics(availability_context(None, npc))
                }
                rows.extend(
                    row
                    for row in _dialogue_service_rows(source, npc)
                    if row[2].topic_id in disclosed
                )
    except Exception as error:
        log_warn(
            PROJECTION_FAILED_EVENT,
            context={
                "npc": npc_id,
                "actor": 0,
                "error": type(error).__name__,
            },
            exc=error,
        )
        return NpcServices(STATE_UNREADABLE)
    if not rows:
        return NpcServices(STATE_NONE)
    if len(rows) > MAX_SERVICE_ENTRIES:
        # A runtime overflow is an integrity failure, never a silent truncation.
        log_warn(
            PROJECTION_FAILED_EVENT,
            context={"npc": npc_id, "actor": 0, "reason": "entry_overflow"},
        )
        return NpcServices(STATE_UNREADABLE)
    reason = ServiceReason(CONTEXT_REQUIRED, CONTEXT_REQUIRED_MESSAGE)
    return NpcServices(
        STATE_READY,
        tuple(_entry(key, label, route, reason) for key, label, route in rows),
    )


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


#: The existing text command one ``services`` route section opens, with the
#: exact selected provider written as its terminal target.
_SECTION_GUIDANCE: dict[str, str] = {
    "shop": "shop stock @#{npc_id}",
    "registration": "guild register @#{npc_id}",
    "board": "guild list @#{npc_id}",
    "report": "guild turnin <quest_id> @#{npc_id}",
    "rank": "guild exam @#{npc_id}",
}


def route_guidance(entry: ServiceEntry, name: str, npc_id: int) -> str:
    """Name the existing text flow one entry opens; it grants no authority."""
    route = entry.route
    if route.kind == ROUTE_DIALOGUE:
        # Talking opens the exact host; the associated topic is chosen in the
        # conversation and is never selected by discovery, so the guidance
        # stays one executable command with no identity or topic suffix.
        return f"talk {name}"
    if route.kind == ROUTE_COMMAND:
        return f"{route.command} #{npc_id}"
    return _SECTION_GUIDANCE[route.section].format(npc_id=npc_id)


def service_report_lines(npc: Any, services: NpcServices) -> list[str]:
    """Render one derived projection as bounded player-facing text lines.

    A pure read of the same descriptors the browser receives: the stable key,
    the canonical label, the exact disabled reason, and the existing text
    route. ``none`` (a host genuinely offers nothing) and ``unreadable`` (the
    projection failed) stay distinct sentences, and every disabled entry keeps
    its reason instead of disappearing. Nothing here writes, selects, or
    creates authority.
    """
    name = str(getattr(npc, "key", "") or "") or "對象"
    if services.state == STATE_UNREADABLE:
        return [f"{name}：{UNREADABLE_MESSAGE}"]
    if services.state != STATE_READY or not services.entries:
        return [f"{name} 目前沒有提供服務。"]
    npc_id = int(getattr(npc, "pk", 0) or 0)
    lines = [f"{name} 的服務："]
    for entry in services.entries:
        if entry.enabled:
            lines.append(
                f"  {entry.key}　{entry.label}　→ "
                f"{route_guidance(entry, name, npc_id)}"
            )
            if entry.route.kind == ROUTE_DIALOGUE:
                # The topic is named on its own annotation line: the copyable
                # command above stays one executable ``talk <npc>`` and never
                # selects the topic.
                lines.append(
                    f"    相關話題：{entry.route.topic_id}（於對話中選擇）"
                )
        else:
            lines.append(
                f"  {entry.key}　{entry.label}（{entry.disabled_reason.message}）"
            )
    return lines


__all__ = [
    "CHURCH_JOIN_COMMAND",
    "CONTEXT_REQUIRED",
    "CONTEXT_REQUIRED_MESSAGE",
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
    "inspect_npc_services",
    "native_entry_count",
    "project_npc_services",
    "read_dialogue_source",
    "route_guidance",
    "service_report_lines",
    "validate_service_capacity",
]
