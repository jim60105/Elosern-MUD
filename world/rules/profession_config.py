"""Profession rulebook loader: assembly-time blueprints as authored game data.

A profession is an ASSEMBLY-TIME BLUEPRINT, never a runtime lens (design
``docs/superpowers/specs/2026-09-05-profession-registries-design.md`` D1):
after NPC construction the authoritative state is the NPC's component
instances and attributes; runtime gates read component fields, never this
table. This module validates ``world/rules/rulebook/professions.yaml`` as a
whole batch against the immutable lore registries and exposes the result as
frozen dataclasses through keyed reads, following the ``guild_config.py``
load/cache family.

``ProfessionComponent.default_binding`` is validated for vocabulary and stored
but intentionally NOT read by any runtime gate in this change; the
service-anchoring change is its first consumer (design D6 seam).
"""

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from typeclasses.components import (
    GuildExaminer,
    GuildStaff,
    Merchant,
    ScriptedDialogue,
)
from world.lore.races import STATIC_TIER_REGISTRY
from world.observability import log_info
from world.rules import npc_schedules

SCHEMA_VERSION = 1

#: Closed component-type vocabulary: authored YAML ``type`` keys to the
#: component classes declared in ``typeclasses/components.py``. The keys MUST
#: equal each class's declared ``name``; the contract test in
#: ``world/rules/tests/test_profession_config.py`` names any drift.
PROFESSION_COMPONENT_TYPES: dict[str, type] = {
    "guild_staff": GuildStaff,
    "guild_examiner": GuildExaminer,
    "merchant": Merchant,
    "scripted_dialogue": ScriptedDialogue,
}

#: Closed service-binding vocabulary (stored, not consumed; design D6).
SERVICE_BINDINGS = frozenset({"person", "place"})

_ROW_FIELDS = frozenset({"key", "components", "schedule_template", "default_tier"})
_COMPONENT_FIELDS = frozenset({"type", "default_binding"})


class ProfessionConfigError(ValueError):
    """The professions rulebook violates the load rules."""


def _error(message: str) -> ProfessionConfigError:
    return ProfessionConfigError(f"professions.yaml: {message}")


@dataclass(frozen=True)
class ProfessionComponent:
    """One assembled component instruction of a profession blueprint."""

    type_key: str
    default_binding: str


@dataclass(frozen=True)
class Profession:
    """Validated assembly blueprint for one authored profession."""

    key: str
    components: tuple[ProfessionComponent, ...]
    schedule_template: str | None
    default_tier: str | None


def _validate_component(entry: Any, key: str, position: int) -> ProfessionComponent:
    path = f"profession {key!r} components[{position}]"
    if not isinstance(entry, Mapping):
        raise _error(f"{path} must be a mapping, got {type(entry).__name__}")
    unknown = set(entry) - _COMPONENT_FIELDS
    if unknown:
        raise _error(f"{path} has unknown fields {sorted(unknown, key=repr)}")
    missing = _COMPONENT_FIELDS - set(entry)
    if missing:
        raise _error(f"{path} is missing fields {sorted(missing, key=repr)}")
    type_key = entry["type"]
    if not isinstance(type_key, str) or type_key not in PROFESSION_COMPONENT_TYPES:
        raise _error(f"{path} has unknown component type {type_key!r}")
    binding = entry["default_binding"]
    if not isinstance(binding, str) or binding not in SERVICE_BINDINGS:
        raise _error(
            f"{path} has default_binding {binding!r} outside {sorted(SERVICE_BINDINGS)}"
        )
    return ProfessionComponent(type_key=type_key, default_binding=binding)


