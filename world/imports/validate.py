"""Validate frozen import records structurally and against lore registries."""

from __future__ import annotations

import argparse
import importlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

from world.imports.schema import CHARACTER_SCHEMA_V1, WORLD_SCHEMA_V1
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY


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
    if subrace_key is None:
        return []
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


def _check_magic_cap(record: dict[str, Any]) -> list[Issue]:
    race = RACE_REGISTRY.get(record.get("race"))
    magic_level = record.get("stats", {}).get("magic_level")
    if race is None or magic_level is None or magic_level <= race.magic_cap:
        return []
    return [
        Issue(
            "stats.magic_level",
            f"{magic_level} exceeds {race.key!r} magic cap {race.magic_cap}",
        )
    ]


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


def _check_world_entry_key_uniqueness(
    records: Sequence[dict[str, Any]],
) -> list[Issue]:
    counts = Counter(record["key"] for record in records)
    return [
        Issue("key", f"duplicate world-entry key {key!r} in batch")
        for key, count in counts.items()
        if key is not None and count > 1
    ]


def validate_character(record: dict[str, Any]) -> RecordReport:
    report = RecordReport(str(record.get("key", "<unknown>")), record=record)
    report.rejections.extend(_structural_issues(record, CHARACTER_SCHEMA_V1))
    if report.rejections:
        return report
    report.rejections.extend(_check_disguised_stats_subset(record))
    report.rejections.extend(_check_race_subrace(record))
    report.rejections.extend(_check_magic_cap(record))
    report.rejections.extend(_check_skills(record))
    report.warnings.extend(_check_stats_band(record))
    return report


def validate_world_entry(record: dict[str, Any]) -> RecordReport:
    report = RecordReport(str(record.get("key", "<unknown>")), record=record)
    report.rejections.extend(_structural_issues(record, WORLD_SCHEMA_V1))
    return report


def validate_batch(paths: list[Path]) -> BatchReport:
    reports: list[RecordReport] = []
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
            validate_character(raw)
            if kind == "character"
            else validate_world_entry(raw)
        )
        report.path = path
        reports.append(report)
        if kind == "world_entry" and report.is_valid:
            world_records.append(raw)

    duplicate_keys = {
        key
        for key, count in Counter(record["key"] for record in world_records).items()
        if count > 1
    }
    for report in reports:
        if (
            report.is_valid
            and report.record
            and report.record.get("record_type") == "world_entry"
            and report.record.get("key") in duplicate_keys
        ):
            report.rejections.append(
                Issue("key", f"duplicate world-entry key {report.record['key']!r} in batch")
            )
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
