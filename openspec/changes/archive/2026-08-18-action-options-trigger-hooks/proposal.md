## Why

The trigger service (`action-options-trigger-service`) defines *how* proposals are generated, cached, and pushed, but nothing yet decides **when** a generation may start. Without deterministic call sites, the proposal surface would never fire on its own: the player would never see suggestions unless some other system happened to wake the service. This change pins the three deterministic moments — arrival in a room, a completed conversation, and a WebClient reconnect — and the session-watcher registry that feeds them, keeping every trigger outside `world/ai/` and outside any rejection path.

## What Changes

- Add `web/webclient/presentation/watchers.py`: an ephemeral registry mapping a puppeted actor to its live WebClient `(session, coordinator_epoch)` watchers, registered on every successful `synchronize_session` (covers both `ui_sync` and post-command refresh) and pruned of disconnected sessions at each registration. **Correction since this proposal was drafted:** the registry and its registration seam already landed with the `action-options-trigger-service` change (archived 2026-08-18); this change verifies the seam and completes its test coverage (the post-command refresh registration test).
- Mount the **room-entry trigger** at the single deterministic movement-success boundary shared by every exit lineage (`after_successful_movement` in `typeclasses/exits.py`, directly after the onboarding `observe_room_entry`), gated to puppeted `PlayerCharacter`s. The scheduling is registered through `django.db.transaction.on_commit` (the `commands/scene.py` precedent), so the service is called only after the movement transaction commits — never inside its critical section, never after a rollback.
- Mount the **dialogue-reply trigger** inside the dispatcher's completion publication (`_publish_completion` in `web/webclient/actions/dispatcher.py`): after the reply text, presentation, and result are already on the wire, for `explore.talk_scripted` / `explore.talk_freeform` completions with outcome `success`, passing the dispatcher-held session and captured coordinator epoch.
- Mount the **reconnect trigger** on the `ui_sync` happy path (`synchronize_session` in `web/webclient/presentation/ingress.py`): after the full snapshot publishes, the requesting session becomes the sole watcher and the service's stale predicate decides whether a generation starts.
- Every hook calls the service's `schedule_action_options(actor, *, watchers, client=None)` fire-and-forget contract; hooks never raise into their callers, never schedule on rejection/failure paths, never live under `world/ai/`, and never mutate game state.
- **Design-doc correction:** the trigger-service design's room-entry row names `PlayerCharacter.at_object_location_change`, a hook that does not exist in Evennia 6.1; this change pins the real seam (`after_successful_movement`) and updates the design document set to match.

## Capabilities

### New Capabilities
- `action-options-trigger-hooks`: the three deterministic trigger call sites (room entry, dialogue completion, `ui_sync` reconnect), the ingress-maintained watcher registry, and the fire-and-forget/never-blocking/never-on-rejection constraints that make every trigger safe.

### Modified Capabilities
- (none — the `ui_sync` happy path gains a side-effect but its envelope and authentication requirements are unchanged; the trigger contract lives in the new capability spec.)

## Impact

- `typeclasses/exits.py`: one added call at the end of `after_successful_movement` (deferred import of the service).
- `web/webclient/actions/dispatcher.py`: thread the action ID through `_invoke_adapter`/`_publish_completion` so the dialogue trigger can identify talk completions; no behavior change for existing actions.
- `web/webclient/presentation/ingress.py` + new `web/webclient/presentation/watchers.py`: registration/pruning + reconnect trigger.
- Depends on `action-options-trigger-service` (the service API, epochs, stale predicate; scaffolded, not yet implemented).
- No new OOB messages, no schema changes, no player commands (the `game-command-docs` surface is untouched).
- New typeclasses → server deferred import direction; contractual fallback to the command-settlement channel if the repository transport contract rejects it (pinned during implementation).