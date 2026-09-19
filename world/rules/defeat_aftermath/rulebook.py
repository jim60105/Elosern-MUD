"""The defeat-aftermath rulebook: section registry and loader.

The ``DEFEAT_AFTERMATH_RULEBOOK`` constant loads the shipped YAML at
import (design D-C8): owned sections are validated fail-closed, unknown
sections are ignored with one warning.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
import yaml
from collections.abc import Callable
from pathlib import Path
from typing import Any

from world.observability import log_warn
from world.rules.defeat_aftermath.contracts import DefeatAftermathRulebook
from world.rules.defeat_aftermath.validation_core import (
    _validate_pg_lines,
    _validate_recovery,
    _validate_weak_debuff,
)
from world.rules.defeat_aftermath.validation_digest import _validate_digest
from world.rules.defeat_aftermath.validation_violation import _validate_violation

_DEFEAT_AFTERMATH_PATH = (
    Path(__file__).parent.parent / "rulebook" / "defeat_aftermath.yaml"
)


_SECTION_VALIDATORS: dict[str, Callable[[dict[str, Any], Path], Any]] = {}


def _register_section_validator(
    name: str, validator: Callable[[dict[str, Any], Path], Any]
) -> None:
    """Register one owned section's validator (design D-C8 seam)."""
    if name in _SECTION_VALIDATORS:
        raise ValueError(f"defeat-aftermath section validator {name!r} already registered")
    _SECTION_VALIDATORS[name] = validator


_register_section_validator("pg_lines", _validate_pg_lines)
_register_section_validator("weak_debuff", _validate_weak_debuff)
_register_section_validator("recovery", _validate_recovery)
_register_section_validator("violation", _validate_violation)
_register_section_validator("digest", _validate_digest)
_OWNED_SECTIONS = frozenset(_SECTION_VALIDATORS)


def load_defeat_aftermath_sections(path: Path) -> DefeatAftermathRulebook:
    """Load the defeat-aftermath rulebook, validating owned sections.

    Unknown sections belong to downstream changes and are ignored with one
    ``log_warn`` (design D-C8); each owned section is parsed by the validator
    registered for it in ``_SECTION_VALIDATORS``, and a malformed owned
    section fails closed at load like every other rulebook.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping of sections")
    unknown = sorted(str(key) for key in set(raw) - _OWNED_SECTIONS)
    if unknown:
        log_warn(
            "defeat_aftermath_unknown_section_ignored",
            context={"path": str(path), "sections": ", ".join(unknown)},
        )
    validated = {name: validator(raw, path) for name, validator in _SECTION_VALIDATORS.items()}
    return DefeatAftermathRulebook(
        pg_lines=validated["pg_lines"],
        weak_debuff_buff_key=validated["weak_debuff"],
        recovery=validated["recovery"],
        violation=validated["violation"],
        digest=validated["digest"],
    )


DEFEAT_AFTERMATH_RULEBOOK = load_defeat_aftermath_sections(_DEFEAT_AFTERMATH_PATH)
