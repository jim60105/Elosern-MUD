"""Exact ``title.*`` ballot-answer, equip, and epithet-removal adapters.

``title.accept`` / ``title.decline`` answer the pending epithet nomination
ballot with the numbered choice only (ballots are never answered with free
text). ``title.equip`` swaps one occupied slot for another banked entry
(kind + identifier, never an unequip), and ``title.remove`` deletes exactly
one banked epithet through the sole rules delete path; its confirmation step
is a UI card over the server-computed ``can_remove`` flag, and the gates are
re-validated by ``remove_epithet`` at execution. Each validator enforces an
exact bounded payload shape; each adapter calls only the rules-layer writers
(``world.rules.titles``) and never assigns attributes directly. A successful
answer declares its affected panels so the completion publication re-renders
them immediately — the targeted-update precedent set by ``options.dismiss``.
The rejection messages mirror the telnet ``title`` command surface
(``commands/title.py``) verbatim so both faces speak one line.
"""

from typing import Any

from world.rules.event_log import render_plain_text
from world.rules.title_view import TITLE_MAX_DISPLAY_CHARS
from world.rules.titles import (
    MAX_BALLOT_CANDIDATES,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
    accept_epithet,
    decline_epithet_ballot,
    equip_epithet,
    equip_fixed,
    remove_epithet,
)

# The 1-based candidate choice bound mirrors the rules ballot cap.
TITLE_ACCEPT_MIN_INDEX = 1
TITLE_ACCEPT_MAX_INDEX = MAX_BALLOT_CANDIDATES
# The equip/remove identifier bound mirrors the codex display cap (the same
# 64 the panel row and the JS validator mirror).
TITLE_IDENTIFIER_MAX_CODE_POINTS = TITLE_MAX_DISPLAY_CHARS

# Stable rejection codes and the Traditional Chinese lines shared with the
# telnet ``title`` command (commands/title.py _NO_BALLOT / _BAD_INDEX /
# _UNAVAILABLE / _REJECTED / the removal gate lines).
NO_BALLOT_CODE = "no_pending_ballot"
NO_BALLOT_MESSAGE = "目前沒有待決的異名提名。"
INDEX_OUT_OF_RANGE_CODE = "index_out_of_range"
INDEX_OUT_OF_RANGE_MESSAGE = "沒有這個編號的提名。"
BALLOT_UNAVAILABLE_CODE = "ballot_unavailable"
BALLOT_UNAVAILABLE_MESSAGE = "你的稱號冊暫時無法閱讀。"
EQUIP_REJECTED_CODE = "title_equip_rejected"
EQUIP_REJECTED_MESSAGE = "無法掛上該稱號。"
REMOVAL_UNKNOWN_CODE = "title_removal_target_unknown"
REMOVAL_UNKNOWN_MESSAGE = "無法移除該異名。"
REMOVAL_LAST_CODE = "title_last_epithet"
REMOVAL_LAST_MESSAGE = "至少需保留一個異名。"
REMOVAL_EQUIPPED_CODE = "title_equipped_unremovable"
REMOVAL_EQUIPPED_MESSAGE = "裝備中的異名無法移除，請先改掛其他異名。"

# Answering consumes the ballot; the targeted completion publication replaces
# the menu panel so it disappears immediately. The codex carries the 「提名中」
# tab, so every ballot answer refreshes it too; equip and removal always do.
AFFECTED_BALLOT = ("title_ballot", "title_codex")
AFFECTED_CODEX = ("title_codex",)
# Equipping re-renders the codex rows AND the character panel's full-title
# row (both describe the equipped pair); removal leaves slots untouched.
AFFECTED_EQUIP = ("title_codex", "character")


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


