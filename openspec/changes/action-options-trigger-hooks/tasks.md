## 1. Watcher registry (`web/webclient/presentation/watchers.py`)

- [ ] 1.1 Add `watchers.py`: module-level ephemeral dict keyed by actor PK → list of `(session, coordinator_epoch)`; `watchers_for(actor) -> tuple[tuple[Any, str], ...]` returning a snapshot tuple (empty when absent); internal register/prune helpers with a `session.is_connected()`-style prune guard
- [ ] 1.2 Register in `synchronize_session` (ingress.py): after `coordinator.synchronize(context)` succeeds, register `(session, coordinator.epoch)` for the actor and prune disconnected entries; add a unit test that `ui_sync` and a post-command refresh both land a watcher, and that a closed session's watcher is pruned on the next registration

## 2. Room-entry trigger (`typeclasses/exits.py`)

- [ ] 2.1 Add the puppeted-player gate helper (imported `PlayerCharacter` + `account is not None`) and a function-local deferred import of `server.option_proposal_service`
- [ ] 2.2 Call `schedule_action_options(player, watchers=watchers_for(actor), client=None)` inside `after_successful_movement`, after `observe_room_entry(traversing_object)`, wrapped so any synchronous failure logs a bounded diagnostic and never alters settlement
- [ ] 2.3 Integration tests (EvenniaTest): successful plain-exit traversal schedules exactly one call with the right watchers; failing settlement (clock-charge raise via patch) schedules nothing; NPC traversal schedules nothing; scheduled call keeps the movement result unchanged

## 3. Dialogue-reply trigger (`web/webclient/actions/dispatcher.py`)

- [ ] 3.1 Thread `action_id` (default `None`) through `_invoke_adapter` and `_publish_completion` from `handle_ui_action`'s `spec`
- [ ] 3.2 Add the trigger at the end of `_publish_completion`'s success branch: fire only for `action_id in {"explore.talk_scripted", "explore.talk_freeform"}` with `outcome == "success"`, passing `(session, coordinator.epoch)`; failure of the scheduling call is logged, never raises into publication
- [ ] 3.3 Tests: successful scripted and freeform talk schedule exactly one call after both sends (assert sequencing with a wrapping spy); rejected talk schedules nothing; successful `explore.look` schedules nothing; existing two-argument adapter tests stay green

## 4. Reconnect trigger (ingress + service predicate)

- [ ] 4.1 On `synchronize_session` success, call the service with the solo watcher `((session, coordinator.epoch),)`; the service's stale predicate decides whether a generation starts
- [ ] 4.2 Integration tests: first `ui_sync` with empty options state schedules once after the snapshot; reconnect with a ready state for the current fingerprint schedules nothing; degraded-but-cached state schedules nothing

## 5. Contract and documentation

- [ ] 5.1 Update the trigger-service design document set (`docs/superpowers/specs/2026-08-15-ai-action-options-trigger-service-design.md` §2) to name `after_successful_movement` as the room-entry seam (correcting the nonexistent `at_object_location_change` row)
- [ ] 5.2 Verify the repository contract scan: no module under `world/ai/` references the triggers or the scheduling API; run the affected package tests (`typeclasses`, `web.webclient`, `server`) plus `uv run --locked python -m tools.spec_traceability check` with `covers_requirement` annotations on the new requirements