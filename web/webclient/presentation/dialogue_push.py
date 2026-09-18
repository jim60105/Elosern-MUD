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
The fan-out discipline itself lives in
:func:`web.webclient.presentation.push.make_panel_pusher`; this shell keeps
the seam and supplies the collaborators.
"""

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.push import PanelPushDeps, make_panel_pusher
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_dialogue_update"]


def _deps() -> PanelPushDeps:
    """Resolve the fan-out collaborators from this module's globals.

    Read per call so identity-based test patches on this module's names keep
    intercepting the shared factory body.
    """
    return PanelPushDeps(
        watchers_for=watchers_for,
        build_registry=build_production_registry,
        build_context=build_presentation_context,
        publish=publish_panel_update,
        log_warn=log_warn,
    )


push_dialogue_update = make_panel_pusher("dialogue", "dialogue", _deps)