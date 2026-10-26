"""Direct NPC capability declarations: one schema, one validator, one assembler.

A profession is gone. An NPC's capabilities are declared directly where the
NPC is authored — an imported record's ``components``, a place's
``components``, a generated package role's ``capabilities`` — and every
producer goes through exactly these two functions:

- :func:`validate_capabilities` turns authored entries into an immutable
  :class:`CapabilityPlan` (pure shape/vocabulary/reference validation; room
  tags are resolved only through the caller's injected resolver).
- :func:`assemble_capabilities` attaches and configures that complete plan on
  one entity and is the ONLY writer of the availability-binding fields.

The component-type vocabulary, the per-type required/optional authored kwargs
and the runtime-owned fields that authored data must never set live here so the
imports pipeline, the place-derived service roster and the generated package
producer cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from typeclasses.components import (
    ChurchHost,
    GuildExamReception,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from world.lore.settlements.capability_declarations import (
    BINDING_KINDS,
    Binding,
    CapabilityDeclaration,
    CapabilityValidationError,
    capability,
    person_bound,
    place_bound,
)
from world.lore.sexual_vocab import AROUSAL_LEVELS

#: The closed capability vocabulary. Keys MUST equal each component class's
#: declared ``name`` (the contract test in
#: ``world/rules/tests/test_npc_capabilities.py`` pins the symmetry).
COMPONENT_TYPES: dict[str, type] = {
    "guild_staff": GuildStaff,
    "guild_exam_reception": GuildExamReception,
    "merchant": Merchant,
    "scripted_dialogue": ScriptedDialogue,
    "quest_issuer": QuestIssuer,
    "church_host": ChurchHost,
}

#: Fields the runtime owns. Authored data can never set them: the assembly is
#: their single writer (binding + anchor) and the subsystems own their state
#: (stock + restock progress).
RUNTIME_FIELDS = frozenset(
    {"service_binding", "anchor_room_id", "merchant_stock", "last_restock_day"}
)

#: Authored kwargs every declaration of a type MUST supply. An absent or blank
#: identity value is a rejection, never a default: the assembler invents no
#: identifier.
REQUIRED_KWARGS: dict[str, frozenset[str]] = {
    "merchant": frozenset({"service_id", "shop_key"}),
    "guild_staff": frozenset({"service_id", "branch_key"}),
    "guild_exam_reception": frozenset({"service_id", "branch_key"}),
    "scripted_dialogue": frozenset({"dialogue_key"}),
    "quest_issuer": frozenset({"service_id"}),
    "church_host": frozenset({"service_id", "church", "initial_arousal"}),
}

#: Authored kwargs a type accepts but does not require. ``issuer_key`` stays
#: optional: an absent or empty value keeps the canonical ``npc:#<pk>``
#: identity form. ``service_id`` on a dialogue component is ordinary config
#: (the historic anchor-read value), never host identity.
OPTIONAL_KWARGS: dict[str, frozenset[str]] = {
    "scripted_dialogue": frozenset({"service_id"}),
    "quest_issuer": frozenset({"issuer_key"}),
}

#: Capabilities that ARE a service. Every one of them must declare its binding:
#: an unbound service is exactly the "unknown availability" state the service
#: gate fails closed on.
REQUIRED_BINDING = frozenset(
    {"merchant", "guild_staff", "guild_exam_reception", "quest_issuer", "church_host"}
)

_ENTRY_FIELDS = frozenset({"type", "kwargs", "binding"})
_BINDING_FIELDS = frozenset({"kind", "anchor_room"})


@dataclass(frozen=True)
class PlannedCapability:
    """One validated capability, with its place anchor resolved when declared."""

    type: str
    kwargs: Mapping[str, Any]
    binding: Binding | None = None
    #: The resolved room object for a ``place`` binding (``None`` until a room
    #: resolver ran; always ``None`` for ``person`` and unbound capabilities).
    anchor_room: Any | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kwargs, Mapping):
            raise CapabilityValidationError(
                [f"component {self.type!r} kwargs must be a mapping"]
            )
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))


@dataclass(frozen=True)
class CapabilityPlan:
    """The complete, validated, immutable capability set of one entity."""

    components: tuple[PlannedCapability, ...] = ()

    def __post_init__(self) -> None:
        # Vocabulary membership and uniqueness are structural: a plan cannot
        # even hold two entries of one capability type. The per-type kwargs,
        # binding and resolved-anchor invariants are re-checked by
        # :func:`assemble_capabilities` before any write.
        seen: set[str] = set()
        for component in self.components:
            if component.type not in COMPONENT_TYPES:
                raise CapabilityValidationError(
                    [f"component {component.type!r} is outside the vocabulary"]
                )
            if component.type in seen:
                raise CapabilityValidationError(
                    [f"component {component.type!r} is declared more than once"]
                )
            seen.add(component.type)

    def type_keys(self) -> frozenset[str]:
        return frozenset(component.type for component in self.components)

    def component(self, type_key: str) -> PlannedCapability | None:
        return next(
            (component for component in self.components if component.type == type_key),
            None,
        )

    def kwargs_for(self, type_key: str) -> Mapping[str, Any]:
        component = self.component(type_key)
        return {} if component is None else component.kwargs


def managed_type_keys() -> frozenset[str]:
    """The capability slots a source-owned host reconciles (the vocabulary)."""
    return frozenset(COMPONENT_TYPES)


def component_field_names(type_key: str) -> frozenset[str]:
    """The authored kwargs the type accepts (its class fields minus runtime)."""
    component_class = COMPONENT_TYPES[type_key]
    return frozenset(component_class._fields) - RUNTIME_FIELDS


def component_attribute_keys(type_key: str) -> tuple[str, ...]:
    """The host-attribute keys backing one component's persistent fields."""
    component_class = COMPONENT_TYPES[type_key]
    slot = component_class.get_component_slot()
    return tuple(f"{slot}::{name}" for name in component_class._fields)


