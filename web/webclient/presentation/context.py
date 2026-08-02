"""Immutable read-only context handed to presenters.

A presenter receives only session-derived facts: the authenticated puppet and a
few read-only session observations. It never receives the raw Session, the
dispatcher, or the coordinator, so it cannot mutate presentation or game state.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PresentationContext:
    """One authenticated, read-only snapshot of presentation inputs.

    Attributes:
        actor: The active puppet object resolved from ``session.puppet``.
        protocol_version: The server protocol schema version in use.
        session_tag: An opaque ephemeral label for diagnostics only; it is
            never a client-controlled value and never persisted.
    """

    actor: Any
    protocol_version: int
    session_tag: str | None = field(default=None)
