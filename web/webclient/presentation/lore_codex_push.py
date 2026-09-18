"""Lore-codex panel fan-out for new lore discovery reveals.

When a player discovers a new lore entry through ``record_lore_reveal``, the
coordinator pushes the updated ``lore_codex`` panel to every live watcher of
that player under the epoch guard. Fire-and-forget by contract: a player with
no live webclient watcher is a silent no-op, and one bad session never
suppresses the others or raises into the caller. The fan-out discipline
itself lives in :func:`web.webclient.presentation.push.make_panel_pusher`;
this shell keeps the seam and supplies the collaborators.
"""

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.push import PanelPushDeps, make_panel_pusher
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_lore_codex_update"]


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


push_lore_codex_update = make_panel_pusher("lore_codex", "lore_codex", _deps)