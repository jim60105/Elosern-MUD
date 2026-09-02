"""Composition root scheduling AI action-options generations (trigger service).

``schedule_action_options`` is the single production caller of
``world.ai.action_options.generate_action_options``. It is the scheduled,
cached, session-scoped delivery layer over the already-implemented schema,
prompts, and layer:

* **situation fingerprint** — one stable hash naming the situation (room key,
  present identities, the canonical eligible-affordance digest, and the
  displayed public-state digest), never the moment, derived through the
  shared read-only ``web.webclient.presentation.fingerprints`` derivation so
  scheduling and presentation can never drift;
* **per-fingerprint LRU cache** (cap 16) — one generation per residency, each
  entry tagged with its ephemeral generation number, with the session's own
  ``displayed`` set taking precedence over the cache on replay;
* **in-flight pending registry** with per-session generation tokens, captured
  coordinator epochs, and monotonic per-fingerprint generation numbers — one
  shared generation per situation, delivery muted when the session dismissed
  or re-triggered mid-flight;
* **per-fingerprint generation chains** — one joinable active generation and
  at most one successor; a dismissing session that cannot join an older
  in-flight generation queues on the successor, which starts exactly once
  (through an identity-guarded detached predecessor handoff) with a fresh
  situation derivation;
* **per-session dismissal barriers** on ``session.ndb.options_barriers`` — the
  minimum displayable generation per fingerprint, capped at the cache
  capacity, cleared on puppet change/unpuppet and on eligible delivery;
* **negative memo** (30 s) written only for transport failures, observed
  through a thin client wrapper (the design D7 controlled-failure fallback,
  standing in for the deferred layer typed-outcome amendment);
* **per-session options state** on ``session.ndb.options_state`` — the
  single source the ``context_actions`` presenter reads;
* **epoch-guarded push** of the ``context_actions`` panel through
  ``coordinator.publish_panel_update``.

It sits in ``server/`` for import-direction reasons (scanned by neither the
deterministic-path ban nor the ``world/ai`` transport boundary), every
``world.ai`` import is deferred into the call path so a cold import binds no
guardrail logger, and the scheduling never blocks arrival or raises to the
caller — a vanished room or malformed context logs a bounded diagnostic and
resolves to nothing. It writes only ephemeral cache and presentation state,
never canonical game state.
"""

import time
from collections import OrderedDict
from typing import Any

from twisted.internet import defer

from world.observability import log_warn

# Mirrors the layer's caps (world.ai.action_options.MAX_OPTIONSET_CACHE_ENTRIES
# / NEGATIVE_MEMO_TTL): the parity is pinned by a test so the two cannot drift.
MAX_OPTIONSET_CACHE_ENTRIES = 16
NEGATIVE_MEMO_TTL = 30

# Prompt affordance rank — objective-relevant (targeted) entries first, then
# movement, then inspection, then the idle baseline; stable within a rank.
_PROMPT_AFFORDANCE_RANKS = {
    "explore.talk_scripted": 0,
    "explore.talk_freeform": 0,
    "explore.engage": 0,
    "explore.move": 1,
    "explore.look": 2,
}


class _OfflineStubClient:
    """Non-``None`` client injected when the ``action_options`` profile is off.

    The layer's gate resolves the degrade before any transport work, so the
    stub is never called; its ``get_response`` fails loudly if it ever is,
    rather than silently half-opening a connection.
    """

    def get_response(self, descriptor):
        raise AssertionError(
            "offline stub client must never be called; the action_options "
            "profile degrades before any transport work"
        )


