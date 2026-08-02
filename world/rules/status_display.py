"""Immutable status display metadata for buffs and combat-modifier rules.

The WebClient status presenter maps stable rule/buff IDs to Traditional Chinese
labels and severities through this registry. A coverage test requires every
currently displayable rule and buff to have exactly one entry so presentation
can never silently fall back to an unknown code.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import _RULES
from world.rules.rulebook.schema import load_rules


class MissingDisplayMetadataError(ValueError):
    """A displayable rule or buff lacks exactly one metadata entry."""


@dataclass(frozen=True)
class ConditionDisplay:
    """One stable display binding for a condition code."""

    code: str
    label: str
    severity: str


_SEVERITIES = {"beneficial", "informational", "warning", "harmful", "critical"}


def _build_display_metadata() -> dict[str, ConditionDisplay]:
    """Load the deterministic label/severity table for every displayable code.

    The table lives in ``rulebook/status_display.yaml`` and must cover exactly
    the current buff definition keys and combat-modifier rule IDs. Unknown
    entries and missing codes both fail closed at import time.
    """
    import yaml

    path = Path(__file__).parent / "rulebook" / "status_display.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a YAML list")
    metadata: dict[str, ConditionDisplay] = {}
    displayable = set(BUFF_DEFINITIONS) | {rule.id for rule in _RULES}
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry {position} must be a mapping")
        code = entry.get("code")
        label = entry.get("label")
        severity = entry.get("severity")
        if not isinstance(code, str) or not code:
            raise ValueError(f"{path}: entry {position} is missing code")
        if not isinstance(label, str) or not label:
            raise ValueError(f"{path}: entry {position} is missing label")
        if severity not in _SEVERITIES:
            raise ValueError(f"{path}: entry {position} has invalid severity")
        if code in metadata:
            raise ValueError(f"{path}: duplicate display code {code!r}")
        metadata[code] = ConditionDisplay(code, label, severity)

    missing = displayable - set(metadata)
    if missing:
        raise MissingDisplayMetadataError(
            f"missing status display metadata for {sorted(missing)}"
        )
    unknown = set(metadata) - displayable
    if unknown:
        raise MissingDisplayMetadataError(
            f"status display metadata for unknown codes {sorted(unknown)}"
        )
    return metadata


STATUS_DISPLAY: dict[str, ConditionDisplay] = _build_display_metadata()


def display_for(code: str) -> ConditionDisplay:
    """Return the immutable display metadata for a stable code."""
    try:
        return STATUS_DISPLAY[code]
    except KeyError as error:
        raise MissingDisplayMetadataError(f"unknown status display code {code!r}") from error
