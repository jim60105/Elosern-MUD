"""Pure profession-assembly resolution shared by validation and the loader.

The exact plan a ``profession``/``components`` record pair resolves to is computed
once here so the batch validator can reject an incomplete plan BEFORE any entity
is constructed and the loader attaches exactly the plan validation approved
(design profession-import-assembly D-1: one assembly mechanism, no drift).

This module performs no state change and touches no database; the attach side
lives in ``world/imports/loader.py`` (``_apply_profession``), which re-runs
``resolve_plan`` fail-closed as the second gate, mirroring the NPC-title
pre-construction gate pattern.
"""

from __future__ import annotations

from typing import Any

from world.rules.profession_config import PROFESSION_COMPONENT_TYPES, Profession

# The identity kwargs a component cannot live without. An authored service host
# is anchored on these values; the blueprint shares only the component SHAPE, so
# every one of them must come from the record (design D4: the loader never
# invents identity values).
_IDENTITY_KWARGS = frozenset({"service_id", "shop_key", "branch_key", "dialogue_key"})


def component_field_names(type_key: str) -> frozenset[str]:
    """Return the persistent DBField names the vocabulary class defines."""
    component_class = PROFESSION_COMPONENT_TYPES[type_key]
    return frozenset(component_class._fields.keys())


def identity_fields(type_key: str) -> frozenset[str]:
    """Return the identity kwargs the class defines (intersection of both sets)."""
    return _IDENTITY_KWARGS & component_field_names(type_key)


def explicit_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the record's explicit ``components`` entries by type key.

    Duplicate types are a validation rejection upstream; a caller reaching this
    seam with a duplicate still gets a deterministic last-wins map, never an
    exception, so the loader gate cannot crash mid-transaction on shape issues
    the validator owns.
    """
    return {
        entry["type"]: dict(entry["kwargs"]) for entry in record.get("components") or []
    }


def resolve_plan(
    profession: Profession, record: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    """Resolve the ordered ``(type_key, kwargs)`` attach plan (design D5).

    Blueprint entries keep declaration order; an explicit entry of the same type
    replaces the blueprint entry entirely (kwargs come only from the record).
    Explicit vocabulary entries the blueprint omits are appended in record order
    — explicit entries assemble the component SET, not merely patch defaults.
    """
    explicit = explicit_map(record)
    plan: list[tuple[str, dict[str, Any]]] = []
    for component in profession.components:
        plan.append(
            (component.type_key, explicit.get(component.type_key, {}))
        )
    blueprint_types = {component.type_key for component in profession.components}
    for type_key, kwargs in explicit.items():
        if type_key not in blueprint_types:
            plan.append((type_key, kwargs))
    return plan


def missing_identity_kwargs(type_key: str, kwargs: dict[str, Any]) -> list[str]:
    """Return the identity fields the authored kwargs fail to supply (sorted).

    An identity value must be a non-empty string; anything else counts as
    missing so a blank ``""`` can never anchor a service component.
    """
    return sorted(
        field
        for field in identity_fields(type_key)
        if not isinstance(kwargs.get(field), str) or not kwargs[field]
    )
