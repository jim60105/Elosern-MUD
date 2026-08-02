"""Server-side ingress and post-command refresh helpers for the OOB protocol.

These helpers isolate the Evennia session plumbing from the pure protocol and
coordinator modules: the input functions in ``server/conf/inputfuncs.py`` stay
thin and delegate authentication, synchronization, protocol-error emission, and
post-command refresh here.
"""

from typing import Any

from twisted.internet.defer import Deferred

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    ClockUnavailable,
    PresentationCoordinator,
    attach_coordinator,
    log_unavailable,
)
from web.webclient.presentation.protocol import (
    PROTOCOL_VERSION,
    UI_PROTOCOL_ERROR,
    check_envelope,
)
from web.webclient.presentation.registry import build_production_registry

# The only transport that may receive Elosern graphical OOB state. Evennia 6.1
# portal sessions pass "websocket" to ``init_session``, which overwrites the
# class-level "webclient/websocket" label, so real sessions report "websocket";
# both spellings are accepted.
_WEBSOCKET_PROTOCOLS = frozenset({"websocket", "webclient/websocket"})
_AJAX_PROTOCOL = "webclient/ajax"


def is_webclient(session: Any) -> bool:
    """Return whether ``session`` is the evennia WebSocket WebClient."""
    return getattr(session, "protocol_key", None) in _WEBSOCKET_PROTOCOLS


def is_ajax_webclient(session: Any) -> bool:
    """Return whether ``session`` is the legacy AJAX WebClient."""
    return getattr(session, "protocol_key", None) == _AJAX_PROTOCOL


def send_protocol_error(
    session: Any,
    *,
    code: str,
    message: str,
    reload_required: bool,
    correlation_id: str | None = None,
) -> None:
    """Emit one exact ``ui_protocol_error`` envelope to a session."""
    envelope: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
        "reload_required": reload_required,
    }
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    session.msg(**{UI_PROTOCOL_ERROR: ((envelope,), {})})


def _coordinator_for(session: Any, actor: Any) -> PresentationCoordinator:
    """Return the session's ephemeral coordinator, reset on puppet change.

    A puppet change atomically retires the previous presentation sequence AND
    the previous dispatch sequence (request cache and in-flight marker), so a
    completion Deferred started for the old puppet can never publish a result
    or panel state into the new puppet's sequence.
    """
    coordinator = attach_coordinator(session, build_production_registry())
    actor_id = str(getattr(actor, "pk", ""))
    last_actor = getattr(session.ndb, "elosern_actor_id", None)
    if last_actor is not None and last_actor != actor_id:
        # A puppet change starts a distinct presentation sequence.
        coordinator.reset()
        from web.webclient.actions.dispatcher import retire_sequence

        retire_sequence(session)
    session.ndb.elosern_actor_id = actor_id
    return coordinator


def synchronize_session(session: Any, actor: Any) -> bool:
    """Emit a full snapshot for a puppeted session; return success.

    Returns ``True`` after a snapshot is sent, ``False`` when a safe protocol
    error replaced it (for example, the world clock is unexpectedly absent).
    Never raises: presentation failures are logged and isolated so text play is
    unaffected.
    """
    coordinator = _coordinator_for(session, actor)
    context = PresentationContext(actor=actor, protocol_version=PROTOCOL_VERSION)
    try:
        coordinator.synchronize(context)
    except ClockUnavailable:
        log_unavailable(coordinator.describe_session(), "world clock is absent")
        send_protocol_error(
            session,
            code="presentation_unavailable",
            message="目前無法取得世界時間，圖形介面暫停同步",
            reload_required=False,
        )
        return False
    except Exception:
        correlation_id = __import__("secrets").token_hex(16)
        log_unavailable(coordinator.describe_session(), f"sync failed {correlation_id}")
        send_protocol_error(
            session,
            code="internal_error",
            message="同步時發生內部錯誤",
            reload_required=True,
            correlation_id=correlation_id,
        )
        return False
    return True


def refresh_after_command(session: Any, actor: Any) -> None:
    """Best-effort full snapshot after a WebClient command settles.

    Presentation failure is logged separately and never replaces the command's
    own value or Failure; Telnet and AJAX sessions are never touched.
    """
    if not is_webclient(session):
        return
    try:
        synchronize_session(session, actor)
    except Exception:
        correlation_id = __import__("secrets").token_hex(16)
        log_unavailable(getattr(session, "sessid", "?"), f"refresh failed {correlation_id}")


def observe_command_settlement(deferred: Deferred, session: Any) -> None:
    """Attach a non-consuming observer to a command Deferred.

    ``deferred`` is the Deferred returned by Evennia's command handler. The
    observer runs once on either the callback or errback path, preserves the
    original success value or Failure unchanged, and then attempts one safe
    presentation refresh for WebClient sessions.
    """

    def _attempt(value: Any) -> Any:
        actor = getattr(session, "puppet", None)
        if actor is not None:
            refresh_after_command(session, actor)
        return value

    def _attempt_failure(failure: Any) -> Any:
        actor = getattr(session, "puppet", None)
        if actor is not None:
            try:
                refresh_after_command(session, actor)
            except Exception:
                correlation_id = __import__("secrets").token_hex(16)
                log_unavailable(getattr(session, "sessid", "?"), f"refresh failed {correlation_id}")
        return failure

    deferred.addCallbacks(_attempt, _attempt_failure)
