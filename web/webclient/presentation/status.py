"""Version-2 read-only ``status`` panel presenter.

The presenter serializes the frozen status read model built by
``world.rules.status_query``. It never reads raw persistent records itself, never
calls ``get_display_value``, and never mutates canonical state. Version 2 adds the
optional ``actor.full_title`` row: the composed 稱號　異名 the client addresses
the player by, omitted entirely while both title slots are empty.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.status_query import StatusQueryError, build_status_read_model

STATUS_SCHEMA_VERSION = 2


def status_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``status`` panel payload for the actor."""
    actor = context.actor
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    status_source = actor
    if possessed_by is not None:
        from world.rules.possession import _resolve_live_object
        owner = _resolve_live_object(int(possessed_by))
        if owner is not None:
            status_source = owner
    try:
        model = build_status_read_model(status_source)
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
    # The composed full title (fixed　epithet); the wire field is optional and
    # omitted when empty, so a pre-creation character keeps the v1 shape
    # minus the version bump.
    if model.full_title:
        actor_field["full_title"] = model.full_title
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
