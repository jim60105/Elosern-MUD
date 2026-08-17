## Context

`action-options-layer` provides `generate_action_options(context, client, *, fingerprint)` —
proposal-only, resolving to a frozen `OptionSet` or `None`. What does not exist yet is the
deterministic side that decides *when* to call it, dedupes concurrent/repeated triggers, scopes
the result per session, and pushes it through the presentation pipeline.

Existing patterns this design builds on:

- `server/scene_flavor_service.py` — the composition-root precedent: `server/` is the one
  directory where imports from both `world/ai/` and `web/webclient/` are legal under the
  repository contract tests; fire-and-forget scheduling (never raises, never blocks, offline
  stub client when the profile is disabled, errback logs).
- `web/webclient/presentation/coordinator.py` — per-transport ephemeral sequence: random epoch,
  monotonic revision, `attach_coordinator`, full snapshots / affected-panel updates; retirement
  (`detach`), puppet-change reset (`reset()`), and the admission-epoch guard in
  `dispatcher._settle_internal_error` (publish only when the captured epoch still matches).
- `web/webclient/presentation/ingress.py` + `server/conf/inputfuncs.py` — `ui_sync` /
  command-settlement refresh; `session.puppet` is the established session→actor mapping; the
  puppet-change branch (`_coordinator_for`) already resets the coordinator and retires the
  dispatch sequence.
- `web/webclient/presentation/context.py` — frozen `PresentationContext(actor,
  protocol_version, session_tag)`; presenters never receive the raw session.
- `web/webclient/presentation/exploration.py` / services/quest views — the quest view already
  renders `quest_id`, `stage_index`, and `objective_summary` per active objective, so the
  "displayed objective identity" is derivable from existing read-only output.

**Dependency note (review fixing):** the v5 suggestions panel seam (`context-actions-suggestions`)
has already landed (archived): the `suggestions` wire shape with the four statuses, the
status-bound card counts, the `validate_suggestions` shape gate, and the snapshot-only presenter
rule (`OptionsSnapshot` on `PresentationContext`, built by the ingress factory from
`session.ndb.options_state`) are the current main-spec contract. This change lands after it
(batch order B4 → B5 in the overview), so the push path is verified end-to-end against the real
seam.

Dependency position: rooted on `action-options-layer` (the generate entry point),
`action-options-affordance-contract` (canonical affordances + `default_cards()` + canonical-JSON
serializer), and `context-actions-suggestions` (the render seam it pushes through). Hook call
sites are the next change; the dismiss action and unified adapter ABI are the change after that.

## Goals / Non-Goals

**Goals:**

- One LLM call per fingerprint **per cache residency**: never per trigger, never per window;
  replay is cached, in-flight triggers attach subscribers, and an evicted or dismissed
  fingerprint regenerates (that is the "clear this cache" contract).
- Per-session presentation state that survives async completion: an arriving `ready` set cannot
  be clobbered by the next snapshot; dismiss state survives re-renders; a puppet change can
  never expose the previous character's options.
- Deterministic degradation in the same field: offline/transport failure → rule cards
  (`default_cards()`), with a short negative memo (only for transport failures) to avoid
  hammering a dead endpoint.
- Session/window isolation: dismissing in one window never disturbs another; a retired
  transport/puppet can never receive a push.

**Non-Goals:**

- The three hook call sites (room entry, dialogue completion, `ui_sync` trigger) — next change,
  consuming the service API defined here; the room-entry import-seam choice is pinned here.
- The `options.dismiss` action and the unified three-parameter adapter ABI — next-next change;
  this change implements `evict()` and its unit surface.
- Any canonical game-state write; proposal persistence across reloads (in-memory only);
  combat-kind proposals; new OOB message types (`ui_update` panel replacement is the whole
  contract).

## Decisions

### D1 — Service signature takes explicit watchers, never guesses sessions

