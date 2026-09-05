"""Validate frozen import records structurally and against lore registries."""

from __future__ import annotations

import argparse
import importlib
import json
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

from world.art.subjects import (
    MAX_SUBJECT_KEY_BYTES,
    is_reserved_player_stable_key,
)
from world.imports.schema import CHARACTER_SCHEMA_V1, WORLD_SCHEMA_V1
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.rules.npc_identity import validate_npc_title


@dataclass(frozen=True)
class Issue:
    field: str
    message: str


@dataclass(frozen=True)
class DegradedCheck:
    name: str
    reason: str


@dataclass
class RecordReport:
    key: str
    path: Path | None = None
    record: dict[str, Any] | None = None
    rejections: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.rejections


@dataclass
class BatchReport:
    records: list[RecordReport]
    degraded_checks: list[DegradedCheck] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return all(record.is_valid for record in self.records)

    @property
    def character_records(self) -> list[dict[str, Any]]:
        return [
            report.record
            for report in self.records
            if report.is_valid
            and report.record is not None
            and report.record.get("record_type") == "character"
        ]


class RecordClassificationError(ValueError):
    """Raised when a record has no recognized discriminator."""


def classify_record(raw: dict[str, Any]) -> Literal["character", "world_entry"]:
    record_type = raw.get("record_type")
    if record_type in ("character", "world_entry"):
        return record_type
    key = raw.get("key", "<unknown>")
    raise RecordClassificationError(
        f"record {key!r} has record_type={record_type!r}; expected one of "
        "'character', 'world_entry'"
    )


def _field_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return path
    if error.validator == "required":
        return str(error.message.split("'")[1])
    return "<record>"


def _structural_issues(
    record: dict[str, Any], schema: dict[str, Any]
) -> list[Issue]:
    validator = Draft202012Validator(schema)
    return [
        Issue(_field_path(error), error.message)
        for error in sorted(validator.iter_errors(record), key=lambda item: list(item.path))
    ]


_DIGIT_ONLY_RESERVED_MESSAGE = (
    "digit-only entity keys are reserved for player characters "
    "(portrait stable-key collision)"
)


def _digit_only_key_issues(record: dict[str, Any]) -> list[Issue]:
    """Named rejection for the digit-only region reserved for player pks.

    Runs in the structural phase (``validate_character``/``validate_world_entry``
    append it alongside the schema issues): a digit-only key always fails the
    schema pattern, so without this check the named message would never reach
    the report once the semantic phase is skipped (fix-portrait-stable-key-
    collision D2).
    """
    key = record.get("key")
    if not isinstance(key, str):
        return []
    if is_reserved_player_stable_key(key):
        return [Issue("key", _DIGIT_ONLY_RESERVED_MESSAGE)]
    return []


def _check_npc_title(record: dict[str, Any]) -> list[Issue]:
    """Reject a title the shared NPC-title validator refuses.

    The structural phase already rejects a missing or non-string title; this
    semantic check owns everything the validator decides on the stripped form
    (empty, over the code-point bound, internal whitespace, control
    characters, the markup delimiter). The exception message is a stable
    English identifier (npc-identity-titles), so it becomes the Issue message
    verbatim. Deliberately catching ``ValueError``: ``NPCTitleError``
    subclasses it, and this conversion returns a diagnosis to the caller
    (rejecting the whole record), so it is not a silent swallow.
    """
    title = record.get("title")
    if not isinstance(title, str):
        return []
    try:
        validate_npc_title(title)
    except ValueError as error:
        return [Issue("title", str(error))]
    return []