def validate_title_equip_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``title.equip`` payload (kind + identifier)."""
    if not isinstance(payload, dict):
        raise TitleActionError("title.equip payload must be an object")
    if set(payload) != {"kind", "identifier"}:
        raise TitleActionError("title.equip requires exactly kind/identifier")
    kind = payload["kind"]
    if kind not in ("fixed", "epithet"):
        raise TitleActionError("kind must be 'fixed' or 'epithet'")
    identifier = payload["identifier"]
    if not isinstance(identifier, str):
        raise TitleActionError("identifier must be a string")
    if not 1 <= sum(1 for _ in identifier) <= TITLE_IDENTIFIER_MAX_CODE_POINTS:
        raise TitleActionError(
            f"identifier must be 1..{TITLE_IDENTIFIER_MAX_CODE_POINTS} code points"
        )
    return {"kind": kind, "identifier": identifier}


def validate_title_remove_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact ``title.remove`` payload (one epithet display)."""
    if not isinstance(payload, dict):
        raise TitleActionError("title.remove payload must be an object")
    if set(payload) != {"display"}:
        raise TitleActionError("title.remove requires exactly display")
    display = payload["display"]
    if not isinstance(display, str):
        raise TitleActionError("display must be a string")
    if not 1 <= sum(1 for _ in display) <= TITLE_IDENTIFIER_MAX_CODE_POINTS:
        raise TitleActionError(
            f"display must be 1..{TITLE_IDENTIFIER_MAX_CODE_POINTS} code points"
        )
    return {"display": display}


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


def _title_equip_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Swap one occupied slot through the rules equip writers (swap-only).

    Unbanked/unknown/wrong-kind targets hit the single stable rejection that
    never enumerates candidates — the exact telnet ``_REJECTED`` line.
    """
    del session
    try:
        if payload["kind"] == "fixed":
            display = equip_fixed(actor, payload["identifier"])
        else:
            display = equip_epithet(actor, payload["identifier"])
    except TitleEquipError:
        return _rejected(EQUIP_REJECTED_CODE, EQUIP_REJECTED_MESSAGE)
    except TitleDataError:
        return _rejected(BALLOT_UNAVAILABLE_CODE, BALLOT_UNAVAILABLE_MESSAGE)
    message = (
        f"你掛上稱號：{display}"
        if payload["kind"] == "fixed"
        else f"你掛上異名：{display}"
    )
    actor.msg(message)
    return _success("equipped", message, AFFECTED_EQUIP)


def _removal_rejection(error: TitleRemovalError) -> dict[str, Any]:
    """Map one stable removal-gate error to its rejection result."""
    if error.reason is TitleRemovalReason.LAST_EPITHET:
        return _rejected(REMOVAL_LAST_CODE, REMOVAL_LAST_MESSAGE)
    if error.reason is TitleRemovalReason.EQUIPPED_UNREMOVABLE:
        return _rejected(REMOVAL_EQUIPPED_CODE, REMOVAL_EQUIPPED_MESSAGE)
    return _rejected(REMOVAL_UNKNOWN_CODE, REMOVAL_UNKNOWN_MESSAGE)


def _title_remove_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Delete one banked epithet through the sole rules delete path.

    The UI confirm card carries no server-side review state: the confirming
    dispatch IS the executing call, and ``remove_epithet`` re-validates both
    gates itself. The result message is the removal EventLog's rendered plain
    text — the exact line the telnet confirm shows.
    """
    del session
    try:
        event_log = remove_epithet(actor, payload["display"])
    except TitleRemovalError as error:
        return _removal_rejection(error)
    except TitleDataError:
        return _rejected(BALLOT_UNAVAILABLE_CODE, BALLOT_UNAVAILABLE_MESSAGE)
    message = render_plain_text(event_log)
    actor.msg(message)
    return _success("removed", message, AFFECTED_CODEX)


__all__ = [
    "AFFECTED_BALLOT",
    "AFFECTED_CODEX",
    "AFFECTED_EQUIP",
    "BALLOT_UNAVAILABLE_CODE",
    "BALLOT_UNAVAILABLE_MESSAGE",
    "EQUIP_REJECTED_CODE",
    "EQUIP_REJECTED_MESSAGE",
    "INDEX_OUT_OF_RANGE_CODE",
    "INDEX_OUT_OF_RANGE_MESSAGE",
    "NO_BALLOT_CODE",
    "NO_BALLOT_MESSAGE",
    "REMOVAL_EQUIPPED_CODE",
    "REMOVAL_EQUIPPED_MESSAGE",
    "REMOVAL_LAST_CODE",
    "REMOVAL_LAST_MESSAGE",
    "REMOVAL_UNKNOWN_CODE",
    "REMOVAL_UNKNOWN_MESSAGE",
    "TITLE_ACCEPT_MAX_INDEX",
    "TITLE_ACCEPT_MIN_INDEX",
    "TITLE_IDENTIFIER_MAX_CODE_POINTS",
    "TitleActionError",
    "validate_title_accept_payload",
    "validate_title_decline_payload",
    "validate_title_equip_payload",
    "validate_title_remove_payload",
]
