"""Immutable read-only context handed to presenters.

A presenter receives only session-derived facts: the authenticated puppet and a
few read-only session observations. It never receives the raw Session, the
dispatcher, or the coordinator, so it cannot mutate presentation or game state.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class FrozenCard:
    """One deep-copied, immutable suggestion card for presentation reads.

    The write side (the trigger service) owns ``session.ndb.options_state``;
    the ingress snapshot factory deep-copies its displayed cards into these
    frozen representations so repeated renders of one snapshot are stable even
    if the async writer later replaces the session state object. ``params`` is
    a read-only mapping view over a fresh copy — never a shared mutable dict.
    """

    kind: str
    action_code: str
    label: str
    params: Mapping[str, Any]
    hint: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize the card into its exact wire object."""
        card: dict[str, Any] = {
            "kind": self.kind,
            "action_code": self.action_code,
            "label": self.label,
            "params": dict(self.params),
        }
        if self.hint is not None:
            card["hint"] = self.hint
        return card


@dataclass(frozen=True)
class OptionsSnapshot:
    """One immutable read of the session's options presentation state.

    Copied from ``session.ndb.options_state`` wherever a presentation context
    is built; presenters read only this snapshot, never the raw session.
    ``displayed`` is ``None`` (or an empty tuple) when no card set is current,
    and the tuple holds deep-copied :class:`FrozenCard` representations.
    """

    fingerprint: str | None
    status: str
    generation_token: int
    displayed: tuple[FrozenCard, ...] | None = None


@dataclass(frozen=True)
class PresentationContext:
    """One authenticated, read-only snapshot of presentation inputs.

    Attributes:
        actor: The active puppet object resolved from ``session.puppet``.
        protocol_version: The server protocol schema version in use.
        session_tag: An opaque ephemeral label for diagnostics only; it is
            never a client-controlled value and never persisted.
        options_state: The immutable session options snapshot (or ``None``);
            presenters render suggestions exclusively from it.
        options_fingerprint: The current read-only exploration situation
            fingerprint derived through the shared freshness derivation (or
            ``None`` when no exploration situation can be derived). The
            suggestions presenter requires every non-``unavailable`` snapshot
            fingerprint to equal this value, so a stale snapshot can never
            render after the situation changed.
    """

    actor: Any
    protocol_version: int
    session_tag: str | None = field(default=None)
    options_state: OptionsSnapshot | None = field(default=None)
    options_fingerprint: str | None = field(default=None)


__all__ = [
    "FrozenCard",
    "OptionsSnapshot",
    "PresentationContext",
]
