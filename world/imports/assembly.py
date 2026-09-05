"""Record-facing profession-plan resolution shared by validation and the loader.

The exact plan a ``profession``/``components`` record pair resolves to is computed
once here so the batch validator can reject an incomplete plan BEFORE any entity
is constructed and the loader attaches exactly the plan validation approved
(design profession-import-assembly D-1: one assembly mechanism, no drift).

The component-identity vocabulary and the attach loop live in the shared
deterministic-core helper ``world.rules.profession_assembly`` (owned by the
declarative-service-hosts change), which both this module's plan resolution and
the guild-economy sync consult. This module keeps only the record-facing
pieces: indexing a record's explicit ``components`` entries and resolving a
record against a profession row.

This module performs no state change and touches no database.
"""

from __future__ import annotations

from typing import Any

from world.rules.profession_assembly import resolve_component_plan
from world.rules.profession_config import Profession


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
    """Resolve the record's ordered ``(type_key, kwargs)`` attach plan (design D5).

    The shared helper owns the algorithm; this seam only maps the record's
    explicit entries (blueprint minus explicit types — an explicit entry of the
    same type replaces the blueprint entry entirely, design D5).
    """
    return resolve_component_plan(profession, explicit_map(record))
