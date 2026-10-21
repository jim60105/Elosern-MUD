"""Version-4 read-only ``status`` panel presenter.

The presenter serializes the frozen status read model built by
``world.rules.status_query``. It never reads raw persistent records itself, never
calls ``get_display_value``, and never mutates canonical state. Version 3 requires
condition provenance and preserves the optional composed ``actor.full_title``.
Version 4 adds the ``fatigue`` subject rows: the status source's own row, plus
the controlled body's distinct row under possession, so each physiological
subject is identified while the owner-keyed resources stay unchanged.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.status_query import (
    StatusQueryError,
    build_fatigue_subject,
    build_status_read_model,
)

STATUS_SCHEMA_VERSION = 4


def _fatigue_entry(row) -> dict[str, Any]:
    return {
        "identity": row.identity,
        "name": row.name,
        "reserve_percent": row.reserve_percent,
        "stage": row.stage,
        "label": row.label,
        "severity": row.severity,
        "restriction": row.restriction,
    }


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
        try:
            condition.provenance.validate()
        except (StatusQueryError, AttributeError, TypeError):
            raise PanelUnavailableError
        entry: dict[str, Any] = {
            "code": condition.code,
            "label": condition.label,
            "severity": condition.severity,
            "provenance": {
                "kind": condition.provenance.kind,
                "equipment_sources": [
                    {"item_key": source.item_key, "label": source.label}
                    for source in condition.provenance.equipment_sources
                ],
            },
        }
        if condition.remaining_seconds is not None:
            entry["remaining_seconds"] = condition.remaining_seconds
        if condition.modifiers:
            entry["modifiers"] = condition.modifiers
        conditions.append(entry)
    fatigue = [_fatigue_entry(row) for row in model.fatigue]
    controlled_identity = str(actor.pk)
    if controlled_identity != model.actor_identity:
        # The controlled body is a distinct physiological subject: append its
        # own row instead of relabelling the owner-keyed resources above.
        try:
            controlled = build_fatigue_subject(actor)
        except StatusQueryError:
            raise PanelUnavailableError
        fatigue.append(_fatigue_entry(controlled))
    actor_field: dict[str, Any] = {
        "name": model.actor_name,
        # Resources remain owner-keyed under possession; identity addresses
        # the session's controlled figure, not the source of those resources.
        "identity": str(actor.pk),
    }
    # The composed full title (fixed　epithet); the wire field is optional and
    # omitted when empty.
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
        "fatigue": fatigue,
        "disguise_active": model.disguise_active,
        "combat": combat,
    }
