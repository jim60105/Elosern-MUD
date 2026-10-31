"""The read-only ``travel.plan`` action.

``travel.plan`` is the browser's bounded route/preview query: it names a
destination cell inside the current revealed wilderness window, a pace and a
``stop_at_night`` intent, and returns the admitted sequential settlement
prediction as one private correlated result. It changes no location, clock,
knowledge, fatigue, quest or party state and never enters the text command
parser; the dispatcher's result-only completion path publishes it without a
panel.

Only the five stable domain codes of the approved design leave the adapter
(``plan_destination_outside_window``, ``plan_destination_unrevealed``,
``plan_unreachable``, ``plan_too_long``, ``plan_party_cannot_travel``).
Malformed payloads and mode refusals keep their existing dispatcher/action
codes, and an unexpected domain failure is logged and answered with
``plan_unreachable`` rather than an exception.
"""

from typing import Any

from web.webclient.presentation.protocol import MAX_SAFE_INTEGER, ProtocolValidationError
from world.observability import log_error
from world.rules.travel_plan import (
    PACES,
    PLAN_OUTSIDE_WINDOW,
    PLAN_PARTY_CANNOT_TRAVEL,
    PLAN_TOO_LONG,
    PLAN_UNREACHABLE,
    PLAN_UNREVEALED,
    TravelPlanRefused,
    plan_travel,
    read_travel_snapshot,
)

#: Existing actionable refusal for "not a wilderness exploration actor".
NOT_EXPLORING_CODE = "not_exploring"
NOT_EXPLORING_MESSAGE = "你不在野外探索中，無法規劃行程。"

CODE_SUCCESS = "travel.plan"
MESSAGE_SUCCESS = "已規劃行程。"

#: Stable zh-TW messages for the five domain refusals.
PLAN_MESSAGES: dict[str, str] = {
    PLAN_OUTSIDE_WINDOW: "目的地不在目前的視野範圍內。",
    PLAN_UNREVEALED: "你尚未探明那個地點。",
    PLAN_UNREACHABLE: "目前無法找到通往該處的路線。",
    PLAN_TOO_LONG: "那段路程太遠，無法一次規劃。",
    PLAN_PARTY_CANNOT_TRAVEL: "同行成員目前無法出發。",
}


def validate_travel_plan_payload(payload: Any) -> dict[str, Any]:
    """Validate the exact ``travel.plan`` payload and return its normalized form."""

    if not isinstance(payload, dict) or set(payload) != {
        "destination",
        "pace",
        "stop_at_night",
    }:
        raise ProtocolValidationError(
            "travel.plan requires exactly destination, pace and stop_at_night"
        )
    destination = payload["destination"]
    if not isinstance(destination, dict) or set(destination) != {"x", "y"}:
        raise ProtocolValidationError(
            "travel.plan destination must be exactly {x, y}"
        )
    for axis in ("x", "y"):
        value = destination[axis]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER
        ):
            raise ProtocolValidationError(
                f"travel.plan destination.{axis} must be a safe integer"
            )
    pace = payload["pace"]
    if not isinstance(pace, str) or pace not in PACES:
        raise ProtocolValidationError("travel.plan pace is not an admitted value")
    stop_at_night = payload["stop_at_night"]
    if not isinstance(stop_at_night, bool):
        raise ProtocolValidationError(
            "travel.plan stop_at_night must be a boolean"
        )
    return {
        "destination": {"x": destination["x"], "y": destination["y"]},
        "pace": pace,
        "stop_at_night": stop_at_night,
    }


def travel_plan_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Answer one bounded read-only travel plan; never raises to the client."""

    del session
    from typeclasses.rooms import TerrainRoom
    from web.webclient.presentation.affordances import in_exploration_mode

    location = getattr(actor, "location", None)
    if not in_exploration_mode(actor) or not isinstance(location, TerrainRoom):
        return {
            "outcome": "rejected",
            "code": NOT_EXPLORING_CODE,
            "message": NOT_EXPLORING_MESSAGE,
            "no_presentation": True,
        }
    destination = (payload["destination"]["x"], payload["destination"]["y"])
    try:
        snapshot = read_travel_snapshot(actor)
        plan = plan_travel(
            snapshot, destination, payload["pace"], payload["stop_at_night"]
        )
    except TravelPlanRefused as refusal:  # observability: ignore R2: the stable domain refusal IS the action result, not a swallowed failure
        return {
            "outcome": "rejected",
            "code": refusal.code,
            "message": PLAN_MESSAGES[refusal.code],
            "no_presentation": True,
        }
    except Exception as error:  # observability: ignore R2: the bounded plan_unreachable result IS the client-facing report; the log_error event below is its diagnostic surface
        log_error(
            "travel_plan_failed",
            context={"char": str(getattr(actor, "pk", "?"))},
            exc=error,
        )
        return {
            "outcome": "rejected",
            "code": PLAN_UNREACHABLE,
            "message": PLAN_MESSAGES[PLAN_UNREACHABLE],
            "no_presentation": True,
        }
    return {
        "outcome": "success",
        "code": CODE_SUCCESS,
        "message": MESSAGE_SUCCESS,
        "data": plan.as_data(),
        "affected_panels": (),
        "no_presentation": True,
    }


__all__ = [
    "CODE_SUCCESS",
    "NOT_EXPLORING_CODE",
    "NOT_EXPLORING_MESSAGE",
    "PLAN_MESSAGES",
    "travel_plan_adapter",
    "validate_travel_plan_payload",
]
