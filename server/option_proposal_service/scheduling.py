"""Public scheduling and eviction entry points.

``schedule_action_options`` is the single production caller path into the
generation lifecycle (it imports the lifecycle layer directly — the package
layering is strictly acyclic), and ``evict`` is the state-only dismissal
contract used by the ``options.dismiss`` adapter. Both are fire-and-forget
and non-raising by contract.

The client-construction seam resolves through
:mod:`server.option_proposal_service.clients` (its owner) at call time, so
patching ``clients._build_action_options_client`` steers both the preflight
construction here and the successor handoff's fallback construction.
"""

from typing import Any

from twisted.internet import defer

from world.observability import log_warn

from server.option_proposal_service import clients as _clients
from server.option_proposal_service import lifecycle as _lifecycle
from server.option_proposal_service.state import (
    _cache,
    _chain_for,
    _chains,
    _current_generation,
    _negative_memo,
    _next_generation,
    _options_state,
    _pending,
    _PendingGeneration,
    _PendingSubscriber,
    _set_barrier_min,
    _set_options_state,
    _state,
)
from server.option_proposal_service.situation import _build_generation_context, _derive_situation
from server.option_proposal_service.trigger import _handle_session_trigger


def schedule_action_options(
    actor: Any,
    *,
    watchers: "tuple[tuple[Any, str], ...] | list[tuple[Any, str]]",
    client: Any = None,
) -> "defer.Deferred | None":
    """Schedule the action-options trigger for ``actor``'s current situation.

    ``watchers`` is the relocation trigger's ``watchers_for(actor)`` result:
    ``(session, captured_epoch)`` pairs. Fire-and-forget: every synchronous
    failure (a vanished room, a malformed context, a vanished clock, a
    broken client construction) is logged and swallowed; a preflight
    failure degrades the affected sessions in place so no session is left
    in ``generating``. The return value is the fingerprint's in-flight
    generation's Deferred — freshly started, or the existing one when it
    survives the trigger (a new watcher attached, or every watcher was a
    replay/cache/memo no-op) — and ``None`` when no generation is in
    flight (pure replays, memo hits, cache hits, preflight no-ops, and
    preflight failures), for caller observability; never an exception.
    """
    try:
        situation = _derive_situation(actor)
        if situation is None:
            log_warn(
                "action_options_schedule_skipped",
                context={
                    "char": getattr(actor, "pk", 0) or 0,
                    "reason": "no location at trigger time",
                },
            )
            return None
        fingerprint_value, _vocab, eligible, npcs, monsters, objectives = situation
        new_subscribers: list[_PendingSubscriber] = []
        for session, captured_epoch in watchers:
            _handle_session_trigger(
                session, actor, str(captured_epoch), fingerprint_value, new_subscribers
            )
        if not new_subscribers:
            generation = _pending.get(fingerprint_value)
            return generation.deferred if generation is not None else None
        generation = _PendingGeneration(_next_generation(fingerprint_value), actor)
        generation.subscribers = new_subscribers
        _pending[fingerprint_value] = generation
        try:
            context = _build_generation_context(actor, npcs, monsters, objectives, eligible)
            if client is None:
                client = _clients._build_action_options_client()
        except Exception as error:
            # Any pre-transport failure (context build or client construction)
            # must retire the generation and settle the sessions as degraded;
            # the failure was never observed at the client boundary, so no
            # memo. Leaving a deferred-less generation in _pending would strand
            # every watcher in "generating" for the life of the process.
            log_warn(
                "action_options_preflight_failed",
                exc=error,
                context={"char": getattr(actor, "pk", 0) or 0, "fingerprint": fingerprint_value},
            )
            _pending.pop(fingerprint_value, None)
            _lifecycle._complete_degraded(generation, actor, fingerprint_value, memoize=False)
            return None
        observing_client = _clients._ObservingClient(client)
        chain = _chain_for(fingerprint_value, actor)
        chain.active = generation
        chain.client = client
        # ``_run_generation`` is an inlineCallbacks function: calling it
        # already yields a Deferred, so no ensureDeferred wrapper is needed.
        generation.deferred = _lifecycle._run_generation(
            generation, observing_client, context, actor, fingerprint_value
        )
        generation.deferred.addErrback(_lifecycle._terminal_generation_error)
        generation.deferred.addBoth(
            lambda _: _lifecycle._settle_active(fingerprint_value, generation)
        )
        return generation.deferred
    except Exception as error:
        log_warn(
            "action_options_scheduling_failed",
            exc=error,
            context={"char": getattr(actor, "pk", 0) or 0},
        )
        return None


def evict(session: Any, actor: Any) -> bool:
    """Dismiss the displayed options for one session (state-only contract).

    Reads the fingerprint the session currently displays, evicts it from the
    cache, memo, and joinable pending registry (retiring and removing an
    emptied generation immediately by identity — its Deferred completion stays
    detached under the chain solely to start a still-current successor), drops
    the session from any queued successor, records the minimum displayable
    generation number in the session's bounded barrier store, bumps the
    session's generation token so an in-flight completion cannot deliver, and
    sets the state to ``unavailable``. Returns ``True`` on success and
    ``False`` when the eviction could not be applied (the state is left
    unchanged); never raises. Never sends: the dismissal's single ``ui_update``
    is published by the dispatcher completion path after the ``options.dismiss``
    adapter declares ``context_actions`` affected (dismiss-options-action
    design D1).
    """
    try:
        actor_id = str(getattr(actor, "pk", ""))
        state = _options_state(session)
        fingerprint_value = state.get("fingerprint") if state is not None else None
        token = int(state.get("generation_token", 0)) if state is not None else 0

        if isinstance(fingerprint_value, str) and fingerprint_value:
            _cache.pop(fingerprint_value, None)
            _negative_memo.pop(fingerprint_value, None)
            generation = _pending.get(fingerprint_value)
            if generation is not None:
                generation.subscribers = [
                    subscriber
                    for subscriber in generation.subscribers
                    if subscriber.session is not session
                ]
                if not generation.subscribers:
                    # The final subscriber is gone: remove the generation from
                    # the joinable registry immediately by identity. If a
                    # successor waits on the chain, the generation's Deferred
                    # completion remains detached there solely to start it.
                    generation.retired = True
                    _pending.pop(fingerprint_value, None)
                    chain = _chains.get(fingerprint_value)
                    if chain is not None and chain.active is generation:
                        chain.detached = generation
                        chain.active = None
            chain = _chains.get(fingerprint_value)
            if chain is not None and chain.successor is not None:
                successor = chain.successor
                successor.subscribers = [
                    subscriber
                    for subscriber in successor.subscribers
                    if subscriber.session is not session
                ]
                if not successor.subscribers:
                    chain.successor = None
            _set_barrier_min(
                session, fingerprint_value, _current_generation(fingerprint_value) + 1
            )

        token += 1
        _set_options_state(
            session, _state(actor_id, None, "unavailable", token, None)
        )
        return True
    except Exception as error:
        log_warn(
            "action_options_evict_failed",
            exc=error,
            context={
                "char": getattr(actor, "pk", 0) or 0,
                "sessid": getattr(session, "sessid", 0) or 0,
            },
        )
        return False