def _validate_row(raw: Any, position: int, seen: set[str]) -> Profession:
    if not isinstance(raw, Mapping):
        raise _error(f"professions[{position}] must be a mapping, got {type(raw).__name__}")
    unknown = set(raw) - _ROW_FIELDS
    if unknown:
        raise _error(f"professions[{position}] has unknown fields {sorted(unknown, key=repr)}")
    missing = _ROW_FIELDS - set(raw)
    if missing:
        raise _error(f"professions[{position}] is missing fields {sorted(missing, key=repr)}")
    key = raw["key"]
    if not isinstance(key, str) or not key:
        raise _error(f"professions[{position}] has empty or non-string key {key!r}")
    if key in seen:
        raise _error(f"duplicate profession key {key!r}")
    seen.add(key)

    raw_components = raw["components"]
    if not isinstance(raw_components, list) or not raw_components:
        raise _error(f"profession {key!r} components must be a non-empty list")
    components = tuple(
        _validate_component(entry, key, position) for position, entry in enumerate(raw_components)
    )

    template = raw["schedule_template"]
    if template is not None:
        if not isinstance(template, str) or npc_schedules.get_rulebook().template_by_key(template) is None:
            raise _error(f"profession {key!r} has unknown schedule_template {template!r}")

    tier = raw["default_tier"]
    if tier is not None and (not isinstance(tier, str) or tier not in STATIC_TIER_REGISTRY):
        raise _error(f"profession {key!r} has unknown default_tier {tier!r}")

    return Profession(
        key=key,
        components=components,
        schedule_template=template,
        default_tier=tier,
    )


def load_professions(path: Path | None = None) -> dict[str, Profession]:
    """Load and validate the whole professions rulebook, failing closed.

    Every deviation -- unreadable file, unknown schema, malformed row or
    component, duplicate key, or a reference outside the schedule-template
    rulebook, the static-tier registry, or the component/
    ``default_binding`` vocabularies -- raises :class:`ProfessionConfigError`
    naming the offense, and the result is returned only after the entire file
    validated; nothing partial is ever produced or cached. ``path`` overrides
    the canonical rulebook location for tests.
    """
    rulebook_path = Path(__file__).parent / "rulebook" / "professions.yaml" if path is None else path
    try:
        text = rulebook_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _error(f"cannot read {rulebook_path}: {exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise _error(f"invalid YAML: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    raw = dict(raw)
    top_level_fields = {"schema_version", "professions"}
    unknown = set(raw) - top_level_fields
    if unknown:
        raise _error(f"unknown top-level fields {sorted(unknown, key=repr)}")
    missing = top_level_fields - set(raw)
    if missing:
        raise _error(f"missing top-level fields {sorted(missing, key=repr)}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise _error(f"schema_version must be {SCHEMA_VERSION}, got {raw['schema_version']!r}")
    raw_professions = raw["professions"]
    if not isinstance(raw_professions, list) or not raw_professions:
        raise _error("professions must be a non-empty list")
    seen: set[str] = set()
    table = {
        profession.key: profession
        for profession in (
            _validate_row(entry, position, seen) for position, entry in enumerate(raw_professions)
        )
    }
    return table


TABLE: Mapping[str, Profession] | None = None


def get_profession(key: str) -> Profession | None:
    """Return the frozen profession for ``key``, or ``None``.

    Loads the rulebook on first use. The cached table is an immutable mapping;
    keyed reads never expose a mutable view.
    """
    global TABLE
    if TABLE is None:
        TABLE = MappingProxyType(load_professions())
    return TABLE.get(key)


def all_professions() -> tuple[Profession, ...]:
    """Return every profession in rulebook declaration order."""
    global TABLE
    if TABLE is None:
        TABLE = MappingProxyType(load_professions())
    return tuple(TABLE.values())


def load_professions_into_cache() -> Mapping[str, Profession]:
    """Rebuild ``TABLE`` from the canonical rulebook file.

    Startup wiring seam (exercised by tests in this change); validation
    failures propagate before the cache is reassigned, so a bad file never
    replaces a good table.
    """
    global TABLE
    table = load_professions()
    TABLE = MappingProxyType(table)
    log_info(
        "profession_rulebook_loaded",
        context={"count": len(table), "keys": sorted(table)},
    )
    return TABLE
