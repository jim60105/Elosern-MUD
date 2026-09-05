"""Shared profession-component assembly for the import loader and the sync interpreter.

One attach mechanism, owned by the deterministic rules core so both
``world/imports/loader.py`` and ``world/rules/guild_economy.py`` converge on it
(AGENTS.md single-convention rule; design declarative-service-hosts D8/D9): a
profession row plus an authored ``{type_key: kwargs}`` map resolves to an
ordered attach plan, and the plan attaches through the component holder exactly
once per slot. This module performs no state change of its own beyond component
attachment on the entity handed to it and touches no database.

The identity-kwargs vocabulary moved here from ``world/imports/assembly.py``
so config-time roster validation and sync both consult the same field truth.
"""

from __future__ import annotations

from typing import Any, Mapping

from world.rules.profession_config import PROFESSION_COMPONENT_TYPES, Profession

# The identity kwargs a component cannot live without. An authored service host
# is anchored on these values; the blueprint shares only the component SHAPE, so
# every one of them must come from authored data (design profession-import-
# assembly D4: assembly never invents identity values).
_IDENTITY_KWARGS = frozenset({"service_id", "shop_key", "branch_key", "dialogue_key"})

# The availability-binding fields are ASSEMBLY-OWNED, not authored kwargs: the
# single writer copies them from the blueprint binding plus the caller's anchor
# room (service-anchoring D2). Keeping them out of the authored vocabulary is
# what makes "assembly is the only writer" structurally true.
_ASSEMBLY_BOUND_FIELDS = frozenset({"service_binding", "anchor_room_id"})


class ProfessionAssemblyError(ValueError):
    """A resolved attach plan lacks authored identity kwargs.

    ``missing`` maps each offending component type key to the sorted identity
    fields its kwargs fail to supply. Callers translate this into their own
    failure surface (the import loader names a batch issue; sync fails closed).
    """

    def __init__(self, missing: dict[str, list[str]]):
        self.missing = missing
        named = "; ".join(
            f"{type_key!r} missing {fields}" for type_key, fields in sorted(missing.items())
        )
        super().__init__(f"profession assembly cannot proceed: {named}")


def component_field_names(type_key: str) -> frozenset[str]:
    """Return the persistent DBField names the vocabulary class defines.

    The assembly-owned binding fields are excluded: authored kwargs (import
    records, roster projections) can never set them, only the assembly can.
    """
    component_class = PROFESSION_COMPONENT_TYPES[type_key]
    return frozenset(component_class._fields.keys()) - _ASSEMBLY_BOUND_FIELDS


def identity_fields(type_key: str) -> frozenset[str]:
    """Return the identity kwargs the class defines (intersection of both sets)."""
    return _IDENTITY_KWARGS & component_field_names(type_key)


def missing_identity_kwargs(type_key: str, kwargs: Mapping[str, Any]) -> list[str]:
    """Return the identity fields the authored kwargs fail to supply (sorted).

    An identity value must be a non-empty string; anything else counts as
    missing so a blank ``""`` can never anchor a service component.
    """
    return sorted(
        field
        for field in identity_fields(type_key)
        if not isinstance(kwargs.get(field), str) or not kwargs[field]
    )


def resolve_component_plan(
    profession: Profession, authored_map: Mapping[str, Mapping[str, Any]]
) -> list[tuple[str, dict[str, Any]]]:
    """Resolve the ordered ``(type_key, kwargs)`` attach plan (design D5).

    Blueprint entries keep declaration order; an authored entry of the same type
    replaces the blueprint entry entirely (kwargs come only from the authored
    map). Authored vocabulary entries the blueprint omits are appended in map
    order — authored entries assemble the component SET, not merely patch
    defaults.
    """
    plan: list[tuple[str, dict[str, Any]]] = []
    for component in profession.components:
        plan.append((component.type_key, dict(authored_map.get(component.type_key, {}))))
    blueprint_types = {component.type_key for component in profession.components}
    for type_key, kwargs in authored_map.items():
        if type_key not in blueprint_types:
            plan.append((type_key, dict(kwargs)))
    return plan


