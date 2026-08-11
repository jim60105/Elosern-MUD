"""
Project OOB input functions for the Elosern WebClient.

This module is loaded through ``settings.INPUT_FUNC_MODULES`` alongside
Evennia's own input functions. It adds ``ui_sync`` (authenticated WebSocket
synchronization) and overrides ``text`` so a WebClient command settlement can
refresh canonical presentation without changing Evennia's command semantics.
"""

from evennia.commands.cmdhandler import cmdhandler
from evennia.server.inputfuncs import _IDLE_COMMAND, _maybe_strip_incoming_mxp

from web.webclient.actions.dispatcher import handle_ui_action, reject_no_puppet
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.ingress import (
    is_webclient,
    observe_command_settlement,
    send_protocol_error,
    synchronize_session,
)
from web.webclient.presentation.protocol import (
    UI_SYNC,
    ProtocolValidationError,
    check_envelope,
    validate_ui_action,
    validate_ui_sync,
)
from web.webclient.presentation.registry import build_production_registry


def ui_sync(session, *args, **kwargs):
    """Authenticated WebSocket-only synchronization of canonical presentation.

    Accepts exactly ``{protocol_version: 1}`` from a WebSocket session with an
    active puppet. The actor is resolved only from ``session.puppet``; a
    client-supplied actor is rejected by the exact envelope schema. Anonymous,
    unpuppeted, Telnet, and AJAX sessions receive no character presentation
    state.
    """
    payload = args[0] if args else None

    if not is_webclient(session):
        # Telnet and AJAX sessions never receive Elosern graphical OOB state.
        return

    try:
        check_envelope(payload)
        validate_ui_sync(payload)
    except ProtocolValidationError as error:
        unsupported = "unsupported protocol_version" in str(error)
        send_protocol_error(
            session,
            code="unsupported_version" if unsupported else "malformed_envelope",
            message="不支援的協定版本" if unsupported else "同步訊息格式錯誤",
            reload_required=unsupported,
        )
        return

    actor = getattr(session, "puppet", None)
    if actor is None:
        # No puppet means no character presentation state is emitted.
        return

    synchronize_session(session, actor)


def ui_action(session, *args, **kwargs):
    """Authenticated WebSocket-only UI action dispatch.

    The actor is resolved only from ``session.puppet``. Anonymous, unpuppeted,
    Telnet, and AJAX sessions are rejected before adapter invocation, and no
    character state is returned. An unpuppeted action is never silently
    dropped: it receives a bounded ``no_puppet`` rejection so the browser can
    release its in-flight mutation lock.
    """
    if not is_webclient(session):
        return
    payload = args[0] if args else None
    actor = getattr(session, "puppet", None)
    if actor is None:
        # Validate only the global envelope: the echoed epoch/revision must be
        # schema-safe, and malformed input still gets the safe error.
        try:
            check_envelope(payload)
            action = validate_ui_action(payload)
        except Exception:
            send_protocol_error(
                session,
                code="malformed_envelope",
                message="操作訊息格式錯誤",
                reload_required=False,
            )
            return
        reject_no_puppet(session, action)
        return
    handle_ui_action(
        session,
        actor,
        payload,
        build_production_action_registry(),
        build_production_registry(),
    )


def text(session, *args, **kwargs):
    """Main text input preserving Evennia 6.1 semantics with post-command refresh.

    Idle handling, MXP stripping, nickname replacement, command dispatch, and
    session counters behave exactly as Evennia's stock ``text`` input function.
    The difference is that the Deferred returned by the command handler is
    observed: after a WebClient command settles (callback or errback), a safe
    full-snapshot refresh is attempted from then-current canonical state. The
    observer never replaces the original value or Failure, and Telnet/AJAX
    sessions receive no graphical output.
    """
    txt = args[0] if args else None
    if txt is None:
        return
    if txt.strip() in _IDLE_COMMAND:
        session.update_session_counters(idle=True)
        return

    txt = _maybe_strip_incoming_mxp(txt)

    if session.account:
        puppet = session.puppet
        if puppet:
            txt = puppet.nicks.nickreplace(txt, categories=("inputline"), include_account=True)
        else:
            txt = session.account.nicks.nickreplace(
                txt, categories=("inputline"), include_account=False
            )
    kwargs.pop("options", None)
    deferred = cmdhandler(session, txt, callertype="session", session=session, **kwargs)
    session.update_session_counters()

    if is_webclient(session):
        observe_command_settlement(deferred, session)
