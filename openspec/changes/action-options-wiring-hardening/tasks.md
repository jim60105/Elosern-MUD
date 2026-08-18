## 1. Shared Freshness Derivation

- [ ] 1.1 Extract the read-only exploration situation fingerprint and scheduling inputs into `web.webclient.presentation.fingerprints`, usable by both scheduling and presentation without importing `server.option_proposal_service` or `world.ai`.
- [ ] 1.2 Extend `PresentationContext` and the ingress context factory with the current options fingerprint, preserving immutable snapshot copies and fail-closed derivation behavior.
- [ ] 1.3 Gate non-unavailable exploration suggestion snapshots on fingerprint equality in the v5 presenter, with bounded diagnostics and no presentation-side state mutation.
- [ ] 1.4 Add focused service and presentation tests for matching fingerprints, stale ready/generating/degraded states, derivation failure, and the helper's forbidden-import boundary.

## 2. Lifecycle Trigger Coverage

- [ ] 2.1 Move the post-commit player-location trigger from Exit-specific code to the `PlayerCharacter` post-move lifecycle, retaining account, WebClient watcher, transaction, and no-raise guards.
- [ ] 2.2 Remove the superseded Exit-specific action-options trigger and add tests for ordinary traversal, direct `move_to()` relocation, failed transactions, rollback compensation, and NPC movement.
- [ ] 2.3 Add the dispatcher terminal-combat trigger after successful terminal combat completion publication and action-result send, gated on the actor returning to exploration and targeting `watchers_for(actor)`.
- [ ] 2.4 Add dispatcher and integration tests proving terminal combat schedules every live watcher after result publication while non-terminal combat actions do not.

## 3. Dismissal and Pending Generation Isolation

- [ ] 3.1 Add monotonic per-fingerprint generation numbers to cache entries and pending work, with version-aware cache replacement and identity-guarded Deferred cleanup.
- [ ] 3.2 Add bounded session-`ndb` dismissal barriers with puppet/unpuppet cleanup and an active-plus-successor pending chain so a dismissing window cannot join or replay an older generation while other windows retain their delivery.
- [ ] 3.3 Remove a last-subscriber retired generation from the joinable registry immediately, retaining only an identity-guarded detached predecessor continuation when a current successor needs handoff.
- [ ] 3.4 Add focused trigger-service tests for cross-window dismissal, successor coalescing, barrier cleanup on qualified delivery and puppet reset, stale cache exclusion, detached predecessor handoff, retired completion, and old-versus-new generation cleanup races.

## 4. Shared Ownership Cleanup

- [ ] 4.1 Replace the affordance destination-node helper with `node_id_for_location()` and remove the duplicate room-type encoder.
- [ ] 4.2 Add ordinary-room, `GridRoom`, and `TerrainRoom` destination encoding coverage through the shared encoder seam.
- [ ] 4.3 Remove `moveChoicePointToEnd` from the narrative facade, choice-point readiness contract, test stubs, and JavaScript exports while retaining append-owned stream-end placement.
- [ ] 4.4 Add or update Node tests proving appends remain before the mounted block with one scroll/unread decision and no detached facade reference remains.

## 5. Contract Verification

- [ ] 5.1 Add `covers_requirement` annotations using canonical requirement IDs for every changed main-spec requirement and run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.2 Run focused Evennia tests for `server.conf.tests.test_option_proposal_service`, `typeclasses.tests.test_action_options_room_entry`, `web.webclient.presentation.tests.test_combat_panel`, and `web.webclient.actions.tests.test_dispatcher`.
- [ ] 5.3 Run affected Node tests for `protocol.test.js`, `option_cards.test.js`, `choicepoint.test.js`, and `ui_contract.test.js`.
- [ ] 5.4 Run `openspec validate action-options-wiring-hardening --strict` and review the final artifact consistency before implementation handoff.
