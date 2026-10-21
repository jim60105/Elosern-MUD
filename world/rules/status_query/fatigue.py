"""No-create physiological subject rows shared by status/member presentation.

Presentation must never materialize handlers or write physiology. This module
reads the stored reserve/posture through ``world.rules.fatigue``'s strict
reader and projects one bounded row per body: the member's own identity, the
display-only rounded reserve percent, the exact threshold stage, and the fixed
action-unavailability line when the body is asleep. The persisted exact units
remain the authority; the rounded percent never selects a stage.
"""

from typing import Any

from world.rules.fatigue import (
    PROJECTION_BUFF_KEYS,
    FatigueStateError,
    actions_allowed,
    fatigue_stage,
    read_fatigue_state,
    reserve_percent,
)
from world.rules.status_display import display_for

from .models import FatigueSubjectView, StatusQueryError

#: The fixed player-facing line a sleeping body's row carries. One string for
#: every read-only surface so presentation never invents a second wording.
SLEEP_RESTRICTION_MESSAGE = "沉睡中，無法行動"
#: The two stages with no registry row: normal physiology projects nothing,
#: and voluntary sleep projects no fatigue status (the posture itself forbids
#: actions). Their presentation labels live here, not in the rulebook.
NORMAL_STAGE_LABEL = "精神充沛"
SLEEPING_STAGE_LABEL = "沉睡"


def build_fatigue_subject(entity: Any) -> FatigueSubjectView:
    """Build one body's fatigue row or raise :class:`StatusQueryError`.

    A missing or malformed reserve/posture fails closed (the panel renders
    unavailable) instead of fabricating a full, awake body.
    """
    try:
        state = read_fatigue_state(entity)
    except FatigueStateError as error:
        raise StatusQueryError("fatigue state is unavailable") from error
    stage = fatigue_stage(state)
    projection_key = PROJECTION_BUFF_KEYS.get(stage)
    if projection_key is not None:
        display = display_for(projection_key)
        label, severity = display.label, display.severity
    elif stage.value == "sleeping":
        label, severity = SLEEPING_STAGE_LABEL, "informational"
    else:
        label, severity = NORMAL_STAGE_LABEL, "informational"
    return FatigueSubjectView(
        identity=str(entity.pk),
        name=str(getattr(entity, "key", "?")),
        reserve_percent=reserve_percent(state),
        stage=stage.value,
        label=label,
        severity=severity,
        restriction=None if actions_allowed(state) else SLEEP_RESTRICTION_MESSAGE,
    )
