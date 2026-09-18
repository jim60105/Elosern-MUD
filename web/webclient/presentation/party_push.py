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
re-establishes correctness regardless. The fan-out discipline itself lives in
:func:`web.webclient.presentation.push.make_panel_pusher`; this shell keeps
the seam and supplies the collaborators.
"""

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.push import PanelPushDeps, make_panel_pusher
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_party_update"]


def _deps() -> PanelPushDeps:
    """Resolve the fan-out collaborators from this module's globals.

    Read per call so ``patch.object(party_push, "watchers_for", ...)``,
    ``patch.object(party_push, "build_production_registry", ...)``, and
    ``patch.object(party_push, "log_warn", ...)`` keep intercepting the
    shared factory body.
    """
    return PanelPushDeps(
        watchers_for=watchers_for,
        build_registry=build_production_registry,
        build_context=build_presentation_context,
        publish=publish_panel_update,
        log_warn=log_warn,
    )


push_party_update = make_panel_pusher("party", "party", _deps)