class _ObservingClient:
    """Thin wrapper that observes transport failures on the layer client.

    ``LLMTransportError`` — raised synchronously or errbacked on the returned
    Deferred — marks ``transport_failed``. This is the memo-discrimination
    signal: a degraded outcome with an observed transport failure is the
    memoized class; every other degrade (validation exhaustion, prompt
    unavailability, a disabled profile that never reaches the client) is not.
    The wrapper forwards the descriptor and every result untouched to the
    wrapped client, so the layer and its test doubles see no difference.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.transport_failed = False

    def get_response(self, descriptor: Any):
        from world.ai.errors import LLMTransportError

        try:
            result = self._inner.get_response(descriptor)
        except LLMTransportError:
            self.transport_failed = True
            raise
        if hasattr(result, "addErrback"):
            result = result.addErrback(self._observe)
        return result

    def _observe(self, failure: Any) -> Any:
        from world.ai.errors import LLMTransportError

        if failure.check(LLMTransportError):
            self.transport_failed = True
        return failure


class _PendingSubscriber:
    __slots__ = ("session", "token", "captured_epoch", "fingerprint")

    def __init__(self, session: Any, token: int, captured_epoch: str, fingerprint: str) -> None:
        self.session = session
        self.token = token
        self.captured_epoch = captured_epoch
        self.fingerprint = fingerprint


class _PendingGeneration:
    __slots__ = ("subscribers", "retired", "deferred", "generation", "actor")

    def __init__(self, generation: int, actor: Any) -> None:
        self.subscribers: list[_PendingSubscriber] = []
        self.retired = False
        self.deferred: "defer.Deferred | None" = None
        self.generation = generation
        self.actor = actor


class _GenerationChain:
    """The per-fingerprint owner of one active and at most one successor.

    ``active`` is the joinable in-flight generation; ``successor`` is a queued
    generation that may not start while ``active`` lives; ``detached`` is the
    identity-bearing reference to an active generation whose final subscriber
    dismissed it — kept solely so its eventual Deferred settlement starts the
    still-current successor exactly once, and only while no newer generation
    owns the chain. ``actor`` is the player whose situation the chain names
    (every watcher of one situation shares it) and ``client`` is the raw
    transport client the active generation used, reused by the successor under
    a fresh observing wrapper so an injected client survives the handoff
    without carrying stale observation state.
    """

    __slots__ = ("active", "successor", "detached", "actor", "client", "fingerprint")

    def __init__(self, fingerprint: str, actor: Any) -> None:
        self.active: _PendingGeneration | None = None
        self.successor: _PendingGeneration | None = None
        self.detached: _PendingGeneration | None = None
        self.actor = actor
        self.client: Any = None
        self.fingerprint = fingerprint

    def empty(self) -> bool:
        return (
            self.active is None
            and self.successor is None
            and self.detached is None
        )


# Process-local stores: gone with the worker, exactly the service's scope.
_cache: "OrderedDict[str, tuple[Any, list[dict[str, Any]], int]]" = OrderedDict()
_negative_memo: dict[str, float] = {}
_pending: dict[str, _PendingGeneration] = {}
_chains: dict[str, _GenerationChain] = {}
_generation_counters: dict[str, int] = {}
_clock = time.monotonic


def _clock_now() -> float:
    return _clock()


def _reset_service_state() -> None:
    """Empty the cache, memo, pending registry, chains, and counters (test seam)."""
    _cache.clear()
    _negative_memo.clear()
    _pending.clear()
    _chains.clear()
    _generation_counters.clear()


# ---------------------------------------------------------------------------
# Session options-state helpers
# ---------------------------------------------------------------------------


def _options_state(session: Any) -> dict[str, Any] | None:
    ndb = getattr(session, "ndb", None)
    state = getattr(ndb, "options_state", None) if ndb is not None else None
    return state if isinstance(state, dict) else None


def _set_options_state(session: Any, state: dict[str, Any] | None) -> None:
    ndb = getattr(session, "ndb", None)
    if ndb is not None:
        ndb.options_state = state


def _state(
    actor_id: str,
    fingerprint: str,
    status: str,
    token: int,
    displayed: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    return {
        "owner_actor_id": actor_id,
        "fingerprint": fingerprint,
        "status": status,
        "generation_token": int(token),
        "displayed": displayed,
    }


def _push_options_update(session: Any, actor: Any, captured_epoch: str) -> None:
    """Push the session's current options state through the epoch-guarded push."""
    from web.webclient.presentation.coordinator import publish_panel_update
    from web.webclient.presentation.ingress import build_presentation_context
    from web.webclient.presentation.registry import build_production_registry

    context = build_presentation_context(session, actor)
    panels = {"context_actions": build_production_registry().render("context_actions", context)}
    publish_panel_update(session, actor, panels, context=context, expected_epoch=captured_epoch)


# ---------------------------------------------------------------------------
# Cache, memo, pending
# ---------------------------------------------------------------------------


def _display_for(option_set: Any) -> list[dict[str, Any]]:
    """The wire-safe card dicts for one cached OptionSet."""
    return [
        {
            "kind": card.kind,
            "action_code": card.action_code,
            "label": card.label,
            "params": dict(card.params),
            "hint": card.hint,
        }
        for card in option_set.cards
    ]


def _cache_get(fingerprint: str) -> "tuple[Any, list[dict[str, Any]], int] | None":
    entry = _cache.get(fingerprint)
    if entry is not None:
        _cache.move_to_end(fingerprint)
    return entry


