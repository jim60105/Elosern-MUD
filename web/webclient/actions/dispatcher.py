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

Adapters declare the fixed ``adapter(actor, payload, session=None)`` ABI;
``_invoke_adapter`` passes the authenticated session positionally as the third
argument with no signature introspection, so an adapter may target the session
(for example the ``options.dismiss`` eviction) without guessing Evennia
account APIs.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
import json
import secrets
from typing import Any, Mapping

from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from web.webclient.actions.registry import ActionRegistry
from world.observability import log_error, log_warn
from world.rules.combat_beats import RoundRecord

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import (
    PresentationCoordinator,
    ResultDeliveryError,
    attach_coordinator,
)
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.publication import (
    PublicationCompletion,
    PublicationReceipt,
    copy_json_value,
)
from web.webclient.presentation.protocol import (
    PROTOCOL_VERSION,
    UI_ACTION_RESULT,
    ProtocolValidationError,
    check_envelope,
    validate_ui_action_result,
    _validate_result_data,
    validate_ui_action,
)
from web.webclient.presentation.registry import PresentationRegistry
from world.rules.presentation_events import publication_group


# Bounded size of the completed-request cache per live sequence.
CACHE_CAPACITY = 64

# The private adapter-result slot naming the causal publication group of the
# synchronous deterministic work the adapter performed. It is internal: it is
# never copied into a result envelope and never serialized.
PUBLICATION_GROUP_FIELD = "publication_group_id"

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

# The dialogue actions whose successful completion triggers a fresh
# action-options generation (action-options-trigger-hooks D3).
_DIALOGUE_TRIGGER_ACTION_IDS = frozenset({"explore.talk_scripted", "explore.talk_freeform"})

# The combat actions whose successful completion may end the active session
# and therefore trigger a fresh exploration action-options generation for
# every live watcher of the actor (action-options-wiring-hardening D2): the
# party command's completing confirmation and the confirmed party exit are the
# only two routes that can settle a terminal outcome.
_COMBAT_TRIGGER_ACTION_IDS = frozenset({"combat.command", "combat.exit_confirm"})

# The field cast whose instant-terminal opening also ends a combat.
_FIELD_CAST_ACTION_ID = "explore.cast"


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
    except Exception:  # observability: ignore R2: malformed client input is answered with the protocol-error envelope; the response IS the reported failure
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
    except KeyError:  # observability: ignore R2: an unknown action_id is answered with the rejected envelope; the client-visible rejection IS the report
        _send_rejected(session, coordinator, request_id, _UNKNOWN_ACTION_CODE, _UNKNOWN_ACTION_MESSAGE)
        return

    action_payload = action.get("payload")
    if action["action_id"] == "explore.talk_scripted":
        if not isinstance(action_payload, Mapping) or "selection_id" in action_payload:
            _send_rejected(session, coordinator, request_id, _MALFORMED_PAYLOAD_CODE, _MALFORMED_PAYLOAD_MESSAGE)
            return
        action_payload = {**action_payload, "selection_id": request_id}

    try:
        normalized = spec.validate_payload(action_payload)
    except Exception:  # observability: ignore R2: a payload failing the action's schema is answered with the malformed-payload rejection envelope; the rejection IS the report
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
    # The publication Deferred is the single completion authority: it releases
    # the in-flight marker (and runs the scheduled triggers) only after the
    # presentation frames and the matching result have sent, whether the
    # adapter resolved synchronously or through its own Deferred.
    _invoke_adapter(
        session,
        actor,
        spec.adapter,
        normalized,
        action_registry,
        registry,
        request_id,
        state.epoch,
        action_id=spec.action_id,
    )


def _invoke_adapter(
    session: Any,
    actor: Any,
    adapter: Any,
    normalized: dict[str, Any],
    action_registry: ActionRegistry,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
    action_id: str | None = None,
) -> None:
    """Invoke the adapter, observing both settlement paths.

    Both paths funnel into :func:`_publish_completion`, whose publication
    Deferred owns the in-flight release. ``action_id`` (default ``None`` so
    existing callers and tests keep their signatures) is threaded into the
    completion publication so the dialogue trigger can identify talk
    completions (action-options-trigger-hooks D3).

    The synchronous adapter invocation is bound to one causal publication
    group, so every panel push and checkpoint fact the adapter's committed work
    enqueues coalesces with this action's completion into a single publication.
    The binding is closed before this function returns, so a pending adapter
    ``Deferred`` never carries it: an adapter that resumes after asynchronous
    work binds its own final synchronous call and names it in the private result
    slot instead.
    """
    failed = False
    result: Any = None
    with publication_group() as captured:
        group_id = captured.id
        try:
            result = adapter(actor, normalized, session)
        except Exception as error:
            log_error(
                "action_adapter_failed",
                context={
                    "char": str(getattr(actor, "pk", "?")),
                    "surface": "dispatcher",
                    "request_id": request_id,
                },
                exc=error,
            )
            failed = True
    if failed:
        _settle_internal_error(session, actor, action_registry, registry, request_id, epoch)
        return
    if isinstance(result, Deferred):
        result.addBoth(
            lambda value, _s=session, _a=actor, _r=registry, _q=request_id, _e=epoch, _i=action_id: _publish_completion(_s, _a, value, _r, _q, _e, action_id=_i, group_id=None)
        )
        return
    _publish_completion(
        session,
        actor,
        result,
        registry,
        request_id,
        epoch,
        action_id=action_id,
        group_id=group_id,
    )


def _settle_internal_error(
    session: Any,
    actor: Any,
    action_registry: ActionRegistry,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
) -> None:
    """Publish the internal-error recovery snapshot and its matching result."""
    correlation_id = secrets.token_hex(16)
    coordinator = attach_coordinator(session, registry)
    if coordinator.epoch != epoch:
        # The sequence was retired; nothing may publish into the replacement.
        _settle_in_flight(session, epoch, None)
        return
    result = {
        "outcome": "error",
        "code": _INTERNAL_CODE,
        "message": _INTERNAL_MESSAGE,
        "correlation_id": correlation_id,
    }
    _publish_with_result(
        session,
        actor,
        coordinator,
        request_id,
        result,
        epoch=epoch,
        force_snapshot=True,
        cache=True,
    )


