"""Targeted OOB art completion push (design D2/D5).

A subscriber to the ``world.art`` ``asset_completed`` signal re-renders the
``art``, ``gallery``, and ``roster`` panels for every connected WebClient session,
gates each independently by reference to the completed subject key, and publishes
all matching available panels in a single affected-panel ``ui_update`` at a newer
revision through the session's coordinator. The subscriber never runs on the worker
thread (the signal is emitted from the drain success callback on the reactor thread),
never propagates an exception back into ``world/art/``, and isolates one bad session
from the others.

Late completions for an old room or a no-longer-present entity re-derive from
current canonical state, so the rendered panel no longer references the subject
and nothing is published for that panel -- the "late completion never replaces
the current panel" rule is enforced by re-derivation, not by remembering what was sent.
"""

from typing import Any

from world.observability import log_info, log_warn

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    attach_coordinator,
)
from web.webclient.presentation.ingress import build_presentation_context, is_webclient
from web.webclient.presentation.registry import build_production_registry

# Stable per-subscriber identity so re-connecting from at_server_start is a
# re-entrant no-op.
DISPATCH_UID = "elosern.art_push"


def _art_subject_keys(payload: dict[str, Any]) -> set[str]:
    """Return the subject keys the rendered art payload references."""
    keys: set[str] = set()
    scene = payload.get("scene") or {}
    if isinstance(scene, dict) and scene.get("subject_key"):
        keys.add(scene["subject_key"])
    catalog = payload.get("portrait_catalog")
    if isinstance(catalog, dict):
        for entry in catalog.values():
            if isinstance(entry, dict) and entry.get("subject_key"):
                keys.add(entry["subject_key"])
    return keys


def _gallery_subject_keys(payload: dict[str, Any]) -> set[str]:
    """Return the subject keys the rendered gallery payload matches.

    Per D2, gallery matches on rendered ``selected`` only, not every rail
    ``subjects`` entry.
    """
    selected = payload.get("selected")
    if isinstance(selected, str) and selected:
        return {selected}
    return set()


def _roster_subject_keys(payload: dict[str, Any]) -> set[str]:
    """Return the subject keys the rendered roster payload references.

    Per D2, roster matches on every ``characters[*].portrait.subject_key``,
    not only the current puppet row.
    """
    keys: set[str] = set()
    characters = payload.get("characters")
    if isinstance(characters, list):
        for char in characters:
            if isinstance(char, dict):
                portrait = char.get("portrait")
                if isinstance(portrait, dict):
                    subject_key = portrait.get("subject_key")
                    if isinstance(subject_key, str) and subject_key:
                        keys.add(subject_key)
    return keys


def _panel_matches_subject(panel_name: str, payload: dict[str, Any], subject_key: str) -> bool:
    """Check whether an available rendered panel payload references the subject."""
    if not payload.get("available"):
        return False
    if panel_name == "art":
        return subject_key in _art_subject_keys(payload)
    if panel_name == "gallery":
        return subject_key in _gallery_subject_keys(payload)
    if panel_name == "roster":
        return subject_key in _roster_subject_keys(payload)
    return False


def _push_for_subject(session: Any, actor: Any, subject_key: str) -> None:
    """Re-render and push matching panels for one session."""
    coordinator: PresentationCoordinator = getattr(
        getattr(session, "ndb", None), "elosern_coordinator", None
    )
    if coordinator is None:
        coordinator = attach_coordinator(session, build_production_registry())
    registry = coordinator.registry
    context: PresentationContext = build_presentation_context(session, actor)

    matching_panels: dict[str, Any] = {}
    for panel_name in ("art", "gallery", "roster"):
        if panel_name not in registry.panel_names:
            continue
        payload = registry.render(panel_name, context)
        if _panel_matches_subject(panel_name, payload, subject_key):
            matching_panels[panel_name] = payload

    if not matching_panels:
        return

    envelope = coordinator.panel_update(context, matching_panels)
    log_info(
        "art_completion_push",
        context={
            "subject": subject_key,
            "session": getattr(session, "sessid", "?"),
            "panels": list(envelope.get("panels", matching_panels).keys()),
        },
    )


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
        except Exception as error:
            # A bad session logs a bounded diagnostic and cannot stop the
            # others; the push never propagates back into world/art/.
            log_warn(
                "art_push_unavailable",
                context={
                    "surface": "art",
                    "session": getattr(session, "sessid", "?"),
                    "subject": subject_key,
                },
                exc=error,
            )


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
    "_art_subject_keys",
    "_gallery_subject_keys",
    "_panel_matches_subject",
    "_roster_subject_keys",
    "DISPATCH_UID",
    "connect_art_push",
    "on_asset_completed",
]