def _cache_put(fingerprint: str, option_set: Any, generation: int) -> None:
    """Cache one generation's OptionSet under its generation number.

    An older completion never overwrites a newer cache entry: the write is
    refused when an entry with a strictly newer generation number already
    sits on the fingerprint.
    """
    existing = _cache.get(fingerprint)
    if existing is not None and existing[2] > generation:
        return
    _cache[fingerprint] = (option_set, _display_for(option_set), generation)
    _cache.move_to_end(fingerprint)
    while len(_cache) > MAX_OPTIONSET_CACHE_ENTRIES:
        _cache.popitem(last=False)


def _memo_live(fingerprint: str) -> bool:
    expires = _negative_memo.get(fingerprint)
    if expires is None:
        return False
    if expires <= _clock_now():
        del _negative_memo[fingerprint]
        return False
    return True


def _drop_if_current(fingerprint: str, generation: _PendingGeneration) -> None:
    """Remove a completed generation from the registry when it is still current.

    Identity-guarded: a retired generation whose slot was already taken by a
    newer generation (or was removed at eviction) is never removed twice.
    """
    if _pending.get(fingerprint) is generation:
        _pending.pop(fingerprint, None)


def _memo_put(fingerprint: str) -> None:
    for expired in [key for key, when in _negative_memo.items() if when <= _clock_now()]:
        del _negative_memo[expired]
    _negative_memo[fingerprint] = _clock_now() + NEGATIVE_MEMO_TTL


# ---------------------------------------------------------------------------
# Generation numbers and dismissal barriers
# ---------------------------------------------------------------------------


def _next_generation(fingerprint: str) -> int:
    """The next monotonic ephemeral generation number for one fingerprint."""
    _generation_counters[fingerprint] = _generation_counters.get(fingerprint, 0) + 1
    return _generation_counters[fingerprint]


def _current_generation(fingerprint: str) -> int:
    """The highest generation number issued for one fingerprint (0 when none)."""
    return _generation_counters.get(fingerprint, 0)


def _barrier_store(session: Any) -> OrderedDict | None:
    ndb = getattr(session, "ndb", None)
    store = getattr(ndb, "options_barriers", None) if ndb is not None else None
    return store if isinstance(store, OrderedDict) else None


def _barrier_min(session: Any, fingerprint: str) -> int:
    """The session's minimum displayable generation for ``fingerprint``.

    ``0`` (the absence marker) when no dismissal barrier is recorded — a
    barrier is a positive number by construction, so ``0`` means "no gate".
    """
    store = _barrier_store(session)
    if store is None:
        return 0
    value = store.get(fingerprint, 0)
    return value if isinstance(value, int) and value > 0 else 0


def _set_barrier_min(session: Any, fingerprint: str, minimum: int) -> None:
    """Record the session's minimum displayable generation for a fingerprint.

    The store is a separate bounded ``session.ndb`` mapping that never alters
    the exact ``options_state`` shape; it is capped at the option-cache
    capacity (the oldest entry falls out under pressure).
    """
    ndb = getattr(session, "ndb", None)
    if ndb is None:
        return
    store = _barrier_store(session)
    if store is None:
        store = OrderedDict()
        ndb.options_barriers = store
    store[fingerprint] = minimum
    store.move_to_end(fingerprint)
    while len(store) > MAX_OPTIONSET_CACHE_ENTRIES:
        store.popitem(last=False)


def _clear_barrier_min(session: Any, fingerprint: str) -> None:
    """Drop a dismissal barrier after an eligible outcome was received."""
    store = _barrier_store(session)
    if store is not None:
        store.pop(fingerprint, None)


def _chain_for(fingerprint: str, actor: Any) -> _GenerationChain:
    """Return the per-fingerprint generation chain, creating it on demand."""
    chain = _chains.get(fingerprint)
    if chain is None:
        chain = _GenerationChain(fingerprint, actor)
        _chains[fingerprint] = chain
    return chain


def _build_action_options_client() -> Any:
    """Build the injected ``action_options`` client for one scheduling call."""
    from world.ai.client import OpenAICompatClient
    from world.ai.profiles import get_profile

    profile = get_profile("action_options")
    if profile.enabled:
        return OpenAICompatClient(profile)
    return _OfflineStubClient()


# ---------------------------------------------------------------------------
# Situation derivation
# ---------------------------------------------------------------------------


def _derive_situation(
    actor: Any,
) -> "tuple[str, Any, Any, list[Any], list[Any], tuple] | None":
    """Derive ``(fingerprint, vocab, eligible, npcs, monsters, objectives)``.

    Delegates to the shared read-only derivation in
    ``web.webclient.presentation.fingerprints`` — the same helper the
    presentation-context factory consumes — so scheduling and presentation can
    never drift on what names the situation. The helper import is
    function-local (this module stays cold importable). Returns ``None`` when
    the trigger has no room to name the situation.
    """
    from web.webclient.presentation.fingerprints import derive_exploration_situation

    return derive_exploration_situation(actor)