`schedule_action_options(actor, *, watchers: tuple[Watcher, ...], client=None)` with
`Watcher = (session, captured_epoch)`, `captured_epoch = attach_coordinator(session,
registry).epoch` at trigger time. The dialogue/reconnect hooks are already inside code paths that
hold the exact session; the room-entry hook resolves through the watcher registry (D4). Never
"look up the puppet's sessions" via Evennia account APIs — the repo has no such precedent, and
guessing invites missing or cross-contaminating windows.

### D2 — Fingerprint: situation, not moment; eligibility digest inside

`sha256(room_key | sorted NPC identities | sorted monster identities |
eligible_affordance_digest | public_state_digest)`. The eligibility digest is the canonical JSON
(one shared serialization function in `presentation/affordances.py`, key-sorted, deterministic
coercion — also used by the schema ladder stage-9 comparison and test fixtures) over
`sorted((action_id, params))` pairs with labels excluded: any flip in what is executable —
schedule gates, exit locks, monster death — changes the fingerprint, so a cached card can never
name an action that stopped being current.

The public-state digest uses one read-only helper `displayed_objective_identity(actor)` that
returns the sorted `(quest_id, stage_index, objective_summary)` tuples of the active objectives
the quest view already renders (never hidden stages, counters, or thresholds) and excludes them
from the anti-oracle set; raw affinity numbers, narrative tail, look commands, and time of day
never enter either digest. An affinity increase within one tier must never churn the cache
(anti-oracle: cache-miss patterns leak at most the tier).

Alternative considered: fingerprint over public snapshot text — rejected: same-situation text
that merely rephrases (scene flavor, tail rolls) would churn generations and make the cache
useless.

### D3 — One pending registry with generation identity and per-session subscribers

`pending[fingerprint] → PendingGeneration(subscribers: [PendingSubscriber], generation_token:
int)` with `PendingSubscriber(session, session_token, captured_epoch)`. A trigger whose
fingerprint is pending appends a subscriber instead of starting a second call. A generation is
**retired** (tombstoned) when `evict()` removes its last subscriber: its completion then updates
no cache, no memo, and no session (empty-subscriber completions are the *retired-generation* path,
fully defined — review fixing). A retired fingerprint's next trigger starts a fresh generation
even if the old network request is still completing in the background; the old completion is
inert by construction (cache write skipped, subscribers none). Delivery publishes per subscriber
only when BOTH (a) the subscriber's session token is still the session's current token and (b)
the session's live coordinator epoch still equals the captured one (retired transport/puppet →
silent drop, mirroring `dispatcher._settle_internal_error`). The session token is monotonic per
session and incremented when a session starts or joins a new generation and
on every dismiss (replays that merely re-publish never increment) — making
evict-vs-generation deterministic per session.

### D4 — Watcher registry: ingress-maintained, keyed by session identity, current epochs

`web/webclient/presentation/watchers.py::watchers_for(actor)` resolves the live watching
sessions for the room-entry hook. The registry is a per-actor map keyed by session identity
(registration is idempotent per session — repeated `ui_sync`/command settlements update the
entry, never append), and `watchers_for()` reads each watcher's *current* coordinator epoch at
query time (so a post-reset epoch is never stale). The OOB ingress registers every live webclient
session on `ui_sync` and command settlement and prunes disconnected sessions at registration.
Stale entries are harmless by construction (the epoch guard drops their pushes), so no disconnect
hook is required — a lazy prune at registration covers growth, and the session-keyed map makes
growth bounded by live sessions.

Alternative considered: evennia session lookup at the hook site — rejected under D1 (no
precedent) and because a room-entry hook in `typeclasses/` has no session context; the registry
shifts session discovery into the web layer where sessions actually flow.

### D5 — Session options state owned by the service, puppet-change safe, read via snapshot