def _check_entity_key_contract(record: dict[str, Any]) -> list[Issue]:
    """Mirror the shared art subject-key contract for imported entity keys.

    The schema pattern excludes the reserved separators, the 64-code-point
    bound, C0/DEL/C1 controls, and digit-only keys structurally; this check
    mirrors ``world.art.subjects._validate_subject_key``
    (fix-art-pipeline-contracts D1) for everything a regex cannot express:
    anything not ``isprintable()`` or in a Unicode ``C*`` category (format,
    surrogate, private-use etc.), and keys exceeding the UTF-8 byte bound so
    the worker output filename always stays within the filesystem name-length
    limit. The digit-only reservation (fix-portrait-stable-key-collision D2)
    mirrors the schema's negative lookahead through the shared predicate.
    """
    key = record.get("key")
    if not isinstance(key, str):
        return []
    reserved = _digit_only_key_issues(record)
    if reserved:
        return reserved
    for char in key:
        if not char.isprintable() or unicodedata.category(char).startswith("C"):
            return [
                Issue(
                    "key",
                    f"key {key!r} contains a non-printable or control character",
                )
            ]
    if len(key.encode("utf-8")) > MAX_SUBJECT_KEY_BYTES:
        return [
            Issue(
                "key",
                f"key {key!r} exceeds the {MAX_SUBJECT_KEY_BYTES}-byte UTF-8 bound",
            )
        ]
    return []


def _check_disguised_stats_subset(record: dict[str, Any]) -> list[Issue]:
    stat_keys = set(record.get("stats", {}))
    return [
        Issue(
            f"disguised_stats.{key}",
            f"{key!r} must also be present in stats",
        )
        for key in record.get("disguised_stats", {})
        if key not in stat_keys
    ]


def _check_race_subrace(record: dict[str, Any]) -> list[Issue]:
    race_key = record.get("race")
    if race_key not in RACE_REGISTRY:
        return [Issue("race", f"{race_key!r} not found in race registry")]
    subrace_key = record.get("subrace")
    if subrace_key is None or not isinstance(subrace_key, str) or not subrace_key:
        # Every race has at least one registered subrace and no player-facing
        # selection ever offers "none", so an imported character without a
        # subrace is a hard rejection
        # (fix-custom-creation-information-and-background D2).
        return [Issue("subrace", "a character requires a registered subrace")]
    subrace = SUBRACE_REGISTRY.get(subrace_key)
    if subrace is None:
        return [Issue("subrace", f"{subrace_key!r} not found in subrace registry")]
    if subrace.race_key != race_key:
        return [
            Issue(
                "subrace",
                f"{subrace_key!r} belongs to race {subrace.race_key!r}, not {race_key!r}",
            )
        ]
    return []


def _check_stats_band(record: dict[str, Any]) -> list[Issue]:
    race = RACE_REGISTRY.get(record.get("race"))
    if race is None:
        return []
    subrace = SUBRACE_REGISTRY.get(record.get("subrace"))
    vitals = {
        "hp": race.vital_baseline.hp,
        "mp": race.vital_baseline.mp,
        "sp": race.vital_baseline.sp,
    }
    if subrace and subrace.race_key == race.key and subrace.vital_overrides:
        vitals.update(subrace.vital_overrides)
    static = {
        "atk_phys": race.static_baseline.atk_phys,
        "agility": race.static_baseline.agility,
        "defense": race.static_baseline.defense,
        # ``magic_power`` is deliberately absent: its band is checked by
        # ``_check_magic_power_band``, which rejects above the ceiling and
        # warns below the floor.
    }
    warnings: list[Issue] = []
    for key, band in (*vitals.items(), *static.items()):
        value = record.get("stats", {}).get(key)
        if value is not None and not band[0] <= value <= band[1]:
            warnings.append(
                Issue(
                    f"stats.{key}",
                    f"{value} outside {race.key!r} {key} band {band}",
                )
            )
    return warnings


def _check_magic_power_band(
    record: dict[str, Any],
) -> tuple[list[Issue], list[Issue]]:
    """Reject magic_power above the race band; warn below it (D-A8).

    The race's ``static_baseline.magic_power`` upper bound is the hard
    mechanical maximum (the retired ``magic_cap`` number): a value above it
    rejects deterministically. A value below the lower bound warns exactly
    like the other static axes.
    """
    race = RACE_REGISTRY.get(record.get("race"))
    if race is None:
        return [], []
    value = record.get("stats", {}).get("magic_power")
    if value is None:
        return [], []
    band = race.static_baseline.magic_power
    rejections: list[Issue] = []
    warnings: list[Issue] = []
    if value > band[1]:
        rejections.append(
            Issue(
                "stats.magic_power",
                f"{value} exceeds {race.key!r} magic_power band {band}",
            )
        )
    elif value < band[0]:
        warnings.append(
            Issue(
                "stats.magic_power",
                f"{value} below {race.key!r} magic_power band {band}",
            )
        )
    return rejections, warnings


