"""Exact ``title.accept`` / ``title.decline`` ballot-answer adapters.

The two actions answer the pending epithet nomination ballot with the
numbered choice only (ballots are never answered with free text). Each
validator enforces an exact bounded payload shape; each adapter calls only
the rules-layer ballot writers (``world.rules.titles.accept_epithet`` /
``decline_epithet_ballot``), maps their stable error surface to the stable
rejection codes below, and never assigns attributes directly. A successful
answer declares ``title_ballot`` affected so the completion publication
re-renders the (now empty) ballot panel immediately — the targeted-update
precedent set by ``options.dismiss``. The rejection messages mirror the
telnet ``title`` command surface (``commands/title.py``) verbatim so both
faces speak one line.
"""

from typing import Any

from world.rules.event_log import render_plain_text
from world.rules.titles import (
    MAX_BALLOT_CANDIDATES,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    accept_epithet,
    decline_epithet_ballot,
)

# The 1-based candidate choice bound mirrors the rules ballot cap.
TITLE_ACCEPT_MIN_INDEX = 1
TITLE_ACCEPT_MAX_INDEX = MAX_BALLOT_CANDIDATES

# Stable rejection codes and the Traditional Chinese lines shared with the
# telnet ``title`` command (commands/title.py _NO_BALLOT / _BAD_INDEX /
# _UNAVAILABLE).
NO_BALLOT_CODE = "no_pending_ballot"
NO_BALLOT_MESSAGE = "目前沒有待決的異名提名。"
INDEX_OUT_OF_RANGE_CODE = "index_out_of_range"
INDEX_OUT_OF_RANGE_MESSAGE = "沒有這個編號的提名。"
BALLOT_UNAVAILABLE_CODE = "ballot_unavailable"
BALLOT_UNAVAILABLE_MESSAGE = "你的稱號冊暫時無法閱讀。"

# Answering consumes the ballot; the targeted completion publication replaces
# the menu panel so it disappears immediately.
AFFECTED_BALLOT = ("title_ballot",)


class TitleActionError(ValueError):
    """A title ballot action payload violates its exact bounded schema."""


def validate_title_accept_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``title.accept`` payload (one 1..3 choice index)."""
    if not isinstance(payload, dict):
        raise TitleActionError("title.accept payload must be an object")
    if set(payload) != {"index"}:
        raise TitleActionError("title.accept requires exactly index")
    index = payload["index"]
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not TITLE_ACCEPT_MIN_INDEX <= index <= TITLE_ACCEPT_MAX_INDEX
    ):
        raise TitleActionError(
            "index must be an integer within "
            f"{TITLE_ACCEPT_MIN_INDEX}..{TITLE_ACCEPT_MAX_INDEX}"
        )
    return {"index": index}


def validate_title_decline_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``title.decline`` payload."""
    if not isinstance(payload, dict):
        raise TitleActionError("title.decline payload must be an object")
    if payload:
        raise TitleActionError("title.decline requires an empty payload")
    return {}


def _rejected(code: str, message: str) -> dict[str, Any]:
    return {"outcome": "rejected", "code": code, "message": message}


def _success(code: str, message: str, affected: tuple[str, ...]) -> dict[str, Any]:
    return {
        "outcome": "success",
        "code": code,
        "message": message,
        "affected_panels": affected,
    }


def _ballot_error(error: TitleBallotError) -> dict[str, Any]:
    """Map one stable ballot-answer error to its rejection result."""
    if error.reason is TitleBallotReason.NO_PENDING_BALLOT:
        return _rejected(NO_BALLOT_CODE, NO_BALLOT_MESSAGE)
    return _rejected(INDEX_OUT_OF_RANGE_CODE, INDEX_OUT_OF_RANGE_MESSAGE)


def _title_accept_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Adopt the numbered ballot candidate through the rules writer.

    The 1-based index is re-checked against the live ballot by
    ``accept_epithet`` (the payload bound is a client hygiene gate, not the
    authority). Malformed title state maps to the stable unavailable
    rejection and changes nothing.
    """
    del session
    try:
        display, banked = accept_epithet(actor, payload["index"])
    except TitleBallotError as error:
        return _ballot_error(error)
    except TitleDataError:
        return _rejected(BALLOT_UNAVAILABLE_CODE, BALLOT_UNAVAILABLE_MESSAGE)
    message = (
        f"你採納異名：{display}" if banked else f"你早已擁有異名：{display}"
    )
    actor.msg(message)
    return _success("accepted", message, AFFECTED_BALLOT)


def _title_decline_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Discard the ballot through the rules writer (starts the cooldown).

    The result message is the decline EventLog's rendered plain text — the
    exact line the telnet ``title decline`` shows.
    """
    del payload, session
    try:
        event_log = decline_epithet_ballot(actor)
    except TitleBallotError:
        # decline has one stable error surface: no pending ballot.
        return _rejected(NO_BALLOT_CODE, NO_BALLOT_MESSAGE)
    except TitleDataError:
        return _rejected(BALLOT_UNAVAILABLE_CODE, BALLOT_UNAVAILABLE_MESSAGE)
    message = render_plain_text(event_log)
    actor.msg(message)
    return _success("declined", message, AFFECTED_BALLOT)


__all__ = [
    "AFFECTED_BALLOT",
    "BALLOT_UNAVAILABLE_CODE",
    "BALLOT_UNAVAILABLE_MESSAGE",
    "INDEX_OUT_OF_RANGE_CODE",
    "INDEX_OUT_OF_RANGE_MESSAGE",
    "NO_BALLOT_CODE",
    "NO_BALLOT_MESSAGE",
    "TITLE_ACCEPT_MAX_INDEX",
    "TITLE_ACCEPT_MIN_INDEX",
    "TitleActionError",
    "validate_title_accept_payload",
    "validate_title_decline_payload",
]