Service-owned `session.ndb.options_state = {owner_actor_id, fingerprint, status,
generation_token, displayed}`. **Puppet-change cleanup (review fixing):** the ingress's
puppet-change branch (`_coordinator_for` actor-id switch and `reset_client_sequence`) SHALL clear
`session.ndb.options_state` next to the existing `coordinator.reset()` / `retire_sequence()` —
a repuppeted session never renders the previous character's fingerprint, cards, or degraded
state; the snapshot builder additionally refuses to surface a snapshot whose `owner_actor_id`
differs from `context.actor` (belt and braces). Presenters never read `session.ndb`:
`PresentationContext` gains a frozen `options_state: OptionsSnapshot | None = None`, built by a
single presentation-context factory that ingress, the dispatcher publication paths, and the
service's own push all go through (review fixing: no path can omit the snapshot). `None` default
keeps every existing presenter and test byte-identical. This is what makes an async `ready`
survive the next snapshot and dismiss state survive re-renders.

### D6 — Epoch-guarded push helper on the coordinator

`publish_panel_update(session, actor, panels, *, context, expected_epoch)` builds the
`OptionsSnapshot`-carrying context (via the D5 factory), compares `expected_epoch` with the live
coordinator's epoch, and silently does nothing on mismatch. It reuses
`_build_presentation`/`_send` so revision monotonicity and envelope shape are exactly the
dispatcher's. **State before push:** the session's `options_state` write is deliberate and
survives a failed push (lost world clock, reset coordinator); the guarded push is best-effort,
and the session's next snapshot re-establishes the rendering from the state.

### D7 — One LLM call per residency; degraded replay is a fresh derivation

Flow per trigger: (1) already-displayed same fingerprint at `ready` → re-publish the session's
`displayed` set (the global LRU entry may already be evicted — precedence is the session's
`displayed`, never the cache); (2) same at `degraded` → re-derive `default_cards()` freshly and
publish as a status refresh (degraded replay is *not* byte-identical by contract — display names
and ordering are not in the fingerprint); (3) cache hit for the fingerprint → publish the cached
set; (4) pending → append subscriber; (5) miss → register pending and start one generation.
Generation result: success → cache + publish `ready` per guard; degraded outcome carried by an
**observed transport failure** (`LLMTransportError` from the layer client, see below) → negative
memo (30 s TTL) + publish `degraded`; every other degrade (validation exhaustion, disabled
profile, prompt unavailability) → publish `degraded`, no memo. `generating → generating`
transitions publish nothing: a new trigger while the previous generation is in flight sets the
new state, but only sessions that were not already `generating` receive the generating line. An
unexpected generation errback (any non-outcome failure) is a no-memo degrade with a status
refresh, so no session is ever left stuck in `generating`.

**Transport-failure discrimination (review-fixed contract, deferred layer amendment):**
`action-options-layer`'s resolve-to-`None` was originally to be augmented to a typed outcome
`OptionGenerationOutcome(status="ready"|"degraded", reason="transport"|"validation"|"disabled")`;
the layer change has since landed and been archived with the plain-`None` contract, so that
typed-outcome amendment is **deferred** (carried in Open Questions) rather than recorded as a
MODIFIED delta on the archived change. This change therefore implements the controlled-failure
fallback this design always kept as the transitional mechanism: the service calls
`generate_action_options` through a thin client wrapper that observes
`LLMTransportError` (raise or Deferred errback) on the injected layer client; a plain-`None`
degrade with an observed transport failure is the memoized class, and every other degrade
(disabled profile resolves before any client call, prompt unavailability and exhausted retries
never fail the client, and an unparseable response fails inside the guardrail
rather than at the client boundary) is a no-memo degrade. A follow-up change may swap the observation for the
typed outcome without changing the service contract or the memo semantics.

### D8 — Eviction is per-session with generation retirement

`evict(session, actor)`: read the session's *displayed* fingerprint (dismissing acts on what the
player sees, even if they moved away), evict that fingerprint from the global cache and memo,
remove that session from `pending[fingerprint].subscribers`; **when the last subscriber goes,
retire the pending generation (its completion writes nothing);** increment that session's token,
set `options_state = {owner_actor_id, fingerprint: None, status: unavailable, token+1}`, and
publish `suggestions.status="unavailable"` to that session via the guarded push. Other sessions'
subscriber entries, tokens, states, and cached publications are untouched. A later trigger for
the same situation regenerates — the user-confirmed "clear this cache" semantics.

