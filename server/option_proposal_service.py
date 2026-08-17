"""Composition root scheduling AI action-options generations (trigger service).

``schedule_action_options`` is the single production caller of
``world.ai.action_options.generate_action_options``. It is the scheduled,
cached, session-scoped delivery layer over the already-implemented schema,
prompts, and layer:

* **situation fingerprint** — one stable hash naming the situation (room key,
  present identities, the canonical eligible-affordance digest, and the
  displayed public-state digest), never the moment;
* **per-fingerprint LRU cache** (cap 16) — one generation per residency, with
  the session's own ``displayed`` set taking precedence over the cache on
  replay;
* **in-flight pending registry** with per-session generation tokens and
  captured coordinator epochs — one shared generation per situation, delivery
  muted when the session dismissed or re-triggered mid-flight;
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

import logging
import time
from collections import OrderedDict
from typing import Any

from twisted.internet import defer

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

logger = logging.getLogger(__name__)


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
    __slots__ = ("subscribers", "retired", "deferred")

    def __init__(self) -> None:
        self.subscribers: list[_PendingSubscriber] = []
        self.retired = False
        self.deferred: "defer.Deferred | None" = None


# Process-local stores: gone with the worker, exactly the service's scope.
_cache: "OrderedDict[str, tuple[Any, list[dict[str, Any]]]]" = OrderedDict()
_negative_memo: dict[str, float] = {}
_pending: dict[str, _PendingGeneration] = {}
_clock = time.monotonic


def _log(message: str) -> None:
    log = logger.log_err if hasattr(logger, "log_err") else logger.warning
    try:
        log("action options: %s" % message)
    except Exception:
        pass


def _clock_now() -> float:
    return _clock()


def _reset_service_state() -> None:
    """Empty the cache, memo, and pending registry (test seam)."""
    _cache.clear()
    _negative_memo.clear()
    _pending.clear()


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


def _cache_get(fingerprint: str) -> "tuple[Any, list[dict[str, Any]]] | None":
    entry = _cache.get(fingerprint)
    if entry is not None:
        _cache.move_to_end(fingerprint)
    return entry


def _cache_put(fingerprint: str, option_set: Any) -> None:
    _cache[fingerprint] = (option_set, _display_for(option_set))
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
    """Remove a completed generation from the registry when it is still current."""
    if _pending.get(fingerprint) is generation:
        _pending.pop(fingerprint, None)


def _memo_put(fingerprint: str) -> None:
    for expired in [key for key, when in _negative_memo.items() if when <= _clock_now()]:
        del _negative_memo[expired]
    _negative_memo[fingerprint] = _clock_now() + NEGATIVE_MEMO_TTL


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

    Returns ``None`` when the trigger has no room to name the situation.
    """
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from web.webclient.actions.node_ids import node_id_for_location
    from web.webclient.presentation.affordances import (
        eligible_affordance_digest,
        exploration_affordances,
        in_exploration_mode,
        suggestible_candidates,
    )
    from web.webclient.presentation.fingerprints import (
        displayed_objective_identity,
        fingerprint,
        public_state_digest,
        public_tier_labels,
    )

    if not in_exploration_mode(actor):
        return None
    location = getattr(actor, "location", None)
    if location is None:
        return None
    room_key = node_id_for_location(location)
    if room_key is None:
        try:
            room_key = "room:%d" % int(location.id)
        except Exception:
            return None

    npcs: list[Any] = []
    monsters: list[Any] = []
    actor_id = getattr(actor, "pk", None)
    for occupant in list(getattr(location, "contents", ()) or ()):
        if getattr(occupant, "pk", None) == actor_id:
            continue
        if isinstance(occupant, Monster):
            monsters.append(occupant)
        elif isinstance(occupant, NPC):
            npcs.append(occupant)
    npcs.sort(key=lambda entity: int(entity.pk))
    monsters.sort(key=lambda entity: int(entity.pk))

    vocab = exploration_affordances(actor)
    eligible = suggestible_candidates(vocab, actor=actor)
    objectives = displayed_objective_identity(actor)
    tiers = public_tier_labels(actor, npcs)
    digest_value = fingerprint(
        room_key,
        (int(entity.pk) for entity in npcs),
        (int(entity.pk) for entity in monsters),
        eligible_affordance_digest(eligible),
        public_state_digest(objectives, tiers),
    )
    return digest_value, vocab, eligible, npcs, monsters, objectives


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

    A ready display republishes without scheduling. A degraded display for a
    situation whose negative memo is still live republishes the rule-card
    refresh without transport; once the memo expires (or none exists) the
    trigger attempts generation again. A live negative memo for a fresh
    session degrades in place; a cache hit publishes the cached set;
    otherwise the session transitions to ``generating`` (publishing the
    transition only once) and either joins the in-flight generation or
    collects to start one.
    """
    actor_id = str(getattr(actor, "pk", ""))
    state = _options_state(session)
    if state is not None and str(state.get("owner_actor_id", "")) != actor_id:
        state = None
    token = int(state.get("generation_token", 0)) if state is not None else 0

    if (
        state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "ready"
    ):
        # A ready display is a valid result for this situation; republish the
        # session's own displayed set (never the cache) and schedule nothing.
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
        option_set, displayed = cached
        token += 1
        _set_options_state(
            session, _state(actor_id, fingerprint_value, "ready", token, list(displayed))
        )
        _push_options_update(session, actor, captured_epoch)
        return

    generation = _pending.get(fingerprint_value)
    if generation is not None and generation.retired:
        generation = None
    if (
        generation is not None
        and state is not None
        and state.get("fingerprint") == fingerprint_value
        and state.get("status") == "generating"
        and any(sub.session is session for sub in generation.subscribers)
    ):
        return

    token += 1
    was_generating = state is not None and state.get("status") == "generating"
    _set_options_state(
        session, _state(actor_id, fingerprint_value, "generating", token, None)
    )
    if not was_generating:
        _push_options_update(session, actor, captured_epoch)
    if generation is not None:
        generation.subscribers.append(
            _PendingSubscriber(session, token, captured_epoch, fingerprint_value)
        )
        return
    new_subscribers.append(
        _PendingSubscriber(session, token, captured_epoch, fingerprint_value)
    )


# ---------------------------------------------------------------------------
# Generation lifecycle
# ---------------------------------------------------------------------------


def _deliver(subscriber: _PendingSubscriber, actor: Any, status: str, displayed: list | None) -> None:
    """Deliver one outcome to one subscriber under the token guard."""
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
    _push_options_update(session, actor, subscriber.captured_epoch)


def _deliver_guarded(
    subscriber: _PendingSubscriber,
    actor: Any,
    status: str,
    displayed: list | None,
) -> None:
    """Deliver to one subscriber, isolating a per-session failure.

    One session's push failure (for example a lost world clock) must not
    suppress the remaining subscribers' state writes, and a subscriber that
    cannot be settled is logged rather than silently swallowed.
    """
    try:
        _deliver(subscriber, actor, status, displayed)
    except Exception as error:
        _log(
            "delivery to session %s failed: %s: %s"
            % (getattr(subscriber.session, "sessid", "?"), type(error).__name__, error)
        )


def _terminal_generation_error(failure: Any) -> Any:
    """Log a generation Deferred that still errbacks after routing."""
    try:
        _log("generation terminal failure: %s" % failure.getErrorMessage())
    except Exception:
        pass
    return failure


def _complete_ready(generation: _PendingGeneration, actor: Any, fingerprint_value: str, option_set: Any) -> None:
    if generation.retired:
        return
    _cache_put(fingerprint_value, option_set)
    displayed = list(_display_for(option_set))
    for subscriber in generation.subscribers:
        _deliver_guarded(subscriber, actor, "ready", list(displayed))


def _complete_degraded(
    generation: _PendingGeneration,
    actor: Any,
    fingerprint_value: str,
    *,
    memoize: bool,
) -> None:
    if generation.retired:
        return
    if memoize:
        _memo_put(fingerprint_value)
    for subscriber in generation.subscribers:
        _deliver_guarded(subscriber, actor, "degraded", None)


@defer.inlineCallbacks
def _run_generation(generation: _PendingGeneration, client: Any, context: Any, actor: Any, fingerprint_value: str) -> None:
    """One guarded layer call; routes the outcome to cache/memo/state per guard."""
    from world.ai import action_options

    try:
        # A plain ``yield``: the layer resolves a Deferred on the enabled
        # path but returns a synchronous ``None`` when the profile is
        # disabled — Twisted resumes with either without transport work.
        outcome = yield action_options.generate_action_options(
            context, client, fingerprint=fingerprint_value
        )
    except Exception as error:
        _log("generation failed: %s: %s" % (type(error).__name__, error))
        outcome = None
    if isinstance(outcome, action_options.OptionSet):
        _complete_ready(generation, actor, fingerprint_value, outcome)
    else:
        _complete_degraded(
            generation, actor, fingerprint_value, memoize=client.transport_failed
        )


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

    ``watchers`` is the room-entry hook's ``watchers_for(actor)`` result:
    ``(session, captured_epoch)`` pairs. Fire-and-forget: every synchronous
    failure (a vanished room, a malformed context, a vanished clock, a
    broken client construction) is logged and swallowed; a preflight
    failure degrades the affected sessions in place so no session is left
    in ``generating``. The return value is the in-flight generation's
    Deferred — freshly started or an existing one a new watcher attached
    to — and ``None`` on replays, memo hits, cache hits, preflight
    no-ops, and preflight failures, for caller observability; never an
    exception.
    """
    try:
        situation = _derive_situation(actor)
        if situation is None:
            _log("scheduling skipped: no location at trigger time")
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
        generation = _PendingGeneration()
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
            _log("preflight failed: %s: %s" % (type(error).__name__, error))
            _pending.pop(fingerprint_value, None)
            _complete_degraded(generation, actor, fingerprint_value, memoize=False)
            return None
        observing_client = _ObservingClient(client)
        generation.deferred = defer.ensureDeferred(
            _run_generation(generation, observing_client, context, actor, fingerprint_value)
        )
        generation.deferred.addErrback(_terminal_generation_error)
        generation.deferred.addBoth(lambda _: _drop_if_current(fingerprint_value, generation))
        return generation.deferred
    except Exception as error:
        _log("scheduling failed: %s: %s" % (type(error).__name__, error))
        return None


def evict(session: Any, actor: Any) -> None:
    """Dismiss the displayed options for one session.

    Reads the fingerprint the session currently displays, evicts it from the
    cache, memo, and pending registry (retiring an emptied generation), bumps
    the session's generation token so an in-flight completion cannot deliver,
    sets the state to ``unavailable``, and publishes the unavailable form.
    Never raises.
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
                    generation.retired = True

        token += 1
        _set_options_state(
            session, _state(actor_id, None, "unavailable", token, None)
        )
        ndb = getattr(session, "ndb", None)
        coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
        if coordinator is not None:
            _push_options_update(session, actor, coordinator.epoch)
        # When no coordinator is attached there is no live presentation
        # sequence to push to; the state write above is the whole effect.
    except Exception as error:
        _log("evict failed: %s: %s" % (type(error).__name__, error))