def _as_binding(raw: Any, path: str, issues: list[str]) -> Binding | None:
    if raw is None:
        return None
    if isinstance(raw, Binding):
        # An authored declaration carries the frozen carrier; re-validate it
        # through the same shape rules the JSON form faces.
        authored = raw
        raw = {"kind": authored.kind}
        if authored.anchor_room is not None:
            raw["anchor_room"] = authored.anchor_room
    if not isinstance(raw, Mapping):
        issues.append(f"{path}.binding must be a mapping")
        return None
    unknown = set(raw) - _BINDING_FIELDS
    if unknown:
        issues.append(f"{path}.binding has unknown fields {sorted(unknown, key=repr)}")
        return None
    kind = raw.get("kind")
    if kind not in BINDING_KINDS:
        issues.append(
            f"{path}.binding kind {kind!r} is outside {sorted(BINDING_KINDS)}"
        )
        return None
    if kind == "person":
        if "anchor_room" in raw:
            issues.append(
                f"{path}.binding is person-bound; an anchor room is the invalid "
                "combination"
            )
            return None
        return person_bound()
    anchor = raw.get("anchor_room")
    if not isinstance(anchor, str) or not anchor.strip():
        issues.append(f"{path}.binding is place-bound; a non-empty anchor_room tag is required")
        return None
    return place_bound(anchor)


def _as_entry(entry: Any, index: int, owner: str | None) -> tuple[str, Mapping[str, Any], Any, list[str]]:
    """Normalize one declaration/mapping entry, collecting named offenses."""
    path = f"components[{index}]"
    if isinstance(entry, CapabilityDeclaration):
        return entry.type, entry.kwargs, entry.binding, []
    if not isinstance(entry, Mapping):
        return "", {}, None, [f"{path} must be a mapping"]
    unknown = set(entry) - _ENTRY_FIELDS
    missing = {"type", "kwargs"} - set(entry)
    if unknown or missing:
        detail = []
        if unknown:
            detail.append(f"unknown fields {sorted(unknown, key=repr)}")
        if missing:
            detail.append(f"missing fields {sorted(missing, key=repr)}")
        return "", {}, None, [f"{path} " + " and ".join(detail)]
    return entry["type"], entry["kwargs"], entry.get("binding"), []


