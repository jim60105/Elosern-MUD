"""Shared combat-result rendering for Telnet commands and WebClient adapters.

Both paths map one facade settlement to stable Traditional Chinese messages and
emit every committed EventLog through Evennia's ordinary escaped text output
path. OOB results carry only bounded outcome/code/message data and never prose
or EventLogs; the WebClient browser does not parse narrative to update state.
"""

from typing import Any

from world.rules.action import RejectReason
from world.rules.event_log import render_plain_text
from world.rules.player_messages import (
    rejection_message,
    terminal_outcome_message,
)

# Stable OOB result codes for nonterminal round outcomes.
_ROUND_CODES = frozenset({"round", "continue"})
CONTINUE_MESSAGE = "行動完成，繼續戰鬥。"


def settle_to_messages(result: dict[str, Any]) -> tuple[tuple[str, ...], str]:
    """Return ``(narrative_lines, terminal_message)`` for one facade settlement.

    Every committed EventLog is rendered as ordinary text; a rejected result
    produces no fabricated combat prose. The terminal announcement uses the
    stable shared mapping.
    """
    if result["outcome"] == "rejected":
        reason = result.get("reason")
        message = (
            rejection_message(reason)
            if isinstance(reason, RejectReason)
            else "這項行動無法完成。"
        )
        return (), message
    lines = tuple(
        render_plain_text(event_log) for event_log in result.get("logs", ())
    )
    outcome = result["outcome"]
    if outcome in _ROUND_CODES:
        return lines, CONTINUE_MESSAGE
    return lines, terminal_outcome_message(outcome)


# The panels an admitted combat action may update after settlement. The art
# panel is included so a combat result that changes the participant roster or
# session state replaces the portrait catalog in the same ui_update.
AFFECTED_PANELS = ("status", "context_actions", "art")


def settle_to_oob_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert one facade settlement into a bounded OOB result dict.

    The result names only the stable code and a safe Traditional Chinese
    message; no narrative prose or EventLog leaves the structured channel. A
    rejected settlement maps its exact stable rejection reason. Success
    declares the affected panels so the dispatcher publishes canonical ``status``
    and ``context_actions`` replacements before unlocking the browser.

    A terminal settlement declares an empty affected-panel set, which the
    dispatcher interprets as a full-snapshot publication: the mode flips back
    to exploration, so every mode-relevant panel (exploration, character,
    services, local_map, status, context_actions, art) must be replaced with
    post-settlement canonical state. Non-terminal rounds keep the small
    three-panel update.
    """
    if result["outcome"] == "rejected":
        reason = result.get("reason")
        code = reason.value if isinstance(reason, RejectReason) else "rejected"
        message = (
            rejection_message(reason)
            if isinstance(reason, RejectReason)
            else "這項行動無法完成。"
        )
        return {"outcome": "rejected", "code": code, "message": message}
    outcome = result["outcome"]
    if outcome in _ROUND_CODES:
        return {
            "outcome": "success",
            "code": "round",
            "message": CONTINUE_MESSAGE,
            "affected_panels": AFFECTED_PANELS,
        }
    return {
        "outcome": "success",
        "code": outcome,
        "message": terminal_outcome_message(outcome),
        "affected_panels": (),
    }


def emit_narrative(actor: Any, result: dict[str, Any]) -> None:
    """Deliver every committed EventLog through the ordinary escaped text path.

    The caller (adapter) uses the bounded OOB result for the browser while the
    narrative stays authoritative on the text channel. A rejected settlement
    emits nothing so no fabricated combat prose appears.
    """
    if result["outcome"] == "rejected":
        return
    for event_log in result.get("logs", ()):
        actor.msg(render_plain_text(event_log))


def emit_settlement(actor: Any, result: dict[str, Any]) -> None:
    """Deliver every committed EventLog and the terminal message as ordinary text.

    Unlike :func:`emit_narrative`, this also announces the stable terminal
    message (``繼續戰鬥。`` for a nonterminal round, or the shared outcome
    announcement for a finished session). The WebClient adapters use it so the
    text channel carries the same outcome prose as the Telnet command path; a
    rejected settlement emits nothing.
    """
    if result["outcome"] == "rejected":
        return
    lines, terminal = settle_to_messages(result)
    for line in lines:
        actor.msg(line)
    actor.msg(terminal)


__all__ = [
    "CONTINUE_MESSAGE",
    "settle_to_messages",
    "settle_to_oob_result",
    "emit_narrative",
    "emit_settlement",
]