# ---------------------------------------------------------------------------
# Generation context
# ---------------------------------------------------------------------------


def _prompt_affordances(eligible: Any) -> tuple[Any, ...]:
    """The bounded, deterministically ranked affordance list for one prompt.

    The full eligible list is what the *fingerprint* digests; the prompt list
    is capped at the layer's bound with targeted entries first, movement next,
    inspection, and the idle baseline last, tie-broken by vocabulary order.
    """
    from world.ai.action_options import MAX_AFFORDANCES

    def _rank(entry: Any) -> int:
        return _PROMPT_AFFORDANCE_RANKS.get(entry.action_id, 3)

    return tuple(sorted(eligible, key=_rank))[:MAX_AFFORDANCES]


def _build_generation_context(
    actor: Any,
    npcs: list[Any],
    monsters: list[Any],
    objectives: tuple,
    eligible: Any,
) -> Any:
    """Assemble the frozen, bounded layer context from read-only world data."""
    from world.ai.action_options import (
        MAX_NARRATIVE_TAIL_LENGTH,
        MAX_OBJECTIVE_LENGTH,
        MAX_ROOM_NAME_LENGTH,
        MAX_ROOM_SUMMARY_LENGTH,
        build_options_context,
    )
    from world.rules.dialogue import dialogue_key_for
    from world.rules.persona import PersonaStore
    from web.webclient.presentation.fingerprints import public_tier_labels

    location = actor.location
    room_name = str(
        getattr(location.db, "name", None) or getattr(location, "key", "") or "???"
    )[:MAX_ROOM_NAME_LENGTH]
    room_summary = str(getattr(location.db, "desc", None) or "")[:MAX_ROOM_SUMMARY_LENGTH]
    narrative_tail = str(
        getattr(location.db, "scene_flavor", None) or ""
    )[-MAX_NARRATIVE_TAIL_LENGTH:]
    objective: str | None = objectives[0][2][:MAX_OBJECTIVE_LENGTH] if objectives else None

    tiers = dict(public_tier_labels(actor, npcs))
    npc_entries = []
    for npc in npcs:
        npc_entries.append(
            {
                "npc_id": int(npc.pk),
                "display_name": str(getattr(npc, "key", None) or "???"),
                "dialogue_key": dialogue_key_for(npc),
                "persona_digest": PersonaStore(npc).flatten() or "",
                "public_tier": tiers.get(int(npc.pk)),
            }
        )
    monster_entries = []
    for monster in monsters:
        threat_tier = getattr(monster, "threat_tier", None)
        monster_entries.append(
            {
                "monster_id": int(monster.pk),
                "display_name": str(getattr(monster, "key", None) or "???"),
                "threat_tier": str(threat_tier) if threat_tier is not None else None,
            }
        )
    secret_tokens = []
    for npc in npcs:
        handler = getattr(npc, "relations", None)
        if handler is not None:
            secret_tokens.append(str(handler.affinity_for(actor)))

    return build_options_context(
        room_name=room_name,
        room_summary=room_summary,
        narrative_tail=narrative_tail,
        npc_entries=npc_entries,
        monster_entries=monster_entries,
        objective=objective,
        affordances=_prompt_affordances(eligible),
        secret_tokens=secret_tokens,
    )


# ---------------------------------------------------------------------------
# Per-session trigger flow
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Generation lifecycle
# ---------------------------------------------------------------------------


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
        situation = _derive_situation(successor.actor)
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
        context = _build_generation_context(
            successor.actor, npcs, monsters, objectives, eligible
        )
        raw_client = chain.client if chain.client is not None else _build_action_options_client()
        observing_client = _ObservingClient(raw_client)
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


# ---------------------------------------------------------------------------
# Public scheduling and eviction
# ---------------------------------------------------------------------------


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
                client = _build_action_options_client()
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
            _complete_degraded(generation, actor, fingerprint_value, memoize=False)
            return None
        observing_client = _ObservingClient(client)
        chain = _chain_for(fingerprint_value, actor)
        chain.active = generation
        chain.client = client
        # ``_run_generation`` is an inlineCallbacks function: calling it
        # already yields a Deferred, so no ensureDeferred wrapper is needed.
        generation.deferred = _run_generation(
            generation, observing_client, context, actor, fingerprint_value
        )
        generation.deferred.addErrback(_terminal_generation_error)
        generation.deferred.addBoth(lambda _: _settle_active(fingerprint_value, generation))
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
