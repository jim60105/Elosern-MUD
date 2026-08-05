"""Targeted OOB art completion push (design D5).

A subscriber to the ``world.art`` ``asset_completed`` signal re-renders the
``art`` panel for every connected WebClient session whose current scene or
portrait catalog references the completed subject key, then publishes an
affected-panel ``ui_update`` at a newer revision through the session's
coordinator. The subscriber never runs on the worker thread (the signal is
emitted from the drain success callback on the reactor thread), never
propagates an exception back into ``world/art/``, and isolates one bad session
from the others.

Late completions for an old room or a no-longer-present entity re-derive from
current canonical state, so the rendered panel no longer references the subject
and nothing is published -- the "late completion never replaces the current
panel" rule is enforced by re-derivation, not by remembering what was sent.
"""

from typing import Any

from django.conf import settings

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import is_webclient
from web.webclient.presentation.protocol import PROTOCOL_VERSION
from web.webclient.presentation.registry import build_production_registry

# Stable per-subscriber identity so re-connecting from at_server_start is a
# re-entrant no-op.
DISPATCH_UID = "elosern.art_push"


def _subject_keys(payload: dict[str, Any]) -> set[str]:
    """Return the subject keys the rendered art payload references."""
    keys: set[str] = set()
    scene = payload.get("scene") or {}
    if scene.get("subject_key"):
        keys.add(scene["subject_key"])
    for entry in (payload.get("portrait_catalog") or {}).values():
        if entry.get("subject_key"):
            keys.add(entry["subject_key"])
    return keys


def _render_art_for_session(session: Any, actor: Any) -> dict[str, Any]:
    """Render the art panel for one live session's canonical state."""
    context = PresentationContext(actor=actor, protocol_version=PROTOCOL_VERSION)
    return build_production_registry().render("art", context)


def _push_for_subject(session: Any, actor: Any, subject_key: str) -> None:
    """Re-render and push the art panel only when it references the subject."""
    coordinator = attach_coordinator(session, build_production_registry())
    payload = _render_art_for_session(session, actor)
    if subject_key not in _subject_keys(payload):
        return
    if not payload.get("available"):
        return
    context = PresentationContext(actor=actor, protocol_version=PROTOCOL_VERSION)
    coordinator.panel_update(context, {"art": payload})


def on_asset_completed(**kwargs: Any) -> None:
    """Subscriber: push completed art to referencing WebClient sessions.

    The signal payload carries only ``subject_key``. Only live WebClient
    sessions with an attached coordinator and an active puppet are considered;
    every session is isolated so one bad session cannot stop notification to
    the others. Nothing here mutates canonical state.
    """
    subject_key = kwargs.get("subject_key")
    if not isinstance(subject_key, str) or not subject_key:
        return
    from evennia import SESSION_HANDLER

    for session in SESSION_HANDLER.get_sessions():
        try:
            if not is_webclient(session):
                continue
            actor = getattr(session, "puppet", None)
            if actor is None:
                continue
            coordinator = getattr(getattr(session, "ndb", None), "elosern_coordinator", None)
            if coordinator is None:
                continue
            _push_for_subject(session, actor, subject_key)
        except Exception:
            # A bad session logs a bounded diagnostic and cannot stop the
            # others; the push never propagates back into world/art/.
            from evennia import logger

            logger.log_warn("art push failed for session %s" % getattr(session, "sessid", "?"))


def connect_art_push() -> None:
    """Connect the art completion subscriber with a stable dispatch UID.

    Called from ``at_server_start``; the deferred-import seam keeps this module
    importable without the presentation registry while a worker is being
    developed. Re-connecting is a re-entrant no-op because of ``dispatch_uid``.
    """
    from world.art.signals import asset_completed

    asset_completed.connect(
        on_asset_completed,
        dispatch_uid=DISPATCH_UID,
        weak=False,
    )


__all__ = [
    "DISPATCH_UID",
    "connect_art_push",
    "on_asset_completed",
]
