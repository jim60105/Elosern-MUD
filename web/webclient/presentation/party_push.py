"""Party-panel fan-out for membership changes with no session context.

The party write seams reached from the webclient (``explore.party_invite``,
``explore.party_leave``, and the ordinary ``invite``/``leave`` commands)
already publish a full snapshot, which renders every registered panel
including ``party``. NPC deletion is the exception:
``world.rules.party.purge_npc_memberships`` runs from
``NPC.at_object_delete`` with no session context, so nothing would push and a
connected explorer would keep the dismissed companion in the last committed
``party`` panel until an unrelated sync.

This module closes that seam at the event layer (mirroring the ``art_push``
subscriber): the typeclass hook resolves the purged membership's owner and
defers :func:`push_party_update` through ``transaction.on_commit`` — the
established side-effect seam — so a rolled-back deletion never pushes a
removal that was undone or burns a presentation revision. The push re-renders
the panel from CURRENT canonical state for every live watching session and publishes an
epoch-guarded affected-panel ``ui_update``. Rendering after the purge
committed is what makes the deleted companion disappear — a late push can
only ever re-derive today's truth, never resurrect a stale row. Failures are
isolated per session and logged as bounded diagnostics; the next snapshot
re-establishes correctness regardless.
"""

from typing import Any

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_party_update"]


def push_party_update(player: Any) -> None:
    """Re-render and push the ``party`` panel to every live watcher of ``player``.

    Fire-and-forget by contract: a player with no live webclient watcher is a
    silent no-op, and one bad session never suppresses the others or raises
    into the deletion hook.
    """
    try:
        watchers = watchers_for(player)
    except Exception as error:
        log_warn(
            "party_push_watchers_failed",
            context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
            exc=error,
        )
        return
    if not watchers:
        return
    registry = build_production_registry()
    for session, epoch in watchers:
        try:
            context = build_presentation_context(session, player)
            payload = registry.render("party", context)
            publish_panel_update(
                session,
                player,
                {"party": payload},
                context=context,
                expected_epoch=epoch,
            )
        except Exception as error:
            log_warn(
                "party_push_failed",
                context={
                    "surface": "presentation",
                    "char": str(getattr(player, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=error,
            )
