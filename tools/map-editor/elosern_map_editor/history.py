"""Undo/redo for the current uninterrupted manual segment.

Each entry is one confirmed single-document operation with both round-trip
baselines: the presence/content before it and after it. An inverse is just
another single-document effect (undo of a creation removes the document, undo
of a removal recreates its retained exact bytes through the absence guard,
undo of a replacement restores the prior bytes), executed through the same
validation and writer as any command. The stacks move only after the inverse
is confirmed; a rejected, failed or uncertain inverse leaves them unchanged.

History belongs to one client segment (an in-memory id the page creates on
load): a command from another segment starts a new empty segment, so a
refreshed page, or a second tab, never inherits undo/redo. Adopting an
external change clears the history. The segment id is not a security boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .writer import ABSENT, CREATE, REMOVE, REPLACE, Effect


@dataclass(frozen=True, slots=True)
class Presence:
    """One document state: its fingerprint (or ``absent``) and its exact text."""

    fingerprint: str
    text: str | None

    @property
    def absent(self) -> bool:
        return self.fingerprint == ABSENT


@dataclass(frozen=True, slots=True)
class Entry:
    command: str
    document_id: str
    before: Presence
    after: Presence

    def _towards(self, source: Presence, target: Presence) -> tuple[Effect, str]:
        if target.absent:
            effect = Effect(REMOVE, self.document_id)
        elif source.absent:
            effect = Effect(CREATE, self.document_id, target.text)
        else:
            effect = Effect(REPLACE, self.document_id, target.text)
        return effect, source.fingerprint

    def undo_effect(self) -> tuple[Effect, str]:
        """The inverse effect and the presence it expects on disk."""

        return self._towards(self.after, self.before)

    def redo_effect(self) -> tuple[Effect, str]:
        return self._towards(self.before, self.after)


@dataclass
class History:
    segment: str | None = None
    undo_stack: list[Entry] = field(default_factory=list)
    redo_stack: list[Entry] = field(default_factory=list)

    def clear(self) -> None:
        """Forget the segment entirely (an adopted external change)."""

        self.segment = None
        self.undo_stack.clear()
        self.redo_stack.clear()

    def record(self, segment: str, entry: Entry) -> None:
        """Append one confirmed manual operation; a new segment starts empty."""

        if segment != self.segment:
            self.clear()
            self.segment = segment
        self.undo_stack.append(entry)
        self.redo_stack.clear()

    def top(self, direction: str, segment: str) -> Entry | None:
        if segment != self.segment:
            return None
        stack = self.undo_stack if direction == "undo" else self.redo_stack
        return stack[-1] if stack else None

    def confirm(self, direction: str) -> None:
        """Move the top entry after its inverse/redo was confirmed on disk."""

        if direction == "undo":
            self.redo_stack.append(self.undo_stack.pop())
        else:
            self.undo_stack.append(self.redo_stack.pop())

    def describe(self) -> dict[str, Any]:
        def head(entry: Entry | None, expected: str | None) -> dict[str, Any] | None:
            if entry is None:
                return None
            return {
                "command": entry.command,
                "document_id": entry.document_id,
                "expected_document_fingerprint": expected,
            }

        undo = self.undo_stack[-1] if self.undo_stack else None
        redo = self.redo_stack[-1] if self.redo_stack else None
        return {
            "segment": self.segment,
            "undo": head(undo, undo.after.fingerprint if undo else None),
            "redo": head(redo, redo.before.fingerprint if redo else None),
        }


__all__ = ["Entry", "History", "Presence"]