def _validate_kwargs(
    type_key: str, kwargs: Mapping[str, Any], path: str, issues: list[str]
) -> None:
    if not isinstance(kwargs, Mapping):
        issues.append(f"{path}.kwargs must be a mapping")
        return
    for field in sorted(set(kwargs) & RUNTIME_FIELDS):
        issues.append(
            f"{path}.kwargs authors runtime-owned field {field!r}; the assembly "
            "and its owning subsystem are its only writers"
        )
    allowed = REQUIRED_KWARGS[type_key] | OPTIONAL_KWARGS.get(type_key, frozenset())
    for field in sorted(set(kwargs) - allowed):
        issues.append(
            f"{path}.kwargs authors {field!r}, which component {type_key!r} does "
            f"not accept; authored kwargs are {sorted(allowed)}"
        )
    for field in sorted(REQUIRED_KWARGS[type_key]):
        value = kwargs.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                f"{path}.kwargs requires a non-empty {field!r} for component "
                f"{type_key!r}"
            )
    for field in sorted(OPTIONAL_KWARGS.get(type_key, frozenset())):
        if field not in kwargs:
            continue
        value = kwargs[field]
        if not isinstance(value, str):
            issues.append(f"{path}.kwargs {field!r} must be a string")


def _validate_references(type_key: str, kwargs: Mapping[str, Any], path: str, issues: list[str]) -> None:
    """Validate registry references through their existing owners."""
    if type_key == "scripted_dialogue":
        table = _loaded_dialogue_table()
        key = kwargs.get("dialogue_key")
        if table is not None and isinstance(key, str) and key and key not in table:
            issues.append(
                f"{path}.kwargs authors dialogue_key {key!r} that the dialogue "
                "registry does not carry"
            )
    if type_key == "church_host":
        level = kwargs.get("initial_arousal")
        if isinstance(level, str) and level and level not in AROUSAL_LEVELS:
            issues.append(
                f"{path}.kwargs authors initial_arousal {level!r} outside "
                f"{list(AROUSAL_LEVELS)}"
            )
    if type_key == "quest_issuer":
        authored = kwargs.get("issuer_key")
        if isinstance(authored, str) and authored:
            from world.rules.quest_issuance import IssuerKeyError, parse_issuer_key

            try:
                parse_issuer_key(f"npc:{authored}")
            except IssuerKeyError as error:
                issues.append(
                    f"{path}.kwargs authors issuer_key {authored!r} outside the "
                    f"issuer-key grammar: {error}"
                )


def _loaded_dialogue_table() -> Any | None:
    """The dialogue registry, or ``None`` during one bootstrap window.

    The place registry validates itself while the lore package is still
    importing, and the dialogue facade imports that package; that single
    import-time window is the only case where the facade cannot be loaded yet,
    so the reference check defers there and the roster derivation re-checks the
    keys before any write. Every later boundary (imports validation, assembly,
    roster/config, generated packages) loads the registry through its owner and
    enforces the check.
    """
    try:
        from world.rules.dialogue import DIALOGUE_TABLE
    except ImportError:  # observability: ignore R2: importing the dialogue facade re-enters the lore package that is mid-import; the deferral is limited to that bootstrap window and every persistence boundary re-validates through assemble_capabilities
        return None
    return DIALOGUE_TABLE


def _resolve_room(tag: str, resolver: Callable[[str], Sequence[Any]], path: str, issues: list[str]) -> Any | None:
    """Resolve one place anchor to exactly one Room object."""
    from typeclasses.rooms import Room

    candidates = list(resolver(tag))
    rooms = [obj for obj in candidates if isinstance(obj, Room)]
    others = [obj for obj in candidates if not isinstance(obj, Room)]
    if others:
        issues.append(
            f"{path}.binding anchor_room {tag!r} resolves to a non-Room object; "
            "an anchor must name a room"
        )
        return None
    if not rooms:
        issues.append(f"{path}.binding anchor_room {tag!r} resolves to no room")
        return None
    if len(rooms) > 1:
        issues.append(
            f"{path}.binding anchor_room {tag!r} resolves to {len(rooms)} rooms; "
            "the anchor must be unique"
        )
        return None
    return rooms[0]


