"""Truthful, spoiler-safe Traditional Chinese dream-dispatch status feedback.

The player sees ordinary game output, never a new story panel. Each durable
work state and each bounded failure reason has its own message, so a player can
tell a receipt from preparation, waiting, an executable arrangement and a
failure:

* nothing here names a future role, a hidden location or a plot outcome;
* nothing here claims an arrangement for readable prose -- only a durable
  ``arranged`` record, with every publication reference present, may say the
  direction has an executable arrangement, and even then it only says the
  *arrangement* exists and that the encounter still has to be met in the world;
* delivery resolves the saved owner's *current* legal actor, so a player who
  reconnects controlling a lawful companion is addressed through that actor and
  never through a stale one captured before generation;
* an ordinary notice may repeat after a reconnect (the module never promises
  exactly-once delivery). The committed effects are exactly-once through the
  durable work identity, not through the notice.
"""

from __future__ import annotations

from typing import Any

from world.narrative import dispatch
from world.observability import log_info, log_warn

__all__ = [
    "MESSAGE_ARRANGED",
    "MESSAGE_BY_REASON",
    "MESSAGE_FAILED",
    "MESSAGE_PREPARING",
    "MESSAGE_WAITING",
    "deliver_status",
    "owner_message",
    "status_message",
]

MESSAGE_PREPARING = "夢境方向已記下，正在準備中；這還不是成局。"
MESSAGE_WAITING = "夢境方向已記下，但目前缺少可用的準備服務，暫時無法開始。"
MESSAGE_ARRANGED = "這個夢境方向已經有了可執行的安排；實際的遭遇要由你在世界中自行遇上。"
MESSAGE_FAILED = "夢境方向無法成局；你仍可重新確認一個新的方向。"

#: One distinct, bounded, actionable reason per terminal failure code.
MESSAGE_BY_REASON: dict[str, str] = {
    dispatch.REASON_NO_CAPABILITY: MESSAGE_WAITING,
    dispatch.REASON_MODEL_UNAVAILABLE: "夢境方向暫時無法準備（服務沒有回應）；你仍可重新確認一個新的方向。",
    dispatch.REASON_INVALID_OUTPUT: "夢境方向無法成局（生成的內容不符合規範）；請調整方向後重新確認。",
    dispatch.REASON_UNSUPPORTED_EFFECT: "夢境方向要求的效果目前無法執行；請調整方向後重新確認。",
    dispatch.REASON_INSUFFICIENT_ARRANGEMENT: "夢境方向目前無法成為可執行的遭遇；請補上角色、地點或委託後重新確認。",
    dispatch.REASON_STALE_SOURCE: "夢境方向與你目前的處境已經不一致，請重新確認。",
    dispatch.REASON_CONFLICT: "夢境方向與既有的故事安排衝突，請調整方向後重新確認。",
    dispatch.REASON_PUBLICATION_FAILED: "夢境方向在成局時失敗，沒有留下任何安排；你仍可重新確認一個新的方向。",
    dispatch.REASON_EXECUTION_FAILED: "夢境方向在準備時失敗；你仍可重新確認一個新的方向。",
}

_TERMINAL_STATES = frozenset({dispatch.STATE_ARRANGED, dispatch.STATE_FAILED})


def status_message(work: Any) -> str:
    """One spoiler-safe message for one durable work record, or ``""``.

    An empty string means this record has nothing truthful to say (no work at
    all), and the caller then sends nothing rather than inventing a status.
    """
    if work is None:
        return ""
    state = str(work.state)
    if state == dispatch.STATE_ARRANGED:
        return MESSAGE_ARRANGED
    if state == dispatch.STATE_FAILED:
        return MESSAGE_BY_REASON.get(str(work.reason_code), MESSAGE_FAILED)
    if state == dispatch.STATE_WAITING_SERVICE:
        return MESSAGE_WAITING
    if state in _TERMINAL_STATES:  # pragma: no cover - closed vocabulary guard
        return ""
    return MESSAGE_PREPARING


def owner_message(owner_id: Any) -> str:
    """The latest durable status message for one saved owner, or ``""``."""
    return status_message(dispatch.latest_status(owner_id))


def current_owner_id(actor: Any) -> str:
    """The saved owner identity of the actor currently in lawful control.

    Possession changes control, not ownership: an account driving its own bound
    companion is still the owner the work belongs to, so its status reaches the
    session driving that actor.
    """
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    if possessed_by is not None:
        return str(possessed_by)
    return str(getattr(actor, "pk", ""))


def deliver_status(actor: Any) -> str:
    """Deliver the owner's latest durable status through ordinary output.

    Returns the delivered message (``""`` when there is nothing truthful to
    say). A delivery failure is reported and swallowed: a status notice may
    never cancel the committed action that triggered it.
    """
    if actor is None:
        return ""
    owner_id = current_owner_id(actor)
    message = owner_message(owner_id)
    if not message:
        return ""
    try:
        actor.msg(message)
    except Exception as error:
        log_warn(
            "dream_dispatch_status_failed",
            context={"owner": owner_id, "char": str(getattr(actor, "pk", ""))},
            exc=error,
        )
        return ""
    log_info(
        "dream_dispatch_status_delivered",
        context={
            "owner": owner_id,
            "char": str(getattr(actor, "pk", "")),
            "work_state": str(getattr(dispatch.latest_status(owner_id), "state", "")),
        },
    )
    return message
