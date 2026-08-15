# AI Action Options — Trigger Service & Cache

**Date:** 2026-08-15
**Status:** Approved (revised after rubber-duck review)
**Scope:** `server/option_proposal_service.py` — fingerprint derivation, the per-fingerprint LRU
cache with replay semantics, the in-flight pending registry, generation tokens, the negative memo,
the session-scoped options presentation state, the coordinator push seam, and eviction via the
dismiss action.

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md).
The generated content itself is specified in
[pipeline](2026-08-15-ai-action-options-pipeline-design.md); the pushed payload shape in
[webclient](2026-08-15-ai-action-options-webclient-design.md).

---

## 1. Scheduling Contract

`schedule_action_options(actor, *, watchers: tuple[Watcher, ...], client=None) -> defer.Deferred | None`
— the mirror of `schedule_scene_flavor` in `server/scene_flavor_service.py`, where
`Watcher = (session, captured_epoch)` and `captured_epoch` is `coordinator.epoch` at trigger time
(round-three review R3-2: the service never guesses live sessions — every hook passes them
explicitly; the epoch guard makes pushes to retired sequences inert, §5):

- Never raises: fingerprint derivation, context assembly, client construction, and Deferred
  acquisition are wrapped; any synchronous failure logs a bounded diagnostic and resolves to
  nothing.
- Never blocks arrival or any command path: the caller invokes it outside its critical section.
- The failure path logs via `evennia.logger`; the success path records the session options state
  and publishes one `ui_update`.
- `client=None` builds the layer client from the `action_options` profile, or the offline stub
  when the profile is disabled (same `_OfflineStubClient` shape as `scene_flavor_service`).

The service lives in `server/` for the same reason `scene_flavor_service` does: it is the single
place where imports from both `world/ai/` and `web/webclient/` are legal under the repository
transport and deterministic-path contract tests.

---

## 2. Trigger Hooks (deterministic call sites)

| Hook | Where | When |
|---|---|---|
| Room entry | `PlayerCharacter.at_object_location_change` (puppeted player only) | After the move settles atomically |
| Dialogue reply | **After the completion publication** of `explore.talk_scripted` / `explore.talk_freeform` (`web/webclient/actions/dispatcher.py` `_publish_completion` success path) | Ordering guarantee: the reply text and action result are already on the wire before the trigger fires (review R3); never on rejection paths |
| Reconnect / initial | `ui_sync` happy path, after the full snapshot publishes | See the stale predicate below |

**Reconnect stale predicate (review R16):** the `ui_sync` hook schedules a generation iff the
session's `options_state` is absent, or its `fingerprint` differs from the current one, or its
status is `generating`/`degraded`/`unavailable` **and** the fingerprint is not cached and not under
a live negative memo. A `ready` state whose fingerprint matches the current situation never
schedules — the render already assembles from `options_state`, and the cache needs no refresh.

Hook code is three tiny deterministic call sites — no module under `world/ai/` touches them. Each
hook supplies **explicit watchers** (round-three review R3-2):

- Room entry: `PlayerCharacter.at_object_location_change` (puppeted player only). The hook mounts
  with a function-local deferred import of the service (the `commands/scene.py` precedent; if the
  typeclasses → server import turns cyclic, the call site moves to the command-settlement channel
  — pinned during change 6). It resolves watchers through
  `web/webclient/presentation/watchers.py::watchers_for(actor)`: an ephemeral registry the OOB
  ingress maintains — it registers each live webclient session on `ui_sync`/command settlement and
  prunes disconnected sessions at every registration. `captured_epoch` comes from
  `attach_coordinator(session, registry)` at trigger time. Stale watcher entries are harmless: the
  epoch guard silently drops their pushes (§5).
- Dialogue reply: **after the completion publication** of `explore.talk_scripted` /
  `explore.talk_freeform` (`web/webclient/actions/dispatcher.py` `_publish_completion` success
  path) — passes exactly the dispatcher-held `(session, coordinator.epoch)`; no session resolution
  happens at the hook site (round-three review R3-2). Ordering guarantee: the reply text and
  action result are already on the wire before the trigger fires (review R3); never on rejection
  paths.
- Reconnect / initial: `ui_sync` happy path, after the full snapshot publishes — the requesting
  session itself is the sole watcher.

---

## 3. Fingerprint, Pending, and Cache Semantics

### 3.1 Fingerprint

`fingerprint(room, npcs, monsters, eligible_affordance_digest, public_state_digest) -> str` — a
stable hash over the *situation*, not the *moment*:

```
sha256(
  room_key
  | sorted(npc identities) | sorted(monster identities)
  | eligible_affordance_digest      # review R4 fix
  | public_state_digest
)
```