def resolve_room(tag: str, resolver: Callable[[str], Sequence[Any]]) -> Any:
    """Resolve one room tag to exactly one Room, or raise by name.

    The one exact-one-Room rule the capability anchors use, exposed so a caller
    that must resolve a room of its own (a host's spawn room) applies the same
    fail-closed semantics instead of taking a first match.
    """
    issues: list[str] = []
    room = _resolve_room(tag, resolver, "room", issues)
    if issues:
        raise CapabilityValidationError(issues)
    return room


def validate_capabilities(
    entries: Sequence[Any] | None,
    *,
    room_resolver: Callable[[str], Sequence[Any]] | None = None,
) -> CapabilityPlan:
    """Validate authored capability entries and return their immutable plan.

    Pure: it reads no database and writes nothing. Place anchors stay
    unresolved until a ``room_resolver`` is injected — the caller that owns the
    transaction resolves them, so a missing/ambiguous/non-Room tag rejects the
    whole operation BEFORE any persistence. :func:`assemble_capabilities`
    refuses a place binding whose anchor was never resolved, so a
    partially-validated plan can never be written.

    Every offense is named (type and field) and reported together through
    :class:`CapabilityValidationError`; nothing partial is returned.
    """
    if entries is None:
        return CapabilityPlan()
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        raise CapabilityValidationError(["components must be a sequence of entries"])
    issues: list[str] = []
    seen: set[str] = set()
    planned: list[PlannedCapability] = []
    for index, entry in enumerate(entries):
        type_key, kwargs, raw_binding, entry_issues = _as_entry(entry, index, None)
        path = f"components[{index}]"
        if entry_issues:
            issues.extend(entry_issues)
            continue
        if not isinstance(type_key, str) or type_key not in COMPONENT_TYPES:
            issues.append(
                f"{path}.type {type_key!r} is outside the capability vocabulary "
                f"{sorted(COMPONENT_TYPES)}"
            )
            continue
        if type_key in seen:
            issues.append(
                f"{path}.type {type_key!r} is declared more than once; one entry "
                "per capability"
            )
            continue
        seen.add(type_key)
        if not isinstance(kwargs, Mapping):
            # The kwargs shape failure is already recorded; stop here so the
            # remaining checks never touch a non-mapping.
            issues.append(f"{path}.kwargs must be a mapping")
            continue
        _validate_kwargs(type_key, kwargs, path, issues)
        _validate_references(type_key, kwargs, path, issues)
        binding = _as_binding(raw_binding, path, issues)
        if binding is None and type_key in REQUIRED_BINDING:
            issues.append(
                f"{path} component {type_key!r} is a service and must declare its "
                "person or place binding"
            )
        anchor_room = None
        if binding is not None and binding.kind == "place" and room_resolver is not None:
            anchor_room = _resolve_room(binding.anchor_room or "", room_resolver, path, issues)
        planned.append(
            PlannedCapability(
                type=type_key,
                kwargs=MappingProxyType(dict(kwargs)),
                binding=binding,
                anchor_room=anchor_room,
            )
        )
    if issues:
        raise CapabilityValidationError(issues)
    return CapabilityPlan(tuple(planned))


