## 1. Watcher registry (`web/webclient/presentation/watchers.py`)

- [x] 1.1 `watchers.py` and its register/prune/query helpers already landed with the
      `action-options-trigger-service` change (archived 2026-08-18); verify the module still
      exposes `watchers_for(actor) -> tuple[tuple[Any, str], ...]` and the ingress registration
      seam before relying on it
- [x] 1.2 Registration already lives in `synchronize_session` (ingress.py, after
      `coordinator.synchronize(context)` succeeds); the existing suite covers the `ui_sync`
      path and prune-on-registration. Add the missing unit test: a post-command refresh
      (`refresh_after_command`/`observe_command_settlement`) also lands a watcher for the
      same session, and a closed session's watcher is pruned on the next registration

## 2. Room-entry trigger (`typeclasses/exits.py`)

- [x] 2.1 Add the puppeted-player gate helper (imported `PlayerCharacter` + `account is not None`) and a function-local deferred import of `server.option_proposal_service` (the `commands/scene.py` precedent; the trigger-service design's contract fallback is decided by the transport contract test — pin during implementation)
- [x] 2.2 Register the trigger through `transaction.on_commit` inside `after_successful_movement`, after `observe_room_entry(traversing_object)`: the fire-and-forget call to `schedule_action_options(player, watchers=watchers_for(actor), client=None)` runs only after the movement transaction commits; any synchronous failure logs a bounded diagnostic and never alters settlement (rubber-duck: the scene.py precedent registers on_commit, keeping the schedule outside the caller's critical section)
- [x] 2.3 Integration tests (EvenniaTest): successful plain-exit traversal schedules exactly one call with the right watchers; failing settlement (clock-charge raise via patch) schedules nothing; a rolled-back outer transaction never fires the on_commit trigger; NPC traversal schedules nothing; scheduled call keeps the movement result unchanged

## 3. Dialogue-reply trigger (`web/webclient/actions/dispatcher.py`)

- [x] 3.1 Thread `action_id` (default `None`) through `_invoke_adapter` and `_publish_completion` from `handle_ui_action`'s `spec`
- [x] 3.2 Add the trigger at the end of `_publish_completion`'s success branch: fire only for `action_id in {"explore.talk_scripted", "explore.talk_freeform"}` whose *normalized* outcome (actually sent to the client) is `success` — a raw `success` that normalizes into an internal error never schedules (rubber-duck) — passing `(session, coordinator.epoch)`; failure of the scheduling call is logged, never raises into publication
- [x] 3.3 Tests: successful scripted and freeform talk schedule exactly one call after both sends (assert sequencing with a wrapping spy); rejected talk schedules nothing; successful `explore.look` schedules nothing; raw-success-normalized-to-error talk schedules nothing; a retired talk completion never schedules; existing two-argument adapter tests stay green

## 4. Reconnect trigger (ingress + service predicate)

- [x] 4.1 On `synchronize_session` success, call the service with the solo watcher `((session, coordinator.epoch),)`; the service's stale predicate decides whether a generation starts (the hook stays dumb; the predicate itself is already implemented and tested in `action-options-trigger-service`)
- [x] 4.2 Integration tests: first `ui_sync` with empty options state schedules once after the snapshot; reconnect with a ready state for the current fingerprint schedules nothing; degraded-but-cached state schedules nothing

## 5. Contract and documentation

- [x] 5.1 Update the trigger-service design document set (`docs/superpowers/specs/2026-08-15-ai-action-options-trigger-service-design.md` §2) to name `after_successful_movement` as the room-entry seam (correcting the nonexistent `at_object_location_change` row)
- [x] 5.2 Verify the repository contract scan: no module under `world/ai/` references the triggers or the scheduling API; run the affected package tests (`typeclasses`, `web.webclient`, `server`) plus `uv run --locked python -m tools.spec_traceability check` with `covers_requirement` annotations on the new requirements