# Race-aware affinity input bounds (element-affinity-progression D3/D4): a
# single deterministic mapping shared with custom creation and the WebClient
# descriptor so the layers cannot drift.
_AFFINITY_INPUT_BOUNDS: dict[str, int] = {
    "human": 2,
    "beastfolk": 1,
    "elf": 0,
}


def _check_affinity_elements(record: dict[str, Any]) -> list[Issue]:
    """Reject an affinity set that violates registry or race-bound rules.

    The schema already constrains structural shape (enum, uniqueness, size).
    Semantically: every key must exist in ``ELEMENT_REGISTRY``, no duplicate,
    and the count must respect the race bound -- at most 2 for a human, at
    most 1 for a beastfolk, and none for an elf (an elf's affinity is
    subrace-derived, so an elf record must not supply the field at all, not
    even an empty array). A record without the field produces no rejection
    here.
    """
    race_key = record.get("race")
    if race_key == "elf" and "affinity_elements" in record:
        return [
            Issue(
                "affinity_elements",
                "an elf's affinity is subrace-derived; an elf record must not "
                "supply affinity_elements",
            )
        ]
    affinity = record.get("affinity_elements")
    if affinity is None:
        return []
    issues: list[Issue] = []
    seen: set[str] = set()
    for element in affinity:
        if element not in ELEMENT_REGISTRY:
            issues.append(
                Issue(
                    "affinity_elements",
                    f"unknown affinity element {element!r}",
                )
            )
        if element in seen:
            issues.append(
                Issue(
                    "affinity_elements",
                    f"duplicate affinity element {element!r}",
                )
            )
        seen.add(element)
    if race_key in _AFFINITY_INPUT_BOUNDS and len(affinity) > _AFFINITY_INPUT_BOUNDS[race_key]:
        bound = _AFFINITY_INPUT_BOUNDS[race_key]
        issues.append(
            Issue(
                "affinity_elements",
                f"affinity_elements exceeds the {race_key} bound of {bound} elements",
            )
        )
    return issues


def _resolve_skill_registry() -> Mapping[str, Any] | None:
    """Resolve forward-declared ``world.skills.registry.SKILL_REGISTRY``."""
    try:
        module = importlib.import_module("world.skills.registry")
    except ModuleNotFoundError as error:
        if error.name not in {"world.skills", "world.skills.registry"}:
            raise
        return None
    return module.SKILL_REGISTRY


def _check_skills(record: dict[str, Any]) -> list[Issue]:
    registry = _resolve_skill_registry()
    if registry is None:
        return []
    return [
        Issue(field_name, f"{key!r} not found in skill registry")
        for field_name in ("skills", "passives")
        for key in record.get(field_name, ())
        if key not in registry
    ]


def _is_npc_target(typeclass: type | None) -> bool:
    """Whether the load target assembles NPC components (default: NPC).

    ``None`` means the NPC-default caller (the CLI and every pre-existing
    record path); a PlayerCharacter target is any non-NPC living-entity class.
    """
    if typeclass is None:
        return True
    from typeclasses.npcs import NPC

    return issubclass(typeclass, NPC)