def assemble_capabilities(
    entity: Any, plan: CapabilityPlan, *, reconcile: bool = False
) -> list[str]:
    """Attach and configure one complete validated plan onto ``entity``.

    The plan is the only input: no profession row, no authored map, no
    inference. A capability already present keeps its slot (components are never
    duplicated); its authored configuration converges to the declaration. The
    availability binding and its anchor are written here and nowhere else.

    ``reconcile`` additionally removes every managed slot the plan no longer
    declares — the source-owned host's convergence — while a capability outside
    the managed vocabulary is never touched. Returns the type keys this call
    actually attached (an already-present slot contributes nothing).
    """
    if not isinstance(plan, CapabilityPlan):
        raise TypeError(
            f"assemble_capabilities requires a validated CapabilityPlan, got "
            f"{type(plan).__name__}"
        )
    holder = getattr(entity, "components", None)
    if holder is None:
        raise CapabilityValidationError(
            [f"{type(entity).__name__} cannot hold capability components"]
        )
    _revalidate_plan(plan)
    attached: list[str] = []
    for component in plan.components:
        component_class = COMPONENT_TYPES[component.type]
        if not holder.has(component_class.name):
            holder.add(component_class.create(entity, **dict(component.kwargs)))
            attached.append(component.type)
    for component in plan.components:
        component_class = COMPONENT_TYPES[component.type]
        live = holder.get(component_class.get_component_slot())
        if live is None:  # vocabulary class without a live slot (unreachable)
            continue
        # Every authored field converges, including the OPTIONAL ones: an
        # omitted optional value clears to its declared default, so a reused
        # host cannot keep a stale authored identity.
        for field in sorted(component_field_names(component.type)):
            if field in live._fields:
                setattr(live, field, component.kwargs.get(field))
        live.service_binding = None if component.binding is None else component.binding.kind
        live.anchor_room_id = (
            component.anchor_room.pk
            if component.binding is not None and component.binding.kind == "place"
            else None
        )
    if reconcile:
        declared = plan.type_keys()
        for type_key in sorted(managed_type_keys() - declared):
            slot = COMPONENT_TYPES[type_key].get_component_slot()
            live = holder.get(slot)
            if live is not None:
                holder.remove(live)
    return attached


def _revalidate_plan(plan: CapabilityPlan) -> None:
    """Re-run every shared invariant on a plan before it is written.

    :class:`CapabilityPlan` only guarantees vocabulary membership and
    uniqueness structurally, and both carriers are public classes, so assembly
    repeats the same checks the authored-entry validator applies: per-type
    kwargs, registry references, binding shape/requirement and a resolved place
    anchor. A hand-built plan fails here instead of reaching a component
    factory.
    """
    issues: list[str] = []
    for index, component in enumerate(plan.components):
        path = f"components[{index}]"
        if not isinstance(component.kwargs, Mapping):
            issues.append(f"{path}.kwargs must be a mapping")
            continue
        _validate_kwargs(component.type, component.kwargs, path, issues)
        _validate_references(component.type, component.kwargs, path, issues)
        binding = component.binding
        if binding is not None:
            if not isinstance(binding, Binding):
                issues.append(f"{path}.binding must be a Binding")
                continue
            raw_binding: dict[str, Any] = {"kind": binding.kind}
            if binding.anchor_room is not None:
                raw_binding["anchor_room"] = binding.anchor_room
            _as_binding(raw_binding, path, issues)
        if binding is None and component.type in REQUIRED_BINDING:
            issues.append(
                f"{path} component {component.type!r} is a service and must declare "
                "its person or place binding"
            )
        if (
            binding is not None
            and binding.kind == "place"
            and component.anchor_room is None
        ):
            issues.append(
                f"{path} component {component.type!r} is place-bound but its anchor "
                f"room {binding.anchor_room!r} was never resolved"
            )
    if issues:
        raise CapabilityValidationError(issues)


__all__ = [
    "BINDING_KINDS",
    "CapabilityDeclaration",
    "CapabilityPlan",
    "CapabilityValidationError",
    "COMPONENT_TYPES",
    "OPTIONAL_KWARGS",
    "PlannedCapability",
    "REQUIRED_BINDING",
    "REQUIRED_KWARGS",
    "RUNTIME_FIELDS",
    "assemble_capabilities",
    "Binding",
    "capability",
    "component_attribute_keys",
    "component_field_names",
    "managed_type_keys",
    "person_bound",
    "place_bound",
    "resolve_room",
    "validate_capabilities",
]