def project_row_kwargs(
    profession: Profession, service_id: str, authored_kwargs: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    """Project one roster row's flat authored kwargs onto each blueprint component.

    Every component receives EXACTLY its own identity fields: ``service_id``
    from the row's anchor only where the class defines it, every other identity
    field from the row's authored kwargs. A ``ScriptedDialogue`` therefore
    receives ``{"dialogue_key": ...}`` and never a stray ``service_id`` —
    reproducing the historical per-component kwargs shapes bit-for-bit.
    """
    projected: dict[str, dict[str, str]] = {}
    for component in profession.components:
        type_key = component.type_key
        fields = identity_fields(type_key)
        entry: dict[str, str] = {}
        if "service_id" in fields:
            entry["service_id"] = service_id
        for field in fields:
            if field != "service_id" and field in authored_kwargs:
                entry[field] = authored_kwargs[field]
        projected[type_key] = entry
    return projected


def plan_bindings(
    profession: Profession, authored_map: Mapping[str, Mapping[str, Any]]
) -> dict[str, str]:
    """Return each planned component type's availability binding.

    Blueprint rows carry the authored ``default_binding`` (validated
    vocabulary); a component an authored map ADDS beyond the blueprint has no
    blueprint row to read, so it takes the design-D1 default: co-presence
    (``person``) is the default and anchoring is the declared exception.
    """
    bindings = {
        component.type_key: component.default_binding
        for component in profession.components
    }
    for type_key in authored_map:
        bindings.setdefault(type_key, "person")
    return bindings


def assemble_profession_components(
    entity: Any,
    profession: Profession,
    authored_map: Mapping[str, Mapping[str, Any]],
    anchor_room: Any = None,
) -> list[str]:
    """Attach the profession's resolved plan onto ``entity``, fail-closed.

    Runs the same identity-gap check the batch validator ran, so a direct sync
    caller (no upstream validation) can never persist an identity-less
    component set: a gap raises :class:`ProfessionAssemblyError` BEFORE the
    first attach. The attach path is the component-holder pattern the guild
    service-host sync has always used — add the class only when the slot is
    free, so assembly never duplicates a component slot. Returns the type keys
    actually attached (an already-present slot contributes nothing).

    After attaching, the assembly converges the authored availability binding
    on EVERY planned component (new or pre-existing): ``service_binding`` from
    the blueprint row and ``anchor_room_id`` from ``anchor_room`` for
    ``place``-bound components — ``person`` components persist no anchor
    (design D1: an anchored person is an invalid combination). Binding and
    anchor are authored config re-converged from the blueprint, not runtime
    identity, so re-writing them for reused components is idempotent
    convergence and the never-rename/never-retitle contract is untouched.
    A ``place`` plan without an ``anchor_room`` raises: the caller failed to
    supply the anchor its blueprint declares.
    """
    plan = resolve_component_plan(profession, authored_map)
    missing = {
        type_key: missing_identity_kwargs(type_key, kwargs)
        for type_key, kwargs in plan
    }
    missing = {type_key: fields for type_key, fields in missing.items() if fields}
    if missing:
        raise ProfessionAssemblyError(missing)
    bindings = plan_bindings(profession, authored_map)
    if anchor_room is None and any(b == "place" for b in bindings.values()):
        raise ProfessionAssemblyError(
            {"profession": ["place-bound components require an anchor room"]}
        )
    attached: list[str] = []
    for type_key, kwargs in plan:
        component_class = PROFESSION_COMPONENT_TYPES[type_key]
        if not entity.components.has(component_class.name):
            entity.components.add(component_class.create(entity, **kwargs))
            attached.append(type_key)
    for type_key, _kwargs in plan:
        component = entity.components.get(
            PROFESSION_COMPONENT_TYPES[type_key].get_component_slot()
        )
        if component is None:  # vocabulary class without a live slot (unreachable)
            continue
        component.service_binding = bindings[type_key]
        component.anchor_room_id = (
            anchor_room.pk if bindings[type_key] == "place" else None
        )
    return attached