### D9 — Where the module lives and how it degrades

`server/option_proposal_service.py` mirrors `scene_flavor_service` exactly: function-local
`world.ai` imports (cold import binds no guardrail logger), `_OfflineStubClient` for the disabled
profile, synchronously wrapped scheduling that resolves to `None` on any pre-flight failure
(vanished room, malformed context), errback logging. The client stays injectable for tests.
Canonical JSON serialization for the digests lives in
`web/webclient/presentation/affordances.py` (the vocabulary source) so stage-9 comparison and
fingerprints share one implementation.

### D10 — Room-entry import seam is pinned, not deferred

The room-entry hook calls the service through a function-local deferred import at the typeclass
hook (the `commands/scene.py` precedent). This choice is pinned by the change's tests (an
import-cycle contract test asserts the module loads cold); if the cycle test fails, the call site
moves to the command-settlement channel and the watcher registry is queried there — a fallback
decision recorded for `action-options-trigger-hooks`, not left open.

## Risks / Trade-offs

- [Fingerprint churn from parameterized affordances (e.g. `current_node` in `explore.move`
  params)] → The node encoder is a shared pure function (affordance-contract change); params are
  included in the eligibility digest precisely because a card whose `current_node` no longer
  matches the adapter's re-derivation would be `stale_location`-rejected. Walking re-entering
  the same room with identical eligibility replays (same fingerprint) — the cache floor.
- [Retired sessions lingering in pending/registry structures] → Bounded by design: pending
  subscribers per fingerprint are bounded by live sessions, the registry is session-keyed and
  prunes at registration, and the epoch guard makes any stale push inert; a retired generation
  writes nothing.
- [Stale `displayed` vs. evicted LRU entry] → Replay precedence is the session's `displayed`
  set, never the cache; the cache entry's absence never triggers regeneration for an
  already-displayed session (covered by a dedicated test).
- [A pending generation outlives its subscribers only as long as the HTTP call in flight] →
  The service deliberately does not own the client timeout; the LLM client profile enforces
  connect/read timeouts, and a terminal errback (whatever its cause) settles the watchers as a
  no-memo degrade and retires the pending entry, so a hung transport degrades instead of
  parking sessions in `generating` beyond the transport budget.
- [A second window generating on the same fingerprint while the first window dismisses] → The
  per-session token isolates the dismissed window; the other window's subscriber entry, token,
  and pending generation survive (covered by multi-session tests).
- [Minor inconsistency risk when eligibility digest and the schema ladder's affordances travel
  different code paths] → Both are produced by the same affordance builders; the canonical-JSON
  serialization is shared and asserted by parity tests on both sides.
- [The coordinator push allocating revisions outside the dispatcher's critical section] → Same
  coordinator instance, monotonic revision, exact envelope via `_build_presentation`; the
  webclient's revision check (≥ base revision) is satisfied by construction.

## Migration Plan

No released users; no data migration. Deployment is a landing sequence of the ten daily changes
in dependency order; within this change, landing order is internal (fingerprint primitives →
watchers registry → single context factory → service → push helper → evict → puppet-change
cleanup → tests), and the hook call sites arrive with the next change — until then the service
is exercised through tests, and the `ui_sync` seam is wired there. The layer typed-outcome
amendment is deferred (D7): the service's controlled-failure observation is the standing
mechanism until a follow-up change lands it, and no main-spec delta on `action-options-layer`
is produced by this change.

## Open Questions

- Whether the reconnect hook should ever force regeneration for an unchanged situation on a
  fresh session — currently rendered from cached state when present (the empty-cache path
  regenerates); carried in the trigger-service design doc for the hooks change.
- The deferred `action-options-layer` typed-outcome amendment
  (`OptionGenerationOutcome(status="ready"|"degraded", reason=
  "transport"|"validation"|"disabled")`): a follow-up change records the MODIFIED delta and
  swaps the service's client observation for the typed reason; the memo semantics are unchanged.