"""Dialogue-panel fan-out for no-session-context clear seams (webclient-align-10).

The dialogue-session writer/clearer seams reached from a webclient action or
an ordinary text command already publish a full snapshot (or an
affected-panel update carrying ``dialogue``), so the committed mode and panel
follow the session atomically. NPC movement and deletion are the exception:
``NPC.at_post_move`` / ``at_object_delete`` clear every character session
naming the NPC through a ``transaction.on_commit`` callback with no session
context — nothing else would push, and a connected explorer would keep the
departed host's available ``dialogue`` panel (and dialogue mode) until an
unrelated snapshot.

This module closes that seam exactly like ``party_push``: for every session
the conditional clear actually retired, resolve the character's live watchers
and publish an epoch-guarded affected-panel ``ui_update`` re-rendered from
CURRENT canonical state (the panel degrades to the registered unavailable
form; the update carries the recomputed mode, so ``dialogue`` leaves the
presentation atomically with the clear). Rendering after the clear committed
is what makes the stale host disappear — a late push can only re-derive
today's truth. Fire-and-forget by contract: a cleared character with no live
watcher is a silent no-op; every failure is isolated per watcher and bounded-
logged so a callback exception never escapes the on-commit chain or suppresses
later watchers; correctness is re-established by the next snapshot regardless.
"""

from typing import Any

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_dialogue_update"]


def push_dialogue_update(player: Any) -> None:
    """Re-render and push the ``dialogue`` panel to every live watcher of ``player``.

    Fire-and-forget by contract: a player with no live webclient watcher is a
    silent no-op, and one bad session never suppresses the others or raises
    into the deferred clear callback.
    """
    try:
        watchers = watchers_for(player)
    except Exception as error:
        log_warn(
            "dialogue_push_watchers_failed",
            context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
            exc=error,
        )
        return
    if not watchers:
        return
    try:
        registry = build_production_registry()
    except Exception as error:
        # A registry-construction defect must degrade to a bounded diagnostic
        # (party_push precedent): raising from an on-commit callback would
        # surface in the caller and skip later commit callbacks.
        log_warn(
            "dialogue_push_failed",
            context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
            exc=error,
        )
        return
    for session, epoch in watchers:
        try:
            context = build_presentation_context(session, player)
            payload = registry.render("dialogue", context)
            publish_panel_update(
                session,
                player,
                {"dialogue": payload},
                context=context,
                expected_epoch=epoch,
            )
        except Exception as error:
            log_warn(
                "dialogue_push_failed",
                context={
                    "surface": "presentation",
                    "char": str(getattr(player, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=error,
            )
