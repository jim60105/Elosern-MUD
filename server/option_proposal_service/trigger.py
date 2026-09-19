"""Per-session trigger flow: the decision tree for one watcher.

Runs the join/replay/degrade/successor-queue decision for one watcher of one
triggered situation. Reads and writes only the process-local stores owned by
:mod:`server.option_proposal_service.state`, so the module stays acyclic on
top of the state layer.
"""

from typing import Any

from server.option_proposal_service.state import (
    _barrier_min,
    _cache_get,
    _chain_for,
    _chains,
    _clear_barrier_min,
    _memo_live,
    _next_generation,
    _options_state,
    _pending,
    _PendingGeneration,
    _PendingSubscriber,
    _push_options_update,
    _set_options_state,
    _state,
)


def _handle_session_trigger(
    session: Any,
    actor: Any,
    captured_epoch: str,
    fingerprint_value: str,
    new_subscribers: list[_PendingSubscriber],
) -> None:
    """Run the decision flow for one watcher of one triggered situation.

    A ready display republishes without scheduling; a degraded display for a
    situation whose negative memo is still live republishes the rule-card
    refresh without transport; once the memo expires (or none exists) the
    trigger attempts generation again. A live negative memo for a fresh
    session degrades in place; a cache hit whose generation number meets the
    session's dismissal barrier publishes the cached set; otherwise the
    session transitions to ``generating`` (publishing the transition only
    once) and either joins the in-flight generation, queues on the chain's
    successor when an older in-flight generation cannot be joined, or
    collects to start one.
    """
    actor_id = str(getattr(actor, "pk", ""))
    state = _options_state(session)
    if state is not None and str(state.get("owner_actor_id", "")) != actor_id:
        state = None
    token = int(state.get("generation_token", 0)) if state is not None else 0
    barrier = _barrier_min(session, fingerprint_value)

    if (
        state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "ready"
        and barrier == 0
    ):
        # A ready display is a valid result for this situation; republish the
        # session's own displayed set (never the cache) and schedule nothing.
        # A dismissal barrier can never coexist with a ready display (eligible
        # delivery clears it), so the gate is purely defensive.
        _push_options_update(session, actor, captured_epoch)
        return

    if (
        state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "degraded"
        and _memo_live(fingerprint_value)
    ):
        # Still inside the transport-failure window: re-derive the rule cards
        # fresh and refresh; no transport work, no scheduling.
        _push_options_update(session, actor, captured_epoch)
        return

    if _memo_live(fingerprint_value):
        token += 1
        _set_options_state(
            session, _state(actor_id, fingerprint_value, "degraded", token, None)
        )
        _push_options_update(session, actor, captured_epoch)
        return

    cached = _cache_get(fingerprint_value)
    if cached is not None:
        option_set, displayed, generation = cached
        if generation >= barrier:
            token += 1
            _set_options_state(
                session, _state(actor_id, fingerprint_value, "ready", token, list(displayed))
            )
            if barrier:
                _clear_barrier_min(session, fingerprint_value)
            _push_options_update(session, actor, captured_epoch)
            return

    # -- pending-generation decision -----------------------------------------
    active = _pending.get(fingerprint_value)
    if active is not None and (active.retired or active.generation < barrier):
        below_barrier = active is not None and not active.retired
        active = None
    else:
        below_barrier = False

    if (
        active is not None
        and state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "generating"
        and any(sub.session is session for sub in active.subscribers)
    ):
        return

    chain = _chains.get(fingerprint_value)
    successor = chain.successor if chain is not None else None
    if (
        successor is not None
        and state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "generating"
        and any(sub.session is session for sub in successor.subscribers)
    ):
        return

    if successor is not None and successor.generation < barrier:
        # The only queued successor predates the session's dismissal barrier
        # (a later dismissal while older work still waits on the chain):
        # joining it would later deliver pre-dismiss content and clear the
        # barrier. The session settles degraded in place — memo-free, with
        # the barrier standing — and a later trigger starts fresh work above
        # the barrier.
        token += 1
        was_generating = state is not None and state.get("status") == "generating"
        _set_options_state(
            session, _state(actor_id, fingerprint_value, "degraded", token, None)
        )
        if not was_generating:
            _push_options_update(session, actor, captured_epoch)
        return

    token += 1
    was_generating = state is not None and state.get("status") == "generating"
    _set_options_state(
        session, _state(actor_id, fingerprint_value, "generating", token, None)
    )
    if not was_generating:
        _push_options_update(session, actor, captured_epoch)
    subscriber = _PendingSubscriber(session, token, captured_epoch, fingerprint_value)
    if active is not None:
        active.subscribers.append(subscriber)
        return
    if successor is not None:
        successor.subscribers.append(subscriber)
        return
    if below_barrier:
        # An older in-flight generation still owned by other watchers cannot
        # be joined or replayed (its number predates the session's dismissal
        # barrier): queue this session on a fresh successor that starts
        # exactly once when the old generation settles.
        if chain is None:
            chain = _chain_for(fingerprint_value, actor)
        successor = _PendingGeneration(_next_generation(fingerprint_value), actor)
        chain.successor = successor
        successor.subscribers.append(subscriber)
        return
    new_subscribers.append(subscriber)
