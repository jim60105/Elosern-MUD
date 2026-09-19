"""Process-local service state: stores, clock seam, test reset, and helpers.

Every mutable module global of the action-options trigger service lives in
this one module: the per-fingerprint option cache, the transport-failure
negative memo, the in-flight pending registry, the generation chains, and the
generation counters, plus the ``_clock`` seam. The package ``__getattr__``
delegates the historical ``server.option_proposal_service.<name>`` reads to
these objects, so a package-path mutation or reset always hits the single
dicts the call path uses, and ``_reset_service_state`` (the test seam) clears
the same objects. Time is funneled through ``_clock_now`` exactly as before:
the only ``_clock()`` lookup lives here, which is why the clock patch targets
this module.

Also owned here: the pending/chain value objects, the session options-state
helpers, the bounded option cache and memo helpers, the generation counters,
and the per-session dismissal-barrier store. All imports are standard-library
plus the observability facade, so the module stays cold importable like the
service it backs.
"""

import time
from collections import OrderedDict
from typing import Any

# Mirrors the layer's caps (world.ai.action_options.MAX_OPTIONSET_CACHE_ENTRIES
# / NEGATIVE_MEMO_TTL): the parity is pinned by a test so the two cannot drift.
MAX_OPTIONSET_CACHE_ENTRIES = 16
NEGATIVE_MEMO_TTL = 30


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
