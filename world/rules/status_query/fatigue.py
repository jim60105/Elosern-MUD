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
    SleepPosture,
    actions_allowed,
    fatigue_stage,
    read_fatigue_state,
    read_optional_fatigue_state,
    reserve_percent,
)
from world.observability import log_debug
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
        asleep=state.posture is not SleepPosture.AWAKE,
    )


def _source_coordinates(location: Any) -> tuple[int, int] | None:
    coordinates = getattr(location, "coordinates", None)
    if (
        isinstance(coordinates, tuple)
        and len(coordinates) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in coordinates)
    ):
        return (coordinates[0], coordinates[1])
    return None


def present_fatigue_subjects(
    traveller: Any,
    known_identities: frozenset[str] = frozenset(),
) -> tuple[FatigueSubjectView, ...]:
    """Rows for the traveller's source-present party members, in scope order.

    Membership is the canonical traversal cohort
    (``travel_cost.source_present_members``), so presentation and movement
    can never disagree about who travels together. Identities already
    presented are skipped, and so is a member whose physiology was never
    constructed or does not read: only the status source and the controlled
    body are required, so one unreadable companion never blanks the panel.
    Nothing is written; reads use the strict non-creating reader.
    """
    from world.rules.travel_cost import source_present_members

    location = getattr(traveller, "location", None)
    if location is None:
        return ()
    seen = set(known_identities)
    rows: list[FatigueSubjectView] = []
    for member in source_present_members(traveller, location, _source_coordinates(location)):
        identity = str(getattr(member, "pk", ""))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        try:
            if read_optional_fatigue_state(member) is None:
                continue
            rows.append(build_fatigue_subject(member))
        except (FatigueStateError, StatusQueryError) as error:
            # An unreadable companion simply has no row; the required
            # owner/controlled rows still fail closed.
            log_debug(
                "status_fatigue_row_skipped",
                context={"char": identity, "traveller": str(getattr(traveller, "pk", ""))},
                exc=error,
            )
            continue
    return tuple(rows)
