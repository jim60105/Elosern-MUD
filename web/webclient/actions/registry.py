"""Allowlisted UI action registry (foundation section 2.1).

The action registry binds each stable action ID to one exact payload validator
and one adapter. Duplicate registration fails, and unknown action IDs are never
routed into the text command parser. This foundation registers no production
game action; tests install an isolated proof adapter.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    _validate_identifier,
)


@dataclass(frozen=True)
class ActionSpec:
    """One registered action definition.

    Attributes:
        action_id: The stable lowercase dotted action identifier.
        validate_payload: A callable validating one exact action payload and
            returning a normalized dict (or raising on violation).
        adapter: A callable ``adapter(actor, payload)`` that re-resolves every
            referenced identity, re-authorizes current domain state, and calls
            a public deterministic-core API. Returns a JSON-safe result dict
            with ``outcome``, ``code``, and ``message``.
        affected_panels: The stable panel names this action may update, or an
            empty tuple to signal the coordinator to publish a full snapshot.
    """

    action_id: str
    validate_payload: Callable[[dict[str, Any]], dict[str, Any]]
    adapter: Callable[[Any, dict[str, Any]], dict[str, Any]]
    affected_panels: tuple[str, ...] = ()


class ActionRegistry:
    """A finite allowlist of stable action IDs with duplicate rejection."""

    def __init__(self, name: str = "actions") -> None:
        self.name = name
        self._specs: dict[str, ActionSpec] = {}

    def register(self, spec: ActionSpec) -> None:
        action_id = _validate_identifier(spec.action_id, "action_id")
        if action_id in self._specs:
            raise ProtocolValidationError(f"duplicate action registration {action_id!r}")
        self._specs[action_id] = spec

    @property
    def action_ids(self) -> frozenset[str]:
        return frozenset(self._specs)

    def spec(self, action_id: str) -> ActionSpec:
        try:
            return self._specs[action_id]
        except KeyError as error:
            raise KeyError(f"unknown action {action_id!r}") from error

    def validate_and_adapter(self, action_id: str):
        """Return ``(normalized_payload, adapter)`` after payload validation."""
        spec = self.spec(action_id)
        return spec, spec.adapter


def build_production_action_registry() -> ActionRegistry:
    """Return the production action registry with no gameplay adapters.

    The dispatcher and validation infrastructure remain available while every
    production adapter belongs to its later delivery unit.
    """
    return ActionRegistry("elosern")
