## Context

The proposal service (change `action-options-trigger-service`, `server/option_proposal_service.py`) exposes `schedule_action_options(actor, *, watchers, client=None)` — a fire-and-forget scheduling contract mirroring `schedule_scene_flavor`. It also owns the fingerprint, pending registry, per-session tokens, LRU cache, negative memo, `session.ndb.options_state`, the epoch-guarded push helper, and `evict()`. This change supplies the deterministic **when**: three call sites plus the watcher registry the service needs because adapters/hooks must never guess Evennia account session APIs.

Current state of the code: movement success funnels through `typeclasses/exits.py::after_successful_movement` (used by plain `MovementCostMixin` exits and the wilderness gate/return/step lineages) and ends with `observe_room_entry`; the dispatcher's `_publish_completion` (dispatcher.py:286) is the single completion-publication critical section; `synchronize_session` (ingress.py:116) is the only happy-path snapshot entry used by both `ui_sync` and post-command refresh. The trigger-service design also names a hook (`PlayerCharacter.at_object_location_change`) that does not exist in Evennia 6.1, so this change pins real seams and amends the design-document set.

## Goals / Non-Goals

**Goals:**
- Pin three deterministic trigger call sites that never block, never raise into callers, never schedule on failure paths, and never live in `world/ai/`.
- Provide an ingress-maintained watcher registry (`watchers_for(actor)`) with coordinated epochs so the service pushes to the right session even when a puppeted player has multiple windows.
- Keep every trigger a bounded, easily testable seam (one integration test per hook).

**Non-Goals:**
- The service itself (fingerprint, cache, tokens, degrade, push, evict) — change `action-options-trigger-service`.
- The `context_actions` v3 panel, dismiss action, dock/choice-point surfaces — later changes.
- Any new OOB message, schema bump, or player command.

## Decisions

### D1: Room-entry trigger mounts on `after_successful_movement`, not on a character hook

Evennia 6.1 has no `at_object_location_change` hook; the design doc's row is corrected. Candidates:
- `PlayerCharacter.at_post_move` — fires on *every* relocation including respawns and non-settlement moves; too broad and harder to tie to the settlement atomicity contract.
- `after_successful_movement` (end, after `observe_room_entry`) — the exact deterministic success boundary every exit lineage already shares; a failed settlement never reaches it, and non-player traversers are excluded by the puppeted-player gate.

Chosen: `after_successful_movement`. The call goes through a function-local deferred import of the service (the `commands/scene.py` precedent at scene.py:128), gated on `isinstance(traversing_object, PlayerCharacter)` plus a puppeted check (`traversing_object.account is not None`).

### D2: Import direction — typeclasses → server with a contractual fallback

`after_successful_movement` lives in `typeclasses/`; the service lives in `server/`. The repo contract scan allows commands → server imports but typeclasses → server is new. The service module itself imports `world/ai` and `web/webclient` pieces *inside functions* (scene-flavor precedent), so a module-level cycle is avoided; the hook's own import is function-local regardless. If the transport contract test rejects the edge, the fallback is a thin re-export seam: the hook calls a stable function defined in `typeclasses/` that the web layer wires at startup (post-move observer registration), keeping the hook import-free. The choice is pinned during implementation by the contract test result; either way the observable behavior is identical.

### D3: Dialogue trigger threads the action ID through the completion path

`_publish_completion` does not know which action completed. Minimal change: `handle_ui_action` already holds `spec`; pass `spec.action_id` into `_invoke_adapter`/`_publish_completion` as a keyword parameter (`action_id`, default `None` so all existing tests keep their signatures). The trigger fires at the very end of `_publish_completion`'s success branch — after `_send_action_result` and `_settle_in_flight` — when `action_id in {"explore.talk_scripted", "explore.talk_freeform"}` and `outcome == "success"`, passing `(session, coordinator.epoch)` captured at that moment. Ordering guarantee (the reply text, update, and result on the wire first) falls out of being after both sends; the in-flight marker is already released, so the trigger cannot interfere with admission.

### D4: Reconnect trigger lives inside `synchronize_session`, predicate stays in the service

Both `ui_sync` and post-command refresh go through `synchronize_session`. Mounting the trigger on its success return (snapshot sent, `True`) covers both entry points with one seam and one registration site (D5). The hook only builds watchers `((session, coordinator.epoch),)` and calls the service; the stale predicate (absent state / fingerprint change / non-ready + not cached) is evaluated by the service per its own spec so the hook stays dumb and the decision logic stays testable in one place.

### D5: Watcher registry is registered inside `synchronize_session` and pruned at every registration

`watchers_for(actor)` returns a snapshot tuple of `(session, coordinator_epoch)`. Registration happens on every successful `synchronize_session` (covers `ui_sync` and refresh uniformly); pruning scans entries and drops those whose session transport is gone (`session.is_connected()` guard, or equivalent established check). Stale leftovers are further neutralized by the push seam's epoch guard, so a disconnect between prunes is harmless. Multi-window: each window registers itself; dismiss/push targeting stays per-session.

## Risks / Trade-offs

- [Room-entry trigger runs inside the movement transaction's success path] → It only schedules (writes nothing, touches no canonical state); synchronous failures are swallowed-and-logged. The service's actual work happens asynchronously after the transaction commits.
- [Duplicate triggers: a conversation reply and a reconnect can both fire for the same situation] → The service dedupes by fingerprint (cache hit / pending registry), so extra triggers cost a cache read at most; the stale predicate suppresses reconnect noise.
- [New typeclasses → server import direction] → Function-local deferred import; if the contract scan rejects it, the D2 fallback re-export seam is used. Pinned by the contract test during implementation.
- [Dialogue trigger on success of freeform talk after the talk Deferred settles] → The completion path already serializes publication results; the trigger only appends a fire-and-forget call after both sends, so it cannot reorder existing wire traffic.

## Open Questions

- Whether the reconnect hook should force regeneration on a fresh session whose situation is unchanged but whose cache was lost — delegated to the service's stale predicate (change `action-options-trigger-service`); this change keeps the hook dumb.