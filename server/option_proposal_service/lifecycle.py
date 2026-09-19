"""Generation lifecycle: delivery, completion routing, settlement, successor handoff.

The guarded delivery path (token-guarded per-session state writes plus the
epoch-guarded push), the completion routing that turns one layer outcome into
cache/memo/state effects, and the chain continuation that cleans up the
pending registry and starts a queued successor exactly once through the
identity-guarded detached-predecessor handoff.

Call-time seams live on this module: ``_run_generation`` is resolved through
this module's globals by ``_start_successor`` and by the scheduling module
(the action_options precedent), so a test patch of the seam retargets to this
module and steers every call site the single-module service used to share.
"""

from typing import Any

from twisted.internet import defer

from world.observability import log_warn

from server.option_proposal_service import clients as _clients
from server.option_proposal_service import situation as _situation
from server.option_proposal_service.state import (
    _cache_put,
    _chains,
    _clear_barrier_min,
    _display_for,
    _drop_if_current,
    _GenerationChain,
    _memo_put,
    _options_state,
    _pending,
    _PendingGeneration,
    _PendingSubscriber,
    _push_options_update,
    _set_options_state,
    _state,
)


def _deliver(
    subscriber: _PendingSubscriber,
    actor: Any,
    status: str,
    displayed: list | None,
    *,
    clear_barrier: bool = True,
) -> None:
    """Deliver one outcome to one subscriber under the token guard.

    ``clear_barrier`` is the eligible-outcome flag: an eligible delivery (a
    result from a generation at or above the session's dismissal barrier)
    clears the barrier; an ineligible settle (a degraded successor outcome
    after the situation moved on) leaves every barrier standing.
    """
    session = subscriber.session
    state = _options_state(session)
    owner_ok = (
        state is not None
        and str(state.get("owner_actor_id", "")) == str(getattr(actor, "pk", ""))
    )
    if not owner_ok:
        return
    if int(state.get("generation_token", 0)) != subscriber.token:
        return
    _set_options_state(
        session,
        _state(
            str(getattr(actor, "pk", "")),
            subscriber.fingerprint,
            status,
            subscriber.token,
            displayed,
        ),
    )
    if clear_barrier:
        # The subscriber belongs to a generation at or above the session's
        # dismissal barrier by construction (barriers gate every join, cache
        # replay, and successor; eviction removes the subscriber from older
        # work), so an eligible delivery clears the barrier.
        _clear_barrier_min(session, subscriber.fingerprint)
    _push_options_update(session, actor, subscriber.captured_epoch)


def _deliver_guarded(
    subscriber: _PendingSubscriber,
    actor: Any,
    status: str,
    displayed: list | None,
    *,
    clear_barrier: bool = True,
) -> None:
    """Deliver to one subscriber, isolating a per-session failure.

    One session's push failure (for example a lost world clock) must not
    suppress the remaining subscribers' state writes, and a subscriber that
    cannot be settled is logged rather than silently swallowed.
    """
    try:
        _deliver(subscriber, actor, status, displayed, clear_barrier=clear_barrier)
    except Exception as error:
        log_warn(
            "action_options_delivery_failed",
            exc=error,
            context={
                "char": getattr(actor, "pk", 0) or 0,
                "sessid": getattr(subscriber.session, "sessid", 0) or 0,
            },
        )


def _terminal_generation_error(failure: Any) -> Any:
    """Log a generation Deferred that still errbacks after routing."""
    log_warn(
        "action_options_generation_terminal",
        exc=failure.value,
        context={"reason": failure.getErrorMessage()},
    )
    return failure


def _complete_ready(generation: _PendingGeneration, actor: Any, fingerprint_value: str, option_set: Any) -> None:
    if generation.retired:
        return
    _cache_put(fingerprint_value, option_set, generation.generation)
    displayed = list(_display_for(option_set))
    for subscriber in generation.subscribers:
        _deliver_guarded(subscriber, actor, "ready", list(displayed))


def _complete_degraded(
    generation: _PendingGeneration,
    actor: Any,
    fingerprint_value: str,
    *,
    memoize: bool,
    clear_barrier: bool = True,
) -> None:
    if generation.retired:
        return
    if memoize:
        _memo_put(fingerprint_value)
    for subscriber in generation.subscribers:
        _deliver_guarded(
            subscriber, actor, "degraded", None, clear_barrier=clear_barrier
        )


@defer.inlineCallbacks
def _run_generation(generation: _PendingGeneration, client: Any, context: Any, actor: Any, fingerprint_value: str) -> None:
    """One guarded layer call; routes the outcome to cache/memo/state per guard."""
    from world.ai import action_options

    try:
        # A plain ``yield`` on the layer's Deferred: ``generate_action_options``
        # is an ``inlineCallbacks`` function, so it returns a Deferred on every
        # path — the disabled profile resolves it with ``None`` before any
        # transport work, without ever touching the client.
        outcome = yield action_options.generate_action_options(
            context, client, fingerprint=fingerprint_value
        )
    except Exception as error:
        log_warn(
            "action_options_generation_failed",
            exc=error,
            context={"char": getattr(actor, "pk", 0) or 0, "fingerprint": fingerprint_value},
        )
        outcome = None
    if isinstance(outcome, action_options.OptionSet):
        _complete_ready(generation, actor, fingerprint_value, outcome)
    else:
        _complete_degraded(
            generation, actor, fingerprint_value, memoize=client.transport_failed
        )


