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
    """Return the production action registry with the combat, service, and creation adapters.

    The registry contains exactly the three combat adapters (``combat.cast``,
    ``combat.flee``, ``combat.forfeit``), the seven service adapters
    (``guild.register``, ``guild.quest_accept``, ``guild.quest_abandon``,
    ``guild.quest_turnin``, ``guild.exam_start``, ``shop.buy``, ``shop.sell``),
    and the four creation adapters (``creation.preset``, ``creation.custom``,
    ``creation.activate``, ``creation.reset``). Each action binds one exact
    payload validator and one narrow deterministic adapter; no action routes
    through the text parser.
    """
    from web.webclient.actions.combat_actions import (
        _cast_adapter,
        _flee_adapter,
        _forfeit_adapter,
        validate_cast_payload,
        validate_flee_payload,
        validate_forfeit_payload,
    )
    from web.webclient.actions.creation_actions import (
        _creation_activate_adapter,
        _creation_custom_adapter,
        _creation_preset_adapter,
        _creation_reset_adapter,
        validate_creation_activate_payload,
        validate_creation_custom_payload,
        validate_creation_preset_payload,
        validate_creation_reset_payload,
    )
    from web.webclient.actions.service_actions import (
        _buy_adapter,
        _exam_start_adapter,
        _guild_register_adapter,
        _quest_abandon_adapter,
        _quest_accept_adapter,
        _quest_turnin_adapter,
        _sell_adapter,
        validate_buy_payload,
        validate_exam_start_payload,
        validate_guild_register_payload,
        validate_quest_abandon_payload,
        validate_quest_accept_payload,
        validate_quest_turnin_payload,
        validate_sell_payload,
    )

    registry = ActionRegistry("elosern")
    registry.register(
        ActionSpec(
            action_id="combat.cast",
            validate_payload=validate_cast_payload,
            adapter=_cast_adapter,
            affected_panels=("status", "context_actions"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="combat.flee",
            validate_payload=validate_flee_payload,
            adapter=_flee_adapter,
            affected_panels=("status", "context_actions"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="combat.forfeit",
            validate_payload=validate_forfeit_payload,
            adapter=_forfeit_adapter,
            affected_panels=("status", "context_actions"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="guild.register",
            validate_payload=validate_guild_register_payload,
            adapter=_guild_register_adapter,
            affected_panels=("status", "services"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="guild.quest_accept",
            validate_payload=validate_quest_accept_payload,
            adapter=_quest_accept_adapter,
            affected_panels=("services",),
        )
    )
    registry.register(
        ActionSpec(
            action_id="guild.quest_abandon",
            validate_payload=validate_quest_abandon_payload,
            adapter=_quest_abandon_adapter,
            affected_panels=("services",),
        )
    )
    registry.register(
        ActionSpec(
            action_id="guild.quest_turnin",
            validate_payload=validate_quest_turnin_payload,
            adapter=_quest_turnin_adapter,
            affected_panels=("status", "services"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="guild.exam_start",
            validate_payload=validate_exam_start_payload,
            adapter=_exam_start_adapter,
            affected_panels=("status", "services", "context_actions"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="shop.buy",
            validate_payload=validate_buy_payload,
            adapter=_buy_adapter,
            affected_panels=("status", "services"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="shop.sell",
            validate_payload=validate_sell_payload,
            adapter=_sell_adapter,
            affected_panels=("status", "services"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="creation.preset",
            validate_payload=validate_creation_preset_payload,
            adapter=_creation_preset_adapter,
            affected_panels=("creation",),
        )
    )
    registry.register(
        ActionSpec(
            action_id="creation.custom",
            validate_payload=validate_creation_custom_payload,
            adapter=_creation_custom_adapter,
            affected_panels=("creation",),
        )
    )
    registry.register(
        ActionSpec(
            action_id="creation.activate",
            validate_payload=validate_creation_activate_payload,
            adapter=_creation_activate_adapter,
            # No affected panels: activation publishes a full snapshot so the
            # exploration hand-off is atomic (design D5).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="creation.reset",
            validate_payload=validate_creation_reset_payload,
            adapter=_creation_reset_adapter,
            affected_panels=("creation",),
        )
    )
    return registry
