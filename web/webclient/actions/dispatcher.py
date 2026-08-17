"""UI action dispatcher: validation, admission, deduplication, and publication.

The dispatcher performs global envelope validation, authenticated session actor
binding, epoch/revision checks, duplicate and in-flight checks, action lookup,
payload validation, adapter invocation, result serialization, and requested
panel refresh. Adapters receive the actor resolved from ``session.puppet``;
actor identity is never client-controlled.

The dispatcher holds per-sequence ephemeral state on ``session.ndb``:
- a bounded insertion-ordered completed-result cache,
- one in-flight marker,
- the active presentation epoch and base revision for admission.

It never writes persistent canonical state itself; adapters are the only
presentation-side components allowed to invoke public deterministic APIs.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
import secrets
from typing import Any

from twisted.internet.defer import Deferred

from web.webclient.actions.registry import ActionRegistry
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    attach_coordinator,
)
from web.webclient.presentation.ingress import options_snapshot
from web.webclient.presentation.protocol import (
    PROTOCOL_VERSION,
    UI_ACTION_RESULT,
    ProtocolValidationError,
    check_envelope,
    validate_ui_action,
)
from web.webclient.presentation.registry import PresentationRegistry

# Bounded size of the completed-request cache per live sequence.
CACHE_CAPACITY = 64

# Stable results produced by the dispatcher itself (not by an adapter).
_BUSY_CODE = "busy"
_BUSY_MESSAGE = "另一項操作正在進行中"
_STALE_CODE = "stale"
_STALE_MESSAGE = "畫面狀態已更新，請重新操作"
_UNKNOWN_ACTION_CODE = "unknown_action"
_UNKNOWN_ACTION_MESSAGE = "未知的操作"
_MALFORMED_PAYLOAD_CODE = "malformed_payload"
_MALFORMED_PAYLOAD_MESSAGE = "操作內容格式錯誤"
_INTERNAL_CODE = "internal_error"
_INTERNAL_MESSAGE = "操作時發生內部錯誤"


class DispatchError(ValueError):
    """A UI action could not be admitted for a safe, stable reason."""


@dataclass
class SequenceState:
    """Ephemeral per transport-and-puppet dispatch state.

    Attributes:
        cache: Bounded insertion-ordered completed-result cache.
        in_flight: Whether one mutation is currently admitted.
        epoch: The presentation epoch captured at admission. Completion
            publication requires this epoch to still match the live
            coordinator, so a retired sequence can never publish into its
            replacement.
    """

    cache: OrderedDict[str, dict[str, Any]] = field(default_factory=OrderedDict)
    in_flight: bool = False
    epoch: str | None = None


def _sequence_state(session: Any) -> SequenceState:
    ndb = getattr(session, "ndb", None)
    state = getattr(ndb, "elosern_dispatch", None) if ndb is not None else None
    if state is None:
        state = SequenceState()
        if ndb is not None:
            ndb.elosern_dispatch = state
    return state


def retire_sequence(session: Any) -> None:
    """Discard the completed-result cache and in-flight marker for a sequence.

    Called on transport replacement and puppet change so a retired sequence can
    never publish a result or panel state into its replacement. The in-flight
    marker is cleared only through the epoch-guarded settle, so a still-running
    old Deferred cannot clear the replacement's lock either.
    """
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        state = getattr(ndb, "elosern_dispatch", None)
        if state is not None:
            state.epoch = None
        ndb.elosern_dispatch = None


NO_PUPPET_CODE = "no_puppet"
NO_PUPPET_MESSAGE = "目前沒有附身角色，無法執行操作"


def reject_no_puppet(session: Any, action: dict[str, Any]) -> None:
    """Send the bounded no-puppet rejection for one validated ``ui_action``.

    The envelope echoes the request's own epoch and base revision so the
    browser can accept it against the view it acted on and release its
    in-flight mutation lock; no character state is ever included.
    """
    _send_action_result(
        session,
        action["presentation_epoch"],
        action["request_id"],
        {"outcome": "rejected", "code": NO_PUPPET_CODE, "message": NO_PUPPET_MESSAGE},
        action["base_revision"],
    )


def _cache_result(state: SequenceState, request_id: str, result: dict[str, Any]) -> None:
    state.cache[request_id] = result
    state.cache.move_to_end(request_id)
    while len(state.cache) > CACHE_CAPACITY:
        state.cache.popitem(last=False)


def _protocol_error_envelope(code: str, message: str, *, correlation_id: str | None = None) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
        "reload_required": False,
    }
    if correlation_id is not None:
        envelope["correlation_id"] = correlation_id
    return envelope


def _safe_busy_result() -> dict[str, Any]:
    return {
        "outcome": "rejected",
        "code": _BUSY_CODE,
        "message": _BUSY_MESSAGE,
    }


def _admission_error_result(code: str, message: str) -> dict[str, Any]:
    return {"outcome": "rejected", "code": code, "message": message}


def _stale_result() -> dict[str, Any]:
    return {"outcome": "stale", "code": _STALE_CODE, "message": _STALE_MESSAGE}


def handle_ui_action(
    session: Any,
    actor: Any,
    payload: Any,
    action_registry: ActionRegistry,
    registry: PresentationRegistry,
) -> None:
    """Validate, admit, and dispatch one ``ui_action`` envelope.

    This entry point is synchronous: it emits a safe protocol error, a busy or
    stale rejection, or the cached duplicate result directly. Admitted
    non-duplicate actions are handed to the Deferred publication path and never
    resolve inside this call.
    """
    coordinator = attach_coordinator(session, registry)

    try:
        check_envelope(payload)
        action = validate_ui_action(payload)
    except Exception:
        _send_protocol_error(
            session,
            _protocol_error_envelope("malformed_envelope", "操作訊息格式錯誤"),
        )
        return

    state = _sequence_state(session)
    request_id = action["request_id"]
    if request_id in state.cache:
        # A completed request replays its prior result without re-execution.
        _send_action_result(session, coordinator.epoch, request_id, state.cache[request_id], coordinator.revision)
        return

    # Epoch and base revision must equal the newest values issued to the live
    # sequence before any action-specific validation or adapter invocation.
    if action["presentation_epoch"] != coordinator.epoch:
        _send_stale(session, coordinator, state, request_id)
        return
    if action["base_revision"] != coordinator.revision:
        _send_stale(session, coordinator, state, request_id)
        return

    try:
        spec = action_registry.spec(action["action_id"])
    except KeyError:
        _send_rejected(session, coordinator, request_id, _UNKNOWN_ACTION_CODE, _UNKNOWN_ACTION_MESSAGE)
        return

    try:
        normalized = spec.validate_payload(action["payload"])
    except Exception:
        _send_rejected(session, coordinator, request_id, _MALFORMED_PAYLOAD_CODE, _MALFORMED_PAYLOAD_MESSAGE)
        return

    if state.in_flight:
        _send_action_result(
            session, coordinator.epoch, request_id, _safe_busy_result(), coordinator.revision
        )
        return

    # Capture the epoch at admission; completion publication requires it to
    # still match so a puppet change cannot publish A-derived state to B.
    state.in_flight = True
    state.epoch = coordinator.epoch
    deferred = _invoke_adapter(session, actor, spec.adapter, normalized, action_registry, registry, request_id, state.epoch)
    if deferred is not None:
        deferred.addBoth(lambda result, session=session, epoch=state.epoch: _settle_in_flight(session, epoch, result))
    else:
        # The adapter resolved synchronously through the synchronous path.
        _settle_in_flight(session, state.epoch, None)


def _invoke_adapter(
    session: Any,
    actor: Any,
    adapter: Any,
    normalized: dict[str, Any],
    action_registry: ActionRegistry,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
) -> Deferred | None:
    """Invoke the adapter, observing both settlement paths.

    Returns the Deferred when the adapter is Deferred-returning; otherwise the
    synchronous result is published immediately through the critical section.
    """
    try:
        result = adapter(actor, normalized)
    except Exception:
        return _settle_internal_error(session, actor, action_registry, registry, request_id, epoch)
    if isinstance(result, Deferred):
        result.addBoth(
            lambda value, _s=session, _a=actor, _r=registry, _q=request_id, _e=epoch: _publish_completion(_s, _a, value, _r, _q, _e)
        )
        return result
    _publish_completion(session, actor, result, registry, request_id, epoch)
    return None


def _settle_internal_error(
    session: Any,
    actor: Any,
    action_registry: ActionRegistry,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
) -> None:
    correlation_id = secrets.token_hex(16)
    coordinator = attach_coordinator(session, registry)
    if coordinator.epoch != epoch:
        # The sequence was retired; nothing may publish into the replacement.
        _settle_in_flight(session, epoch, None)
        return
    context = PresentationContext(
        actor=actor,
        protocol_version=PROTOCOL_VERSION,
        options_state=options_snapshot(session),
    )
    _publish_presentation(session, coordinator, context, None)
    result = {
        "outcome": "error",
        "code": _INTERNAL_CODE,
        "message": _INTERNAL_MESSAGE,
        "correlation_id": correlation_id,
    }
    _cache_result(_sequence_state(session), request_id, result)
    _send_action_result(session, coordinator.epoch, request_id, result, coordinator.revision)
    _settle_in_flight(session, epoch, None)


def _publish_completion(
    session: Any,
    actor: Any,
    value: Any,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
) -> Any:
    """Publish canonical presentation and the matching result for an adapter.

    This runs in the coordinator publication critical section: exactly one next
    revision is allocated, the completion presentation is sent before the
    exact result naming the same revision, and the server in-flight marker is
    released only after both sends. The captured ``epoch`` must still match the
    live coordinator; a retired sequence publishes nothing into its
    replacement.
    """
    coordinator = attach_coordinator(session, registry)
    state = _sequence_state(session)
    if not state.in_flight or state.epoch != epoch or coordinator.epoch != epoch:
        # The sequence was retired (transport or puppet change); nothing may
        # publish into the replacement.
        _settle_in_flight(session, epoch, None)
        return value

    if isinstance(value, BaseException) or (value is not None and not isinstance(value, dict)):
        value = {
            "outcome": "error",
            "code": _INTERNAL_CODE,
            "message": _INTERNAL_MESSAGE,
            "correlation_id": secrets.token_hex(16),
        }

    if not isinstance(value, dict) or "outcome" not in value:
        value = {
            "outcome": "error",
            "code": _INTERNAL_CODE,
            "message": _INTERNAL_MESSAGE,
            "correlation_id": secrets.token_hex(16),
        }

    outcome = value.get("outcome")
    affected = value.get("affected_panels")
    context = PresentationContext(
        actor=actor,
        protocol_version=PROTOCOL_VERSION,
        options_state=options_snapshot(session),
    )
    if not isinstance(affected, (tuple, list, set)):
        affected = None
    if affected is not None:
        unknown = set(affected) - coordinator.registry.panel_names
        if unknown:
            # An adapter declaring panels it does not own cannot publish; use a
            # full recovery snapshot instead of raising mid-publication.
            affected = None
    try:
        if outcome in ("stale", "error") or not affected:
            _publish_presentation(session, coordinator, context, None)
        else:
            _publish_presentation(session, coordinator, context, tuple(affected))
    except Exception:
        correlation_id = secrets.token_hex(16)
        result = {
            "outcome": "error",
            "code": _INTERNAL_CODE,
            "message": _INTERNAL_MESSAGE,
            "correlation_id": correlation_id,
        }
        _cache_result(state, request_id, result)
        _send_action_result(session, coordinator.epoch, request_id, result, coordinator.revision)
        _settle_in_flight(session, epoch, None)
        return value

    result = _normalize_result(value)
    _cache_result(state, request_id, result)
    _send_action_result(session, coordinator.epoch, request_id, result, coordinator.revision)
    _settle_in_flight(session, epoch, None)
    return value


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    """Convert an adapter result into an exact schema-valid result dict.

    Any field that would violate the exact result envelope (unknown outcome,
    unstable or oversized code, empty or oversized message, malformed
    correlation ID) is replaced by a safe generic internal error so the
    browser can never be asked to accept an out-of-schema result.
    """
    from web.webclient.presentation.protocol import (
        _validate_identifier,
        _validate_message,
        _validate_correlation_id,
        _validate_request_id,
    )

    outcome = value.get("outcome")
    code = value.get("code")
    message = value.get("message")
    correlation_id = value.get("correlation_id")
    if outcome not in ("success", "rejected", "stale", "error"):
        return _internal_result(None)
    try:
        code = _validate_identifier(code, "code")
        message = _validate_message(message, "message")
        if outcome == "error":
            correlation_id = _validate_correlation_id(correlation_id)
        else:
            correlation_id = None
    except ProtocolValidationError:
        return _internal_result(None)
    result: dict[str, Any] = {
        "outcome": outcome,
        "code": code,
        "message": message,
    }
    if outcome == "error":
        result["correlation_id"] = correlation_id
    return result


def _internal_result(correlation_id: str | None) -> dict[str, Any]:
    return {
        "outcome": "error",
        "code": _INTERNAL_CODE,
        "message": _INTERNAL_MESSAGE,
        "correlation_id": correlation_id or secrets.token_hex(16),
    }


def _publish_presentation(
    session: Any,
    coordinator: PresentationCoordinator,
    context: PresentationContext,
    affected: Any,
) -> None:
    """Send a full snapshot (or affected-panel update) at one new revision."""
    if affected:
        panels = {name: coordinator.registry.render(name, context) for name in affected}
        coordinator.panel_update(context, panels)
    else:
        coordinator.full_snapshot(context)


def _send_stale(session: Any, coordinator: PresentationCoordinator, state: SequenceState, request_id: str) -> None:
    context = PresentationContext(
        actor=getattr(session, "puppet", None),
        protocol_version=PROTOCOL_VERSION,
        options_state=options_snapshot(session),
    )
    _publish_presentation(session, coordinator, context, None)
    result = _stale_result()
    # A stale result is never cached: the browser resubmits the same request ID
    # with a newer base revision, and a cached stale entry would wrongly replay.
    _send_action_result(session, coordinator.epoch, request_id, result, coordinator.revision)


def _send_rejected(
    session: Any,
    coordinator: PresentationCoordinator,
    request_id: str,
    code: str,
    message: str,
) -> None:
    """Send a schema-valid rejected ``ui_action_result`` for an admission failure.

    Unknown actions and malformed action payloads are stable, safe rejections;
    they use the exact result envelope (outcome ``rejected``) rather than a
    protocol error, which is reserved for transport/protocol-level failures.
    """
    result = _admission_error_result(code, message)
    _send_action_result(session, coordinator.epoch, request_id, result, coordinator.revision)


def _send_action_result(
    session: Any,
    epoch: str,
    request_id: str,
    result: dict[str, Any],
    presentation_revision: int,
) -> None:
    envelope: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "presentation_epoch": epoch,
        "request_id": request_id,
        "outcome": result["outcome"],
        "code": result["code"],
        "message": result["message"],
        "presentation_revision": presentation_revision,
    }
    if "correlation_id" in result:
        envelope["correlation_id"] = result["correlation_id"]
    session.msg(**{UI_ACTION_RESULT: ((envelope,), {})})


def _send_protocol_error(session: Any, envelope: dict[str, Any]) -> None:
    from web.webclient.presentation.ingress import send_protocol_error

    send_protocol_error(
        session,
        code=envelope["code"],
        message=envelope["message"],
        reload_required=envelope.get("reload_required", False),
        correlation_id=envelope.get("correlation_id"),
    )


def _settle_in_flight(session: Any, epoch: str | None, _result: Any) -> Any:
    """Release the in-flight marker after a sequence's publication settles.

    Only the marker belonging to ``epoch`` is cleared, so a retired sequence's
    completion cannot clear a replacement's lock.
    """
    state = _sequence_state(session)
    if state.epoch == epoch:
        state.in_flight = False
        state.epoch = None
    return _result
