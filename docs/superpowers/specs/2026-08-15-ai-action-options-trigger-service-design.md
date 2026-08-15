# AI Action Options — Trigger Service & Cache

**Date:** 2026-08-15
**Status:** Approved
**Scope:** `server/option_proposal_service.py` — fingerprint derivation, the per-fingerprint LRU
cache with replay semantics and the negative memo, fire-and-forget scheduling, the coordinator
push seam, and eviction via the dismiss action.

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
- Never blocks arrival or any command path: the caller invokes it outside its critical section
  (on the success side of adapters, or post-settlement in location-change hooks).
- The failure path logs via `evennia.logger`; the success path publishes one `ui_update`.
- `client=None` builds the layer client from the `action_options` profile, or the offline stub
  when the profile is disabled (same `_OfflineStubClient` shape as `scene_flavor_service`).

The service lives in `server/` for the same reason `scene_flavor_service` does: it is the single
place where imports from both `world/ai/` and `web/webclient/` are legal under the repository
transport and deterministic-path contract tests.

---

## 2. Trigger Hooks (deterministic call sites)

| Hook | Where | When |
|---|---|---|
| Room entry | `PlayerCharacter.at_object_location_change` (puppeted player only) | After the move settles atomically; covers moves, quest scene arrivals, and teleports |
| Dialogue reply | Success side of `explore.talk_scripted` / `explore.talk_freeform` adapters (`web/webclient/actions/exploration_actions.py`) | After the reply presentation publishes (single call per reply, never in the adapter's rejection paths) |
| Reconnect / initial | `ui_sync` handler path | After the full snapshot publishes on an existing fingerprint |
| Scene spawn | none (deliberate) | A spawned room is covered by the player's location change on arrival; spawning *empty* scenes proposes nothing new |

Hook code is three tiny deterministic call sites — no module under `world/ai/` touches them. Each
hook dedupes through the fingerprint floor (§3.1): rapid consecutive calls for the same situation
collapse into one request.

---

## 3. Fingerprint and Cache Semantics

### 3.1 Fingerprint

`fingerprint(room, npcs, monsters, dialogue_host) -> str` — a stable hash over the *situation*, not
the *moment*:

```
sha256(room_key | sorted(npc identities) | sorted(monster identities) | dialogue_host identity?)
```

Deliberately excluded: narrative tail, look commands, time of day. The same room with the same
people is the same situation every time, so the cache replays instead of re-calling (overview A-4).
An NPC leaving, arriving, or a dialogue host change produces a new fingerprint and one new call.

### 3.2 LRU cache

- Key: fingerprint. Value: the ready `OptionSet` (schema doc §1.1 — transport states never cached).
- Cap: `MAX_OPTIONSET_CACHE_ENTRIES` (16). Single-player memory cache; a reload empties it and the
  next trigger regenerates (degraded rule list shows meanwhile).
- Replay rule (user-confirmed): **one LLM call per fingerprint**, period. Any later trigger for a
  cached fingerprint re-publishes the cached `OptionSet` without touching the LLM.

### 3.3 Publishing a result

On success the service attaches the puppet's coordinator and publishes
`ui_update` / `context_actions` with `suggestions.status="ready"` through a new public helper
`publish_panel_update(session, actor, panels)` added to
`web/webclient/presentation/coordinator.py` (the trigger service itself never pokes session state).
The helper reuses the existing coordinator revision/epoch discipline and the
`_publish_presentation` semantics from `web/webclient/actions/dispatcher.py`. Stale sequences
(retired epoch / puppet change) publish nothing.

### 3.4 Negative memo

A transport failure is memoized per fingerprint for `NEGATIVE_MEMO_TTL` (30 s): triggers within the
TTL resolve to `degraded` immediately instead of burning profile retries against a dead endpoint.
After the TTL, the next trigger tries once more. Successful `OptionSet`s are cached indefinitely
until eviction or LRU pressure.

### 3.5 Fingerprint floor for degrade

A fingerprint with neither a cached set nor a negative memo shows `suggestions=degraded` with the
deterministic `default_cards()` (deterministic-actions doc §4) from the moment the trigger fires —
the player never waits for the LLM verdict.

---

## 4. Eviction (dismiss)

`evict(fingerprint)` — called by the `options.dismiss` adapter (webclient doc §6.3): drops the cache
entry and the negative memo, then publishes `suggestions.status="unavailable"` (section hidden).
A later trigger for the same situation regenerates — the user-confirmed "clear this cache"
semantics. Eviction never races generation: an in-flight generation resolving after eviction
drops its publish (its fingerprint is no longer cached and the section is unavailable).

---

## 5. Tests

| Area | Method |
|---|---|
| Fingerprint | Same room+people → same fingerprint; any member change → new; narrative/look changes → same |
| Replay | 3 triggers, 1 LLM call (FakeLLM call count); cached set re-published each time |
| LRU | Cap eviction order; survives unrelated fingerprints |
| Negative memo | Timeout → recycled `degraded` within TTL; fresh attempt after TTL (injected clock) |
| Synchronous guard | Malformed context / vanished room → logged no-op, no exception to caller |
| Push | Coordinator revision increments; retired epoch publishes nothing; puppet-only guard |
| Eviction | Cache + memo dropped; publish `unavailable`; in-flight generation after eviction publishes nothing |
| Offline | Disabled profile → stub never called; every trigger `degraded` |

---

## 6. Open Questions Carried Forward

- Whether room-entry triggers should also fire for *initial* placement (character creation /
  respawn) — the `ui_sync` hook already covers it; no separate rule is needed until evidence says
  otherwise.