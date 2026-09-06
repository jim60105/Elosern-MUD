"""Lore-codex panel fan-out for new lore discovery reveals.

When a player discovers a new lore entry through ``record_lore_reveal``, the
coordinator pushes the updated ``lore_codex`` panel to every live watcher of
that player under the epoch guard. Fire-and-forget by contract: a player with
no live webclient watcher is a silent no-op, and one bad session never
suppresses the others or raises into the caller.
"""

from typing import Any

from world.observability import log_warn

from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for

__all__ = ["push_lore_codex_update"]


def push_lore_codex_update(player: Any) -> None:
    """Re-render and push the ``lore_codex`` panel to every live watcher of ``player``.

    Fire-and-forget by contract: a player with no live webclient watcher is a
    silent no-op, and one bad session never suppresses the others or raises
    into the reveal transaction callback.
    """
    try:
        watchers = watchers_for(player)
    except Exception as error:
        log_warn(
            "lore_codex_push_watchers_failed",
            context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
            exc=error,
        )
        return
    if not watchers:
        return
    try:
        registry = build_production_registry()
    except Exception as error:
        log_warn(
            "lore_codex_push_failed",
            context={"surface": "presentation", "char": str(getattr(player, "pk", "?"))},
            exc=error,
        )
        return
    for session, epoch in watchers:
        try:
            context = build_presentation_context(session, player)
            payload = registry.render("lore_codex", context)
            publish_panel_update(
                session,
                player,
                {"lore_codex": payload},
                context=context,
                expected_epoch=epoch,
            )
        except Exception as error:
            log_warn(
                "lore_codex_push_failed",
                context={
                    "surface": "presentation",
                    "char": str(getattr(player, "pk", "?")),
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=error,
            )