def _check_profession_fields(
    record: dict[str, Any], is_npc_target: bool
) -> list[Issue]:
    """Reject an incomplete or misplaced profession/components pair.

    Every rejection is decided from the record, the profession registry, and the
    component vocabulary alone, so the whole plan (blueprint expansion plus the
    authored identity kwargs) fails as a named ISSUE in the shared batch report
    BEFORE any entity is constructed. The loader re-runs the same
    ``assembly.resolve_plan`` fail-closed as its second gate.
    """
    profession_value = record.get("profession")
    entries = record.get("components")
    if profession_value is None:
        if entries:
            return [
                Issue(
                    "components",
                    "explicit components require a profession blueprint; the "
                    "assembly plan is defined only alongside a profession",
                )
            ]
        return []
    issues: list[Issue] = []
    if not is_npc_target:
        issues.append(
            Issue(
                "profession",
                "a PlayerCharacter-targeted record cannot declare a profession; "
                "professions assemble NPC components only",
            )
        )
    from world.imports import assembly
    from world.rules.profession_config import PROFESSION_COMPONENT_TYPES, get_profession

    profession = get_profession(profession_value)
    if profession is None:
        issues.append(
            Issue(
                "profession",
                f"unknown profession key '{profession_value}' is not a profession "
                "rulebook row",
            )
        )
    if entries is not None:
        seen: set[str] = set()
        for index, entry in enumerate(entries):
            type_key = entry["type"]
            if type_key not in PROFESSION_COMPONENT_TYPES:
                issues.append(
                    Issue(
                        f"components.{index}.type",
                        f"unknown component type '{type_key}' is outside the "
                        "profession component vocabulary",
                    )
                )
                continue
            if type_key in seen:
                issues.append(
                    Issue(
                        f"components.{index}.type",
                        f"duplicate component type '{type_key}'; one entry per "
                        "component slot",
                    )
                )
                continue
            seen.add(type_key)
            allowed = assembly.component_field_names(type_key)
            for kwarg in sorted(entry["kwargs"]):
                if kwarg not in allowed:
                    issues.append(
                        Issue(
                            f"components.{index}.kwargs",
                            f"component '{type_key}' accepts no kwarg '{kwarg}'; "
                            f"authored kwargs are {sorted(allowed)}",
                        )
                    )
    if profession is None or issues:
        return issues
    # Identity completeness on the FINAL resolved set: blueprint-only and
    # explicit-replacement components face the same non-empty identity rule
    # (the loader never invents a service anchor).
    for type_key, kwargs in assembly.resolve_plan(profession, record):
        missing = assembly.missing_identity_kwargs(type_key, kwargs)
        if missing:
            issues.append(
                Issue(
                    "components",
                    f"profession '{profession_value}' component '{type_key}' is "
                    f"missing authored identity kwargs {missing}",
                )
            )
    return issues


def _check_skill_proficiency_keys(record: dict[str, Any]) -> list[Issue]:
    """Reject explicit practice XP for unregistered skill keys.

    The lineage auto-seed normalizes the record before the semantic phase and
    seeds proficiency for registry keys only; a typo in an explicit
    ``skill_proficiency`` map would otherwise be silently dropped or silently
    persisted (use-driven-skill-lineage: imports are all-or-nothing, so a
    bad key must name itself and reject the whole record). Checked against
    the RAW record so normalization cannot hide it.
    """
    registry = _resolve_skill_registry()
    if registry is None:
        return []
    return [
        Issue("skill_proficiency", f"{key!r} not found in skill registry")
        for key in (record.get("skill_proficiency") or {})
        if key not in registry
    ]


def collect_degraded_checks() -> list[DegradedCheck]:
    checks: list[DegradedCheck] = []
    if _resolve_skill_registry() is None:
        checks.append(
            DegradedCheck(
                "skill-registry",
                "world.skills.registry.SKILL_REGISTRY is unavailable; skill-key "
                "checks are not enforced until skills-equipment lands",
            )
        )
    return checks


def _flag_duplicate_keys(
    reports: list[RecordReport],
    records: Sequence[dict[str, Any]],
    record_type: str,
    label: str,
) -> None:
    """Append a structural key-uniqueness issue to every valid matching report.

    Mirrors the world-entry scan for each record family so a duplicated
    character or world-entry key fails the whole batch (fix-import-key-validity
    D2). Only valid reports are flagged -- a record that already failed earlier
    checks stays rejected on its own grounds.
    """
    duplicate_keys = {
        key
        for key, count in Counter(record["key"] for record in records).items()
        if count > 1
    }
    for report in reports:
        if (
            report.is_valid
            and report.record
            and report.record.get("record_type") == record_type
            and report.record.get("key") in duplicate_keys
        ):
            report.rejections.append(
                Issue(
                    "key",
                    f"duplicate {label} key {report.record['key']!r} in batch",
                )
            )


def validate_character(
    record: dict[str, Any], typeclass: type | None = None
) -> RecordReport:
    report = RecordReport(str(record.get("key", "<unknown>")), record=record)
    report.rejections.extend(_structural_issues(record, CHARACTER_SCHEMA_V1))
    # The digit-only reservation is part of the structural phase: a digit-only
    # key always fails the schema pattern, so its named message is appended
    # here, before the semantic phase is skipped (fix-portrait-stable-key-
    # collision D2).
    report.rejections.extend(_digit_only_key_issues(record))
    if report.rejections:
        return report
    # Lineage auto-seed normalizes the record BEFORE the semantic phase: the
    # report (and therefore the loader) carries prerequisite-ownership closure
    # plus exact seeded proficiency (use-driven-skill-lineage DC6). Structural
    # schema validation ran on the raw record, so a malformed field still
    # rejects wholesale; explicit skill_proficiency entries always beat the
    # seed.
    from world.rules.progression import normalize_lineage_record

    # The raw record's explicit proficiency keys are validated verbatim: the
    # seed below only understands registered keys, so an unregistered one
    # must reject here instead of being dropped or persisted unchecked.
    report.rejections.extend(_check_skill_proficiency_keys(record))
    record = normalize_lineage_record(record)
    report.record = record
    report.rejections.extend(_check_entity_key_contract(record))
    report.rejections.extend(_check_npc_title(record))
    report.rejections.extend(_check_disguised_stats_subset(record))
    report.rejections.extend(_check_race_subrace(record))
    magic_rejections, magic_warnings = _check_magic_power_band(record)
    report.rejections.extend(magic_rejections)
    report.warnings.extend(magic_warnings)
    report.rejections.extend(_check_affinity_elements(record))
    report.rejections.extend(_check_skills(record))
    report.rejections.extend(
        _check_profession_fields(record, _is_npc_target(typeclass))
    )
    report.warnings.extend(_check_stats_band(record))
    return report


def validate_world_entry(record: dict[str, Any]) -> RecordReport:
    report = RecordReport(str(record.get("key", "<unknown>")), record=record)
    report.rejections.extend(_structural_issues(record, WORLD_SCHEMA_V1))
    # Same structural-phase placement as ``validate_character``: the named
    # digit-only reservation message must reach the report.
    report.rejections.extend(_digit_only_key_issues(record))
    if report.rejections:
        return report
    report.rejections.extend(_check_entity_key_contract(record))
    return report


def validate_batch(
    paths: list[Path], typeclass: type | None = None
) -> BatchReport:
    reports: list[RecordReport] = []
    character_records: list[dict[str, Any]] = []
    world_records: list[dict[str, Any]] = []
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("top-level JSON value must be an object")
            kind = classify_record(raw)
        except RecordClassificationError as error:
            reports.append(
                RecordReport(
                    key=path.stem,
                    path=path,
                    rejections=[Issue("record_type", str(error))],
                )
            )
            continue
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
        ) as error:
            reports.append(
                RecordReport(
                    key=path.stem,
                    path=path,
                    rejections=[Issue("<record>", str(error))],
                )
            )
            continue
        report = (
            validate_character(raw, typeclass)
            if kind == "character"
            else validate_world_entry(raw)
        )
        report.path = path
        reports.append(report)
        if report.is_valid:
            # The VALIDATED record carries the lineage auto-seed normalization
            # (use-driven-skill-lineage DC6); the loader instantiates exactly
            # what was validated, never the raw file content.
            (character_records if kind == "character" else world_records).append(
                report.record
            )

    _flag_duplicate_keys(reports, character_records, "character", "character")
    _flag_duplicate_keys(reports, world_records, "world_entry", "world-entry")
    return BatchReport(reports, collect_degraded_checks())


def render_report(report: BatchReport) -> str:
    lines: list[str] = []
    if report.degraded_checks:
        lines.extend(
            [
                "=" * 80,
                " DEGRADED VALIDATION -- the following checks are NOT being enforced:",
            ]
        )
        lines.extend(
            f"   * {check.name}: {check.reason}" for check in report.degraded_checks
        )
        lines.append("=" * 80)
    for record in report.records:
        location = str(record.path) if record.path else record.key
        lines.append(f"{'VALID' if record.is_valid else 'REJECT'} {record.key} ({location})")
        lines.extend(
            f"  REJECT {issue.field}: {issue.message}" for issue in record.rejections
        )
        lines.extend(
            f"  WARNING {issue.field}: {issue.message}" for issue in record.warnings
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    report = validate_batch(args.files)
    print(render_report(report))
    return 0 if report.all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
