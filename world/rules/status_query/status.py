"""The compact ``status`` panel read-model builder.

``build_status_read_model`` assembles the frozen model once per read (design
D3) and presents exactly the conditions ``matched_combat_modifiers`` matches —
the same matches the breakdown composes its layers from — so the panel can
never show a condition combat did not apply.
"""

from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.status_display import display_for

from .assembly import _assemble
from .models import (
    _GAUGE_KEYS,
    ConditionValue,
    StatusQueryError,
    StatusReadModel,
)
from .readers import _read_attribute, _read_full_title


def build_status_read_model(entity: Any) -> StatusReadModel:
    """Build the frozen read model or raise :class:`StatusQueryError`.

    Requires exactly the HP, MP, and SP gauges; other required data that is
    missing or malformed also fails closed so the presenter shows unavailable
    rather than fabricating values.
    """
    assembly = _assemble(entity)
    conditions: list[ConditionValue] = []
    for buff_key, cache in assembly.buff_entries:
        definition_key = cache.get("definition_key")
        if not isinstance(definition_key, str) or definition_key not in BUFF_DEFINITIONS:
            raise StatusQueryError(f"buff {buff_key!r} has an unknown definition")
        display = display_for(definition_key)
        conditions.append(
            ConditionValue(
                code=definition_key,
                label=display.label,
                severity=display.severity,
                remaining_seconds=cache.get("remaining_seconds"),
                modifiers={},
            )
        )

    # Deterministic combat-modifier matches — the SAME matches the breakdown
    # composes from (D3: one assembly per read, no second evaluation path).
    for rule_id, adjustments in assembly.matches:
        display = display_for(rule_id)
        conditions.append(
            ConditionValue(
                code=rule_id,
                label=display.label,
                severity=display.severity,
                remaining_seconds=None,
                modifiers=dict(adjustments),
            )
        )

    combat = assembly.combat
    identity = str(entity.pk)
    location = getattr(entity, "location", None)
    return StatusReadModel(
        actor_name=str(getattr(entity, "key", "?")),
        actor_identity=identity,
        full_title=_read_full_title(entity),
        location_label=None if location is None else str(location.key),
        location_identity=None if location is None else str(location.pk),
        resources={key: assembly.gauges[key] for key in _GAUGE_KEYS},
        conditions=tuple(conditions),
        disguise_active=bool(_read_attribute(entity, "disguised_stats", default=None)),
        combat_mode=None if combat is None else combat[0],
        combat_round=None if combat is None else combat[1],
        creation_pending=bool(getattr(entity, "creation_pending", False)),
    )