`eligible_affordance_digest` is the digest of the canonical eligible-affordance list (as the
schema ladder's stage-9 argument would receive it): `sha256(sorted((action_id, params) pairs,
params serialized key-sorted))`, labels excluded. Any change that makes an action executable or
not — NPC schedule gates flipping, an exit locking, a monster dying, an object vanishing —
changes the digest and therefore the fingerprint, so a cached proposal can never point at an action
that stopped being current (the exact-match promise holds by construction). Identical eligibility
(e.g. walking back and forth through the same room) replays as before: one call, cached answer.
The digest serialization is one shared canonical JSON function (keys sorted, deterministic type
coercion) used by the fingerprint, the validation stage-9 comparison, and the test fixtures, so
builder- and validator-side representations cannot drift (round-three review suggestion).
`public_state_digest` covers the remaining **discrete, public** state that changes what one should
*do*: the **currently displayed quest-objective identity** (the objective id/label the objective
panel already renders to this player — round-three review R3-2: hidden stages, internal counters,
and uncompleted thresholds are excluded; partial progress toward an objective never changes the
fingerprint) and the set of public relationship **tiers** (好感層級 labels) toward present NPCs.
Deliberately excluded: narrative tail, look commands, time of day, and **all raw affinity
numbers** — an affinity increase within one tier must not churn the cache.

Anti-oracle rule (review R4): the cache must never be used as an affinity oracle. Because
`public_state_digest` turns over only on tier boundaries, an observer watching cache misses learns
at most the tier, never the numeric value; the pipeline doc further forbids feeding hidden numbers
to the prompt. Asserted by the fingerprint tests (§6).

### 3.2 LRU cache + in-flight pending registry

- Cache: key = fingerprint; value = the ready `OptionSet` (schema doc §1.1 — transport states never
  cached). Cap: `MAX_OPTIONSET_CACHE_ENTRIES` (16). Single-player memory cache; a reload empties it
  and the next trigger regenerates (degraded rule list shows meanwhile).
- Pending registry (review R4, extended round three): `pending[fingerprint] → list[PendingSubscriber]`
  where `PendingSubscriber = (session, generation_token, captured_epoch)` — one entry **per
  watching session**, because the presentation state is per-session while the service is global
  (review R15). A trigger whose fingerprint is pending **attaches a new subscriber** to the
  in-flight Deferred; the eventual result is delivered to each subscriber independently, guarded by
  its own token and epoch — **one LLM call per fingerprint per service lifetime is true even while
  the first call is in flight.**
- Replay rule (user-confirmed): **one LLM call per fingerprint, period.** Any later trigger for a
  cached fingerprint re-publishes the cached `OptionSet` without touching the LLM (each watching
  session gets its own publish, guarded by its own token).

### 3.3 Session-scoped options presentation state

The trigger service is the single owner of a transport-scoped presentation state on
`session.ndb.options_state` (review R3):

```
options_state {
  fingerprint: str | None      # what situation the current suggestions describe
  status: generating|ready|degraded|unavailable
  generation_token: int        # monotonic per session lifetime
  displayed: OptionSet | None  # the last validated set shown as ready
}
```

Every `context_actions` render — full snapshots, `ui_update` from any action, `ui_sync` — reads
`options_state` **through an immutable snapshot on `PresentationContext`** (round-three review
R3-2: presenters never receive the raw session, so they cannot read `session.ndb` directly;
`PresentationContext` gains a frozen field `options_state: OptionsSnapshot | None = None`, built by
the coordinator/ingress from `session.ndb.options_state` at context-construction time —
dispatcher publication paths, `ui_sync`, and the service's own push each build it; a `None` default
keeps every existing presenter and test unchanged). `OptionsSnapshot` is an immutable copy of
`{fingerprint, status, generation_token, displayed}` — so an async `ready` result can no longer be
clobbered by the next snapshot, and dismiss state survives re-renders. State updates are
atomic-by-assignment and never leak outside the session. On transport or puppet retire the
`session.ndb` state disappears with the transport; the epoch guard makes any later push for that
session a silent drop, so no explicit unregister is required (bounded structures only).

### 3.4 Generation flow

1. Trigger (puppet + its live session(s), determined at each hook) → fingerprint floor: if a
   session's `options_state.fingerprint == fingerprint` and status is `ready`/`degraded` →
   re-publish the displayed/cached set for that session (`degraded` re-derives from
   `default_cards()`, deterministic-actions doc §4); no LLM activity.
2. Else set `options_state = {fingerprint, generating, token+1}` for each watching session;
   publish `generating` **only to sessions whose previous status was not `generating`** (a
   generating → generating transition publishes nothing — the card line, if still visible, is
   replaced in place by `ready` moments later; review R14).
3. If `pending[fingerprint]` exists → append a subscriber; else register a new pending list with
   one subscriber and start the generation (one LLM call).
4. Completion (the token and epoch captured at subscription are per-session; **a subscriber whose
   session's `coordinator.epoch` no longer matches its `captured_epoch` is dropped silently —
   retired transport/puppet, round-three review R3-2**):
   - Success → validate-and-inject (pipeline doc §4); cache; for each subscriber whose
     `generation_token` is still its session's current token **and whose epoch still matches**:
     update `displayed`, publish `ready`;
   - `None` (layer degrade) → publish `degraded` (rule cards) under the same per-session token and
     epoch guards;
   - Transport failure → record negative memo (30 s TTL); publish `degraded` per subscriber.
5. A completion whose subscriber token or epoch is stale (a newer trigger took over, the session
   was dismissed, or the transport was retired) publishes nothing to that subscriber.

### 3.5 Negative memo

A transport failure is memoized per fingerprint for `NEGATIVE_MEMO_TTL` (30 s): triggers within the
TTL resolve to `degraded` immediately instead of burning profile retries against a dead endpoint.
After the TTL, the next trigger tries once more. Successful `OptionSet`s are cached indefinitely
until eviction or LRU pressure.

---

## 4. Eviction (dismiss)

`evict(session, actor)` — called by the `options.dismiss` adapter (webclient doc §5). Session
targeting (review R15) is resolved **by the dispatcher, not by guessing Evennia account APIs**: the
dispatcher already holds the session object and injects it into adapters through the **unified
adapter ABI** — `adapter(actor, payload, session=None)` for *every* registered adapter (round-three
review R3-2: no runtime signature introspection; the change that introduces `options.dismiss`
(overview slicing change 8) updates all production adapters and the `ActionSpec` type to the
three-parameter ABI in the same unit, and `_invoke_adapter` passes the session positionally —
existing direct two-argument adapter tests keep working through the default);

per-session eviction, in order:

1. Read the session's `options_state.fingerprint` (the **displayed** situation — dismissing always
   acts on what the player sees, even if the player moved away since).
2. Evict the cache entry and negative memo for that fingerprint from the global stores.
3. Invalidate that session's in-flight generation: remove its subscriber entry in
   `pending[fingerprint]` and **increment its `options_state.generation_token`** — the racing
   completion finds the token stale for that session and publishes nothing.
4. Set `options_state = {fingerprint: None, status: unavailable, token+1}` and publish
   `suggestions.status="unavailable"` (section hidden in dock and narrative stream) to that
   session.

Other sessions are untouched: their subscriber entries, tokens, states, and cached publications
survive an unrelated dismiss (review R15). A later trigger for the same situation regenerates —
the user-confirmed "clear this cache" semantics. Eviction never races generation: the token guard
makes the outcome deterministic per session.

---

## 5. Coordinator Push Seam

A new public helper `publish_panel_update(session, actor, panels, *, context, expected_epoch)` in
`web/webclient/presentation/coordinator.py` reuses the existing epoch/revision discipline and
`_publish_presentation` semantics from `web/webclient/actions/dispatcher.py`:

- `context` is built by the service with the session's current `OptionsSnapshot` (trigger-service
  doc §3.3) — the presenter reads it through `PresentationContext`, never the raw session
  (round-three review R3-2).
- `expected_epoch` is the subscriber's `captured_epoch`; the helper compares it with the live
  `attach_coordinator(...).epoch` and **silently publishes nothing on mismatch** (retired
  transport or puppet change) — the same guard `_settle_internal_error` already uses, so the helper
  cannot bypass the coordinator's retirement guard.
- Called by the service with the per-session token guard in place; it never writes game state.

---

## 6. Tests

| Area | Method |
|---|---|
| Fingerprint | Same room+people+eligibility+digest → same; member change → new; **schedule gate flip / exit lock / monster death → new (eligibility digest)**; raw-affinity change within a tier → **same**; tier boundary → new; **partial objective progress (hidden counter) → same; displayed objective identity change → new** |
| Anti-oracle | Cache-miss pattern cannot expose sub-tier affinity movement (asserted over tier-step fixtures) |
| Replay | 3 triggers, 1 LLM call; 3 rapid triggers while pending → 1 call, all subscribers receive the result |
| Pending | In-flight trigger attaches a new subscriber; completion updates every subscriber whose token is current |
| Token | Stale completion publishes nothing; dismiss during flight → that session's completion inert, other sessions unaffected |
| Epoch | Subscriber whose session's coordinator epoch moved (retire/puppet change) receives nothing; `publish_panel_update` mismatch → silent no-op (round-three review) |
| Watchers | `watchers_for(actor)` registration/pruning; room-entry hook resolves the same sessions the ingress serves; dialogue hook passes the dispatcher-held session without re-resolution (round-three review) |
| Multi-session | Two sessions on one puppet: dismiss in A leaves B's state, token, and future publications intact |
| LRU | Cap eviction order; pending entry never evicted by a plugin trigger |
| Negative memo | Timeout → recycled `degraded` within TTL; fresh attempt after TTL (injected clock) |
| State | `ui_sync` re-render preserves ready cards and dismiss state; every render reads `options_state` through the `PresentationContext` snapshot |
| Stale predicate | Empty state / fingerprint change / cache-miss+non-ready → schedules; ready+same fingerprint → never |
| Synchronous guard | Malformed context / vanished room → logged no-op, no exception to caller |
| Offline | Disabled profile → stub never called; every trigger `degraded` |

---

## 7. Open Questions Carried Forward

- Whether the reconnect hook should ever force a regeneration when the situation is unchanged but
  the session is fresh — currently it renders the cached state, which a reload cannot have; the
  empty-cache path already regenerates.