def _publish_completion(
    session: Any,
    actor: Any,
    value: Any,
    registry: PresentationRegistry,
    request_id: str,
    epoch: str,
    action_id: str | None = None,
    group_id: str | None = None,
) -> Any:
    """Publish canonical presentation and the matching result for an adapter.

    The normalized result is handed to the coordinator as one immutable
    completion: the coordinator prevalidates the exact ``ui_action_result``
    envelope against the revision it is about to publish, sends every
    presentation frame and then that result inside one serialized critical
    section, and resolves this publication's Deferred only afterwards. The
    in-flight marker is therefore released only after both sends, and the
    captured ``epoch`` must still match the live coordinator — a retired
    sequence publishes nothing into its replacement.

    The completion joins the causal group of the adapter's synchronous work
    (``group_id``), so any push or checkpoint fact from that work merges into
    the same publication instead of preceding it. An adapter that resumed after
    asynchronous work names the group it captured in the private
    ``publication_group_id`` slot, which wins. A result-only completion (the
    sequence-retiring actions B carved out) is flushed immediately: its adapter
    may already have scheduled the retirement for the next reactor turn, so the
    answer has to leave first. Every other group keeps waiting for the deferred
    boundary.
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

    target_group = _publication_group_id(value) or group_id
    result = _normalize_result(value)
    outcome = result["outcome"]
    affected = value.get("affected_panels")
    # Result-only completion (namegen-creation-ui D10): an adapter that
    # declares ``no_presentation`` on a success/rejected outcome ships its
    # result through the same serialized owner without any presentation, so it
    # cannot interleave another batch's frames. Every adapter already
    # publishes one way or the other, so a dice-roll that must not re-sync the
    # player's unsaved form edits had no channel; the duplicate-request busy
    # result is the established send-result-without-publish precedent. The
    # flag is internal: ``_normalize_result`` never copies it into the wire
    # envelope, and existing adapters (which never set it) are unchanged.
    result_only = bool(value.get("no_presentation")) and outcome in ("success", "rejected")
    if outcome in ("stale", "error"):
        # Recovery outcomes always re-announce the complete baseline.
        declaration = None
        force_snapshot = True
    elif result_only:
        declaration = None
        force_snapshot = False
    else:
        # A valid declaration scopes the comparison to those panels; an absent
        # declaration means unknown eager scope (compare every eager panel and
        # transmit only differences).
        declaration = affected if isinstance(affected, (tuple, list, set)) else None
        force_snapshot = False
    # The completing action's frozen round record reaches ONLY this
    # publication, and only when it really is one (combat-beats-panel D2): an
    # adapter cannot smuggle an arbitrary object into a presenter's read
    # context through the internal slot.
    combat_round = value.get("combat_round")
    round_record = combat_round if isinstance(combat_round, RoundRecord) else None
    deferred = coordinator.enqueue_publication(
        lambda: build_presentation_context(session, actor, combat_round=round_record),
        affected_panels=declaration,
        force_snapshot=force_snapshot,
        result_only=result_only,
        expected_epoch=epoch,
        completion=_completion(request_id, result),
        group_id=target_group,
    )
    if result_only and target_group is not None:
        coordinator.flush_publication_group(target_group)
    deferred.addCallbacks(
        lambda receipt: _completion_published(
            receipt, session, actor, coordinator, request_id, action_id, result, value, epoch
        ),
        lambda failure: _completion_failed(
            failure, session, actor, coordinator, request_id, result, epoch
        ),
    )
    return value


def _publication_group_id(value: Any) -> str | None:
    """The adapter's private causal-group slot, or ``None`` when absent/invalid.

    Only an adapter that resumed after asynchronous work sets it, to name the
    group it wrapped its final synchronous deterministic call in. Any other
    value is ignored: the completion then makes its own standalone group.
    """
    if not isinstance(value, dict):
        return None
    candidate = value.get(PUBLICATION_GROUP_FIELD)
    if not isinstance(candidate, str) or len(candidate) != 32:
        return None
    try:
        int(candidate, 16)
    except ValueError:  # observability: ignore R2: an unparseable identifier is the rejected value, not a swallowed failure
        return None
    return candidate


def _completion_published(
    receipt: PublicationReceipt | None,
    session: Any,
    actor: Any,
    coordinator: PresentationCoordinator,
    request_id: str,
    action_id: str | None,
    result: dict[str, Any],
    value: dict[str, Any],
    epoch: str,
) -> None:
    """Release the in-flight marker after the batch (and its result) sent.

    ``None`` means the captured sequence retired before its publication ran:
    nothing was sent and nothing may be published into the replacement. After a
    released marker, a successful talk or terminal-combat completion schedules
    its action-options regeneration fire-and-forget
    (action-options-trigger-hooks D3 / action-options-wiring-hardening D2): the
    reply text, presentation and result are already on the wire, so the trigger
    cannot reorder existing traffic, and a scheduling failure is logged and
    swallowed, never raised into publication.
    """
    if receipt is not None:
        _cache_result(_sequence_state(session), request_id, result)
    _settle_in_flight(session, epoch, None)
    # The gates use the *normalized* outcome actually sent to the client: a
    # raw ``success`` that normalizes into an internal error must never
    # schedule (action-options-trigger-hooks D3 / action-options-wiring-
    # hardening D2).
    if result["outcome"] == "success" and action_id in _DIALOGUE_TRIGGER_ACTION_IDS:
        _schedule_dialogue_options(session, actor, coordinator)
    if result["outcome"] == "success" and action_id in _COMBAT_TRIGGER_ACTION_IDS:
        _schedule_terminal_combat_options(actor)
    # A field cast whose opening ended the encounter at once is a combat
    # ending too (skillbook-authoritative-casting); an ordinary utility cast
    # or a continuing opening round schedules nothing. The flag is internal
    # adapter data that ``_normalize_result`` never copies to the wire.
    if (
        result["outcome"] == "success"
        and action_id == _FIELD_CAST_ACTION_ID
        and value.get("field_combat_terminal") is True
    ):
        _schedule_terminal_combat_options(actor)
    return None


def _completion_failed(
    failure: Any,
    session: Any,
    actor: Any,
    coordinator: PresentationCoordinator,
    request_id: str,
    result: dict[str, Any],
    epoch: str,
) -> None:
    """Recover from a publication failure without leaving the request unanswered.

    A presentation/preflight failure means nothing was published: the batched
    request is answered with the safe internal-error result through the same
    serialized owner (never from inside another batch), the cached duplicate
    entry stays truthful, and the in-flight marker is released once that answer
    resolves. A failure that happens *after* the presentation published (the
    result frame alone failed to send) must never manufacture a contradictory
    outcome: the completed result is cached for replay, the delivery
    uncertainty is logged as an operational failure, and the marker simply
    releases.
    """
    error = failure.value if isinstance(failure, Failure) else failure
    context = {
        "char": str(getattr(actor, "pk", "?")),
        "surface": "dispatcher",
        "request_id": request_id,
    }
    if isinstance(error, ResultDeliveryError):
        log_error("action_result_delivery_failed", context=context, exc=error)
        _cache_result(_sequence_state(session), request_id, result)
        _settle_in_flight(session, epoch, None)
        return
    log_error("presentation_publish_failed", context=context, exc=error)
    # Nothing was published, so the client's presentation is behind canonical
    # state. Report that through the safe protocol-error surface (it carries no
    # revision) before the single bounded answer below: the client then holds
    # the presentation unavailable and asks for one complete repair, instead of
    # resuming graphical mutations against stale panels.
    _send_presentation_unavailable(session)
    fallback = {
        "outcome": "error",
        "code": _INTERNAL_CODE,
        "message": _INTERNAL_MESSAGE,
        "correlation_id": secrets.token_hex(16),
    }
    _publish_with_result(
        session,
        actor,
        coordinator,
        request_id,
        fallback,
        epoch=epoch,
        force_snapshot=False,
        cache=True,
    )


def _send_presentation_unavailable(session: Any) -> None:
    """Mark the current presentation unavailable after a failed publication.

    The frame claims no revision and demands no reload: the client's next
    complete repair (the usual ``ui_sync`` path) rebuilds it. A transport that
    cannot carry the notice is already gone, so the delivery failure is logged
    here instead of raised into the caller's command settlement.
    """
    try:
        _send_protocol_error(
            session,
            _protocol_error_envelope(
                "presentation_unavailable", "圖形介面暫時無法更新，正在重新同步"
            ),
        )
    except Exception as send_error:  # observability: ignore R2: the publication failure above is the reported failure; a transport that cannot carry the notice is already gone
        log_warn(
            "presentation_unavailable_delivery_failed",
            context={
                "surface": "dispatcher",
                "session": str(getattr(session, "sessid", "?")),
            },
            exc=send_error,
        )


def _publish_with_result(
    session: Any,
    actor: Any,
    coordinator: PresentationCoordinator,
    request_id: str,
    result: dict[str, Any],
    *,
    epoch: str,
    force_snapshot: bool,
    cache: bool,
) -> None:
    """Answer one request through the serialized owner, with or without frames.

    Used where the response itself must not be lost (an adapter failure, a
    publication failure, an internal recovery): the result travels as a
    result-only publication so it always leaves after any batch already in
    progress, never between another action's presentation and its result. A
    recovery snapshot that cannot even be planned falls back to that result-only
    answer, so the admitted request is never left unanswered; a failure of the
    answer itself (``ResultDeliveryError``) is logged as delivery uncertainty
    and never answered twice. Either way the in-flight marker releases once the
    final answer's Deferred resolves.
    """
    state = _sequence_state(session)
    if cache:
        _cache_result(state, request_id, result)
    deferred = coordinator.enqueue_publication(
        lambda: build_presentation_context(session, actor),
        force_snapshot=force_snapshot,
        result_only=not force_snapshot,
        expected_epoch=coordinator.epoch,
        completion=_completion(request_id, result),
    )

    def _published(receipt: PublicationReceipt | None) -> None:
        _settle_in_flight(session, epoch, None)
        return None

    def _failed(failure: Any) -> None:
        error = failure.value if isinstance(failure, Failure) else failure
        context = {
            "char": str(getattr(actor, "pk", "?")),
            "surface": "dispatcher",
            "request_id": request_id,
        }
        if force_snapshot and not isinstance(error, ResultDeliveryError):
            # The recovery presentation could not be planned or sent, so the
            # safe result still travels as the same owner's result-only answer.
            log_error("presentation_publish_failed", context=context, exc=error)
            _send_presentation_unavailable(session)
            _publish_with_result(
                session,
                actor,
                coordinator,
                request_id,
                result,
                epoch=epoch,
                force_snapshot=False,
                cache=False,
            )
            return None
        log_error(
            "action_result_fallback_failed",
            context=context,
            exc=error,
        )
        _settle_in_flight(session, epoch, None)
        return None

    deferred.addCallbacks(_published, _failed)


def _completion(request_id: str, result: dict[str, Any]) -> PublicationCompletion:
    """Build the immutable coordinator completion for one normalized result."""
    owned = copy_json_value(dict(result))

    def envelope(epoch: str, revision: int) -> dict[str, Any]:
        return _result_envelope(epoch, request_id, owned, revision)

    return PublicationCompletion(request_id=request_id, result=owned, envelope=envelope)


def _schedule_dialogue_options(
    session: Any,
    actor: Any,
    coordinator: PresentationCoordinator,
) -> None:
    """Fire-and-forget the action-options generation after a talk completion.

    The dispatcher-held session is the sole watcher and the coordinator epoch
    is captured at publication time, so the service publishes through the
    correct sequence. The scheduling call is fire-and-forget by contract; any
    synchronous failure is logged as a bounded diagnostic and swallowed so
    publication is never delayed or altered.
    """
    try:
        from server.option_proposal_service import schedule_action_options

        schedule_action_options(
            actor,
            watchers=((session, coordinator.epoch),),
        )
    except Exception as error:
        log_warn(
            "action_options_schedule_failed",
            context={
                "surface": "dialogue-reply",
                "session": getattr(session, "sessid", "?"),
            },
            exc=error,
        )


def _schedule_terminal_combat_options(actor: Any) -> None:
    """Fire-and-forget the exploration options trigger after terminal combat.

    Runs only after the dispatcher has published the terminal completion
    presentation and the action result, and only when the successful combat
    action actually returned the actor to exploration — a non-terminal round
    leaves the session active, so nothing schedules. Every live watcher of the
    actor (``watchers_for(actor)``) is refreshed, not just the initiating
    session. Fire-and-forget by contract: any synchronous failure is logged
    as a bounded diagnostic and swallowed.
    """
    try:
        from server.option_proposal_service import schedule_action_options
        from web.webclient.presentation.affordances import in_exploration_mode
        from web.webclient.presentation.watchers import watchers_for

        if not in_exploration_mode(actor):
            return
        schedule_action_options(
            actor,
            watchers=watchers_for(actor),
        )
    except Exception as error:
        log_warn(
            "action_options_schedule_failed",
            context={
                "surface": "terminal-combat",
                "char": str(getattr(actor, "pk", "?")),
            },
            exc=error,
        )


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    """Convert an adapter result into an exact schema-valid result dict.

    Any field that would violate the exact result envelope (unknown outcome,
    unstable or oversized code, empty or oversized message, malformed
    correlation ID, a malformed or misplaced adapter data slot) is replaced by
    a safe generic internal error so the browser can never be asked to accept
    an out-of-schema result. The private causal-group slot is stripped here, so
    no group identity can ever be serialized.
    """
    from web.webclient.presentation.protocol import (
        _validate_identifier,
        _validate_message,
        _validate_correlation_id,
        _validate_request_id,
    )

    value = {
        key: item for key, item in value.items() if key != PUBLICATION_GROUP_FIELD
    }
    outcome = value.get("outcome")
    code = value.get("code")
    message = value.get("message")
    correlation_id = value.get("correlation_id")
    if outcome not in ("success", "rejected", "stale", "error"):
        return _internal_result(None)
    # An adapter data slot is contractually success-only; its mere presence on
    # any other outcome is an out-of-schema adapter result.
    if "data" in value and outcome != "success":
        return _internal_result(None)
    try:
        code = _validate_identifier(code, "code")
        message = _validate_message(message, "message")
        if outcome == "error":
            correlation_id = _validate_correlation_id(correlation_id)
        else:
            correlation_id = None
    except ProtocolValidationError:  # observability: ignore R2: an out-of-schema adapter result is replaced by the internal-error envelope; the browser-visible error IS the report
        return _internal_result(None)
    result: dict[str, Any] = {
        "outcome": outcome,
        "code": code,
        "message": message,
    }
    if outcome == "error":
        result["correlation_id"] = correlation_id
    if "data" in value:
        try:
            validated = _validate_result_data(value["data"])
        except ProtocolValidationError:  # observability: ignore R2: an adapter data slot over the exact bound is an out-of-schema adapter result; the internal-error envelope IS the report
            return _internal_result(None)
        # Own the slot: the completed-result cache replays this dict, so it
        # must be a private JSON snapshot, never the adapter's mutable object.
        result["data"] = json.loads(json.dumps(validated, ensure_ascii=False))
    return result


def _internal_result(correlation_id: str | None) -> dict[str, Any]:
    return {
        "outcome": "error",
        "code": _INTERNAL_CODE,
        "message": _INTERNAL_MESSAGE,
        "correlation_id": correlation_id or secrets.token_hex(16),
    }


def _send_stale(session: Any, coordinator: PresentationCoordinator, state: SequenceState, request_id: str) -> None:
    """Re-announce the complete baseline, then answer the stale request.

    The recovery snapshot is planned and prevalidated with the stale result
    envelope before the first frame, so the client always receives the complete
    snapshot that makes its superseded base usable again *before* the one
    bounded stale result. A publication failure falls back to the stale result
    alone at the current revision, so a pre-admission rejection is never lost.
    """
    result = _stale_result()
    # A stale result is never cached: the browser resubmits the same request ID
    # with a newer base revision, and a cached stale entry would wrongly replay.
    actor = getattr(session, "puppet", None)
    deferred = coordinator.enqueue_publication(
        lambda: build_presentation_context(session, actor),
        force_snapshot=True,
        expected_epoch=coordinator.epoch,
        completion=_completion(request_id, result),
    )

    def _failed(failure: Any) -> None:
        error = failure.value if isinstance(failure, Failure) else failure
        log_error(
            "stale_recovery_publish_failed",
            context={
                "surface": "dispatcher",
                "request_id": request_id,
                "session": str(getattr(session, "sessid", "?")),
            },
            exc=error,
        )
        fallback = coordinator.enqueue_publication(
            lambda: build_presentation_context(session, actor),
            result_only=True,
            expected_epoch=coordinator.epoch,
            completion=_completion(request_id, result),
        )

        def _answer_failed(answer_failure: Any) -> None:
            answer_error = (
                answer_failure.value
                if isinstance(answer_failure, Failure)
                else answer_failure
            )
            log_error(
                "stale_result_delivery_failed",
                context={
                    "surface": "dispatcher",
                    "request_id": request_id,
                    "session": str(getattr(session, "sessid", "?")),
                },
                exc=answer_error,
            )
            return None

        fallback.addErrback(_answer_failed)
        return None

    deferred.addErrback(_failed)


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
    session.msg(
        **{UI_ACTION_RESULT: ((_result_envelope(epoch, request_id, result, presentation_revision),), {})}
    )


def _result_envelope(
    epoch: str,
    request_id: str,
    result: dict[str, Any],
    presentation_revision: int,
) -> dict[str, Any]:
    """Build the exact ``ui_action_result`` naming one published revision."""
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
    if "data" in result:
        envelope["data"] = result["data"]
    return envelope


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