# ---------------------------------------------------------------------------
# Generation chains: settlement continuation and successor handoff
# ---------------------------------------------------------------------------


def _settle_active(fingerprint_value: str, generation: _PendingGeneration) -> None:
    """Settle one generation's Deferred: registry cleanup plus successor handoff.

    Runs on every settlement of a chain-owned generation (normal completion or
    a retired completion alike). The registry cleanup is identity-guarded
    (``_drop_if_current``), and the chain handoff proceeds only while this
    generation is still the chain's active reference — a detached predecessor
    clears only its own detached reference and never touches a newer
    generation that took the chain, so an obsolete predecessor can never
    remove newer work or start an obsolete replacement generation. When the
    chain's ownership slot is empty and a successor waits on it, that
    successor is started exactly once with a fresh situation derivation.
    """
    _drop_if_current(fingerprint_value, generation)
    chain = _chains.get(fingerprint_value)
    if chain is None:
        return
    is_active = chain.active is generation
    is_detached = chain.detached is generation
    if not is_active and not is_detached:
        return
    if is_active:
        chain.active = None
        successor = chain.successor
        if successor is not None:
            _start_successor(fingerprint_value, chain, successor)
    elif chain.active is None:
        # The chain's ownership slot is empty: a detached predecessor's
        # settlement starts the still-current successor exactly once. When a
        # newer generation already owns the chain, the predecessor settles
        # its own reference only.
        successor = chain.successor
        if successor is not None:
            _start_successor(fingerprint_value, chain, successor)
    if is_detached:
        chain.detached = None
    if chain.empty():
        _chains.pop(fingerprint_value, None)


def _start_successor(
    fingerprint_value: str,
    chain: _GenerationChain,
    successor: _PendingGeneration,
) -> None:
    """Start the chain's queued successor exactly once with fresh derivation.

    The successor registers on the chain and in the pending registry before
    its Deferred starts, so a synchronously settling generation is still
    owned, cleaned up, and handed off by its own settlement. The successor
    derives the actor's situation fresh at settlement time: a vanished
    situation or an actor who moved on settles the queued watchers degraded
    (no memo — this is not a transport failure) without clearing their
    dismissal barriers for the old fingerprint, and drops the successor,
    leaving the post-move lifecycle trigger to derive the next applicable
    situation. Any failure is logged and swallowed so the old generation's
    settlement is never broken.
    """
    try:
        situation = _situation._derive_situation(successor.actor)
        if situation is None:
            _complete_degraded(
                successor,
                successor.actor,
                fingerprint_value,
                memoize=False,
                clear_barrier=False,
            )
            chain.successor = None
            return
        fresh_fingerprint, _vocab, eligible, npcs, monsters, objectives = situation
        if fresh_fingerprint != fingerprint_value:
            log_warn(
                "action_options_successor_situation_stale",
                context={
                    "char": getattr(successor.actor, "pk", 0) or 0,
                    "fingerprint": fingerprint_value,
                    "reason": "situation moved on; queued watchers settled degraded",
                },
            )
            _complete_degraded(
                successor,
                successor.actor,
                fingerprint_value,
                memoize=False,
                clear_barrier=False,
            )
            chain.successor = None
            return
        context = _situation._build_generation_context(
            successor.actor, npcs, monsters, objectives, eligible
        )
        raw_client = (
            chain.client
            if chain.client is not None
            else _clients._build_action_options_client()
        )
        observing_client = _clients._ObservingClient(raw_client)
        chain.active = successor
        chain.successor = None
        _pending[fingerprint_value] = successor
        successor.deferred = _run_generation(
            successor, observing_client, context, successor.actor, fingerprint_value
        )
        successor.deferred.addErrback(_terminal_generation_error)
        successor.deferred.addBoth(lambda _: _settle_active(fingerprint_value, successor))
    except Exception as error:
        log_warn(
            "action_options_successor_handoff_failed",
            exc=error,
            context={
                "char": getattr(successor.actor, "pk", 0) or 0,
                "fingerprint": fingerprint_value,
            },
        )
        try:
            _complete_degraded(
                successor,
                successor.actor,
                fingerprint_value,
                memoize=False,
                clear_barrier=False,
            )
        except Exception as degrade_error:
            log_warn(
                "action_options_successor_degrade_failed",
                exc=degrade_error,
                context={
                    "char": getattr(successor.actor, "pk", 0) or 0,
                    "fingerprint": fingerprint_value,
                },
            )
        chain.successor = None
