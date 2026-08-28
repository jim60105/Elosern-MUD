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
        adapter: A callable ``adapter(actor, payload, session=None)`` that
            re-resolves every referenced identity, re-authorizes current domain
            state, and calls a public deterministic-core API. The dispatcher
            passes the authenticated session positionally as the third argument
            (never through signature introspection); a direct two-argument call
            stays valid through the default. The session is used only for
            per-session presentation targeting, never to read or write
            character state. Returns a JSON-safe result dict with ``outcome``,
            ``code``, and ``message``.
        affected_panels: The stable panel names this action may update, or an
            empty tuple to signal the coordinator to publish a full snapshot.
    """

    action_id: str
    validate_payload: Callable[[dict[str, Any]], dict[str, Any]]
    adapter: Callable[[Any, dict[str, Any], Any], dict[str, Any]]
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
    """Return the production action registry with the combat, service, creation,
    and exploration adapters.

    The registry contains exactly the three combat adapters (``combat.cast``,
    ``combat.flee``, ``combat.forfeit``), the seven service adapters
    (``guild.register``, ``guild.quest_accept``, ``guild.quest_abandon``,
    ``guild.quest_turnin``, ``guild.exam_start``, ``shop.buy``, ``shop.sell``),
    the five creation adapters (``creation.preset``, ``creation.custom``,
    ``creation.concept``, ``creation.activate``, ``creation.reset``), and the
    eight exploration adapters (``explore.move``, ``explore.look``,
    ``explore.talk_scripted``, ``explore.talk_freeform``, ``explore.party_invite``,
    ``explore.party_leave``, ``explore.engage``, ``explore.wait``), and the
    ``options.dismiss`` action. Each action
    binds one exact payload validator and one narrow deterministic adapter; no
    action routes through the text parser.
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
        _creation_concept_adapter,
        _creation_custom_adapter,
        _creation_preset_adapter,
        _creation_reset_adapter,
        validate_creation_activate_payload,
        validate_creation_concept_payload,
        validate_creation_custom_payload,
        validate_creation_preset_payload,
        validate_creation_reset_payload,
    )
    from web.webclient.actions.exploration_actions import (
        _engage_adapter,
        _look_adapter,
        _move_adapter,
        _party_invite_adapter,
        _party_leave_adapter,
        _talk_freeform_adapter,
        _talk_scripted_adapter,
        _wait_adapter,
        validate_engage_payload,
        validate_look_payload,
        validate_move_payload,
        validate_party_invite_payload,
        validate_party_leave_payload,
        validate_talk_freeform_payload,
        validate_talk_scripted_payload,
        validate_wait_payload,
    )
    from web.webclient.actions.options import (
        _dismiss_adapter,
        validate_options_dismiss_payload,
    )
    from web.webclient.actions.service_actions import (
        _buy_adapter,
        _exam_start_adapter,
        _guild_register_adapter,
        _inventory_toggle_equip_adapter,
        _inventory_use_adapter,
        _quest_abandon_adapter,
        _quest_accept_adapter,
        _quest_turnin_adapter,
        _sell_adapter,
        validate_buy_payload,
        validate_exam_start_payload,
        validate_guild_register_payload,
        validate_inventory_toggle_equip_payload,
        validate_inventory_use_payload,
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
            affected_panels=("status", "context_actions", "art"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="combat.flee",
            validate_payload=validate_flee_payload,
            adapter=_flee_adapter,
            affected_panels=("status", "context_actions", "art"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="combat.forfeit",
            validate_payload=validate_forfeit_payload,
            adapter=_forfeit_adapter,
            affected_panels=("status", "context_actions", "art"),
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
            action_id="inventory.use",
            validate_payload=validate_inventory_use_payload,
            adapter=_inventory_use_adapter,
            # No affected panels: an item use may change inventory, mirrors,
            # status, clock, and (in combat) mode, so every completion
            # publishes a full canonical snapshot (add-inventory-item-actions
            # D5).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="inventory.toggle_equip",
            validate_payload=validate_inventory_toggle_equip_payload,
            adapter=_inventory_toggle_equip_adapter,
            # No affected panels: the toggle changes inventory, character
            # equipment, and derived appraisal surfaces, published as one
            # full canonical snapshot.
            affected_panels=(),
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
            action_id="creation.concept",
            validate_payload=validate_creation_concept_payload,
            adapter=_creation_concept_adapter,
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
    registry.register(
        ActionSpec(
            action_id="explore.move",
            validate_payload=validate_move_payload,
            adapter=_move_adapter,
            # No affected panels: movement changes location, clock, map, header,
            # and shop/quest state together (design D3).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.look",
            validate_payload=validate_look_payload,
            adapter=_look_adapter,
            # Look changes no panel; the ordinary full-snapshot refresh keeps
            # the dock honest with the onboarding beat (design D4).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.talk_scripted",
            validate_payload=validate_talk_scripted_payload,
            adapter=_talk_scripted_adapter,
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.talk_freeform",
            validate_payload=validate_talk_freeform_payload,
            adapter=_talk_freeform_adapter,
            # Full snapshot so an applied intent (including a mode change)
            # refreshes atomically (design D5).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.party_invite",
            validate_payload=validate_party_invite_payload,
            adapter=_party_invite_adapter,
            # Full snapshot so an applied membership binding refreshes
            # atomically (party-core D-2).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.party_leave",
            validate_payload=validate_party_leave_payload,
            adapter=_party_leave_adapter,
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.engage",
            validate_payload=validate_engage_payload,
            adapter=_engage_adapter,
            affected_panels=("status", "context_actions"),
        )
    )
    registry.register(
        ActionSpec(
            action_id="explore.wait",
            validate_payload=validate_wait_payload,
            adapter=_wait_adapter,
            # No affected panels: a clock skip changes header, status, shop
            # hours, and quest deadlines together (design D7).
            affected_panels=(),
        )
    )
    registry.register(
        ActionSpec(
            action_id="options.dismiss",
            validate_payload=validate_options_dismiss_payload,
            adapter=_dismiss_adapter,
            # The completion publication is the single send: the adapter's
            # eviction is state-only, and the panel renders the session's
            # now-unavailable options state exactly once (design D1).
            affected_panels=("context_actions",),
        )
    )
    return registry
