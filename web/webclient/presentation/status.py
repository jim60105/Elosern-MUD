"""Version-1 read-only ``status`` panel presenter.

The presenter serializes the frozen status read model built by
``world.rules.status_query``. It never reads raw persistent records itself, never
calls ``get_display_value``, and never mutates canonical state.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.status_query import StatusQueryError, build_status_read_model

STATUS_SCHEMA_VERSION = 1


def status_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``status`` panel payload for the actor."""
    actor = context.actor
    try:
        model = build_status_read_model(actor)
    except StatusQueryError:
        raise PanelUnavailableError
    resources: dict[str, Any] = {}
    for key in ("hp", "mp", "sp"):
        gauge = model.resources[key]
        resources[key] = {"current": gauge.current, "maximum": gauge.maximum}
    conditions = []
    for condition in model.conditions:
        entry: dict[str, Any] = {
            "code": condition.code,
            "label": condition.label,
            "severity": condition.severity,
        }
        if condition.remaining_seconds is not None:
            entry["remaining_seconds"] = condition.remaining_seconds
        if condition.modifiers:
            entry["modifiers"] = condition.modifiers
        conditions.append(entry)
    actor_field: dict[str, Any] = {
        "name": model.actor_name,
        "identity": model.actor_identity,
    }
    if model.location_label is not None:
        actor_field["location"] = {
            "label": model.location_label,
            "identity": model.location_identity,
        }
    else:
        actor_field["location"] = None
    combat = None
    if model.combat_mode is not None:
        combat = {"mode": model.combat_mode, "round": model.combat_round}
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "available": True,
        "actor": actor_field,
        "resources": resources,
        "conditions": conditions,
        "disguise_active": model.disguise_active,
        "combat": combat,
    }
