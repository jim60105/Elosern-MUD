"""Typed authoring diagnostics and source locations.

Every failure the authoring layer reports is one of these values: a stable
machine code, the gate category it belongs to, the canonical source path, the
dotted field path and -- when the value came from YAML -- the one-based source
line and column. Callers (the game adapter and the editor service) map the code
to their own presentation; the core never owns wording policy.

Categories are the acceptance gates:

``structure``   the candidate cannot be loaded or written at all.
``semantic``    the candidate loads and saves but is unfinished map work.
``external``    the authoritative game-side external result is unusable.
``freshness``   the required generated artifact does not describe this world.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STRUCTURE = "structure"
SEMANTIC = "semantic"
EXTERNAL = "external"
FRESHNESS = "freshness"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """One-based line/column of an authored value in its source document."""

    line: int
    column: int

    def as_dict(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One typed authoring diagnostic."""

    code: str
    category: str
    message: str
    relative_path: str | None = None
    field_path: str = ""
    line: int | None = None
    column: int | None = None
    object_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "relative_path": self.relative_path,
            "field_path": self.field_path,
            "line": self.line,
            "column": self.column,
            "object_id": self.object_id,
        }


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """The deterministic order every diagnostic tuple is emitted in."""

    return (
        diagnostic.relative_path or "",
        diagnostic.line or 0,
        diagnostic.column or 0,
        diagnostic.field_path,
        diagnostic.code,
        diagnostic.message,
    )


def sorted_diagnostics(diagnostics) -> tuple[Diagnostic, ...]:
    return tuple(sorted(diagnostics, key=diagnostic_sort_key))


class AuthoringError(ValueError):
    """An authoring candidate was rejected; ``diagnostics`` names every fault."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        self.diagnostics = sorted_diagnostics(diagnostics)
        summary = "; ".join(
            f"{item.relative_path or '<input>'}:{item.field_path or '<document>'}: "
            f"{item.code}: {item.message}"
            for item in self.diagnostics
        )
        super().__init__(f"authoring candidate rejected: {summary}")


class RuntimeRejection(AuthoringError):
    """A validated authoring world cannot become a runtime snapshot."""
