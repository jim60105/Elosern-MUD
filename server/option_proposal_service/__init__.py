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

The package layering is acyclic: :mod:`~server.option_proposal_service.state`
(the process-local stores, the clock seam, and every session-state/cache/
barrier helper) <- :mod:`~server.option_proposal_service.clients` <-
:mod:`~server.option_proposal_service.situation` <-
:mod:`~server.option_proposal_service.trigger` <-
:mod:`~server.option_proposal_service.lifecycle` <-
:mod:`~server.option_proposal_service.scheduling`. This facade re-exports the
historical single-module surface and delegates the mutable-globals read
through module ``__getattr__`` so a package-path reset or mutation always
hits the same objects the call path uses.
"""

from server.option_proposal_service import (
    clients,
    lifecycle,
    scheduling,
    situation,
    state,
    trigger,
)
from server.option_proposal_service.clients import (
    _build_action_options_client,
    _ObservingClient,
    _OfflineStubClient,
)
from server.option_proposal_service.lifecycle import (
    _complete_degraded,
    _complete_ready,
    _deliver,
    _deliver_guarded,
    _run_generation,
    _settle_active,
    _start_successor,
    _terminal_generation_error,
)
from server.option_proposal_service.scheduling import (
    evict,
    schedule_action_options,
)
from server.option_proposal_service.situation import (
    _build_generation_context,
    _derive_situation,
    _prompt_affordances,
)
from server.option_proposal_service.situation import _PROMPT_AFFORDANCE_RANKS
from server.option_proposal_service.state import (
    MAX_OPTIONSET_CACHE_ENTRIES,
    NEGATIVE_MEMO_TTL,
    _barrier_min,
    _barrier_store,
    _cache_get,
    _cache_put,
    _chain_for,
    _clock_now,
    _clear_barrier_min,
    _current_generation,
    _display_for,
    _drop_if_current,
    _GenerationChain,
    _memo_live,
    _memo_put,
    _next_generation,
    _options_state,
    _PendingGeneration,
    _PendingSubscriber,
    _push_options_update,
    _reset_service_state,
    _set_barrier_min,
    _set_options_state,
    _state,
)
from server.option_proposal_service.trigger import _handle_session_trigger

__all__ = [
    "MAX_OPTIONSET_CACHE_ENTRIES",
    "NEGATIVE_MEMO_TTL",
    "_build_action_options_client",
    "_build_generation_context",
    "_cache_get",
    "_cache_put",
    "_chain_for",
    "_clock_now",
    "_barrier_min",
    "_barrier_store",
    "_clear_barrier_min",
    "_complete_degraded",
    "_complete_ready",
    "_current_generation",
    "_deliver",
    "_deliver_guarded",
    "_derive_situation",
    "_display_for",
    "_drop_if_current",
    "_GenerationChain",
    "_handle_session_trigger",
    "_memo_live",
    "_memo_put",
    "_next_generation",
    "_OfflineStubClient",
    "_ObservingClient",
    "_options_state",
    "_PendingGeneration",
    "_PendingSubscriber",
    "_prompt_affordances",
    "_push_options_update",
    "_reset_service_state",
    "_run_generation",
    "_set_barrier_min",
    "_set_options_state",
    "_settle_active",
    "_start_successor",
    "_state",
    "_terminal_generation_error",
    "evict",
    "schedule_action_options",
]


def __getattr__(name: str):
    """Delegate the mutable module-global reads to their owning module.

    The five process-local stores and the ``_clock`` seam live in
    :mod:`server.option_proposal_service.state` as the single dicts/pointer
    the call path reads and writes. The historical
    ``server.option_proposal_service._cache``-style reads resolve live here so
    a package-path mutation hits the same objects with no frozen second
    binding in this namespace (and ``_reset_service_state`` clears exactly
    them). Call-time patch seams (``_clock`` among them) target the owner
    module directly, following the action_options precedent.
    """
    if name in ("_cache", "_negative_memo", "_pending", "_chains", "_generation_counters", "_clock"):
        from server.option_proposal_service import state as _state_module

        return getattr(_state_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
