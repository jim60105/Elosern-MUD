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

`schedule_action_options(puppet, *, client=None) -> defer.Deferred | None` — the mirror of
`schedule_scene_flavor` in `server/scene_flavor_service.py`:

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
| Dialogue reply | **After the completion publication** of `explore.talk_scripted` / `explore.talk_freeform` (`web/webclient/actions/dispatcher.py` `_publish_completion` success path) | Ordering guarantee: the reply text and action result are already on the wire before the trigger fires (rubber-duck R3); never on rejection paths |
| Reconnect / initial | `ui_sync` happy path, after the full snapshot publishes | Renders from the existing session state; schedules only on fingerprint change or stale state |

Hook code is three tiny deterministic call sites — no module under `world/ai/` touches them. Each
hook dedupes through the pending/cache floors (§3).

---

## 3. Fingerprint, Pending, and Cache Semantics

### 3.1 Fingerprint

`fingerprint(room, npcs, monsters, public_state_digest) -> str` — a stable hash over the
*situation*, not the *moment*:

```
sha256(room_key | sorted(npc identities) | sorted(monster identities) | public_state_digest)
```

`public_state_digest` covers **discrete, public** state that changes what one should do: the
current quest-objective id, and the set of public relationship **tiers** (好感層級 labels) toward
present NPCs. Deliberately excluded: narrative tail, look commands, time of day, and **all raw
affinity numbers** — an affinity increase within one tier must not churn the cache (rubber-duck R4).

Anti-oracle rule (rubber-duck R4): the cache must never be used as an affinity oracle. Because the
digest turns over only on tier boundaries, an observer watching cache misses learns at most the
tier, never the numeric value; the pipeline doc further forbids feeding hidden numbers to the
prompt. This rule is stated here and asserted by the fingerprint tests (§5).

### 3.2 LRU cache + in-flight pending registry

- Cache: key = fingerprint; value = the ready `OptionSet` (schema doc §1.1 — transport states never
  cached). Cap: `MAX_OPTIONSET_CACHE_ENTRIES` (16). Single-player memory cache; a reload empties it
  and the next trigger regenerates (degraded rule list shows meanwhile).
- Pending registry (rubber-duck R4): `pending[fingerprint] → Deferred`. A trigger with a pending
  fingerprint attaches to the existing Deferred (replays the eventual result) instead of starting a
  second generation — **one LLM call per fingerprint is now true even while the first call is in
  flight.** `pending` participates in the LRU cap: a pending fingerprint being evicted is a bug
  (the trigger guard prevents it); eviction while pending only happens via dismiss (§4).
- Replay rule (user-confirmed): **one LLM call per fingerprint, period.** Any later trigger for a
  cached fingerprint re-publishes the cached `OptionSet` without touching the LLM.

### 3.3 Session-scoped options presentation state

The trigger service is the single owner of a transport-scoped presentation state on
`session.ndb.options_state` (rubber-duck R3):

```
options_state {
  fingerprint: str | None      # what situation the current suggestions describe
  status: generating|ready|degraded|unavailable
  generation_token: int        # monotonic per service lifetime
  displayed: OptionSet | None  # the last validated set shown as ready
}
```

Every `context_actions` render — full snapshots, `ui_update` from any action, `ui_sync` — reads
`options_state` through the presenter (webclient doc §1.3), so an async `ready` result can no
longer be clobbered by the next snapshot, and dismiss state survives re-renders. State updates are
atomic-by-assignment and never leak outside the transport.

### 3.4 Generation flow

1. Trigger → fingerprint floor: if `options_state.fingerprint == fingerprint` and status is
   `ready`/`degraded` → re-publish the displayed/cached set (`degraded` re-derives from
   `default_cards()`, deterministic-actions doc §4); no LLM activity.
2. Else set `options_state = {fingerprint, generating, token+1}`; publish `generating` once.
3. If `pending[fingerprint]` exists → attach; else register the Deferred (one LLM call).
4. Completion (token captured at registration):
   - Success → validate-and-inject (pipeline doc §4); cache; update `displayed`; publish `ready`
     **only if** the captured token is still `options_state.generation_token`;
   - `None` (layer degrade) → publish `degraded` (rule cards) under the same token guard;
   - Transport failure → record negative memo (30 s TTL); publish `degraded`.
5. A completion whose token is stale (newer trigger took over) publishes nothing (rubber-duck R4).

### 3.5 Negative memo

A transport failure is memoized per fingerprint for `NEGATIVE_MEMO_TTL` (30 s): triggers within the
TTL resolve to `degraded` immediately instead of burning profile retries against a dead endpoint.
After the TTL, the next trigger tries once more. Successful `OptionSet`s are cached indefinitely
until eviction or LRU pressure.

---

## 4. Eviction (dismiss)

`evict(puppet)` — called by the `options.dismiss` adapter (webclient doc §5):

1. Determine the current fingerprint from `options_state`; drop its cache entry and negative memo.
2. Invalidate any in-flight generation: `pending.pop(fingerprint, None)` and **increment
   `options_state.generation_token`** — the racing Deferred's completion finds the token stale and
   publishes nothing (rubber-duck R4).
3. Set `options_state = {fingerprint: None, status: unavailable, token+1}` and publish
   `suggestions.status="unavailable"` (section hidden in both dock and narrative stream).

A later trigger for the same situation regenerates — the user-confirmed "clear this cache"
semantics. Eviction never races generation: the token guard makes the outcome deterministic.

---

## 5. Coordinator Push Seam

A new public helper `publish_panel_update(session, actor, panels)` in
`web/webclient/presentation/coordinator.py` reuses the existing epoch/revision discipline and
`_publish_presentation` semantics from `web/webclient/actions/dispatcher.py`. It accepts the
already-validated session/actor pair and is called by the service with the token guard in place;
when the sequence is retired (transport or puppet change) it publishes nothing — the helper cannot
be used to bypass the coordinator's retirement guard.

---

## 6. Tests

| Area | Method |
|---|---|
| Fingerprint | Same room+people+digest → same; member change → new; raw-affinity change within a tier → **same**; tier boundary → new |
| Anti-oracle | Cache-miss pattern cannot expose sub-tier affinity movement (asserted over tier-step fixtures) |
| Replay | 3 triggers, 1 LLM call; 3 rapid triggers while pending → 1 call, all receive the result |
| Pending | In-flight trigger attaches; completion updates every attached waiter once |
| Token | Stale completion publishes nothing; dismiss during flight → completion inert |
| LRU | Cap eviction order; pending entry never evicted by a plugin trigger |
| Negative memo | Timeout → recycled `degraded` within TTL; fresh attempt after TTL (injected clock) |
| State | `ui_sync` re-render preserves ready cards and dismiss state; every render reads `options_state` |
| Synchronous guard | Malformed context / vanished room → logged no-op, no exception to caller |
| Offline | Disabled profile → stub never called; every trigger `degraded` |

---

## 7. Open Questions Carried Forward

- Whether the reconnect hook should ever force a regeneration when the situation is unchanged but
  the session is fresh — currently it renders the cached state, which a reload cannot have; the
  empty-cache path already regenerates.