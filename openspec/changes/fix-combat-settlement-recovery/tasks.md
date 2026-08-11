## 1. Settlement marker

- [ ] 1.1 Add `settled_tick: int | None` to `CombatSessionRecord` (JSON-safe, default None) and update serialization/reconstruction
- [ ] 1.2 In `settle_session`, write `settled_tick` inside the same durable step as the clock advance and session clear, for both hostile and exam modes
- [ ] 1.3 In `restore_active_session`, skip re-settlement when the record is already marked settled (log and clear state instead)

## 2. Atomic round-and-settlement chain

- [ ] 2.1 In `submit_player_action`, snapshot all touched entities (participants, battlefield, quest log) before resolution
- [ ] 2.2 Wrap run_round/overwhelm + friendly-fire scan + `_persist` + `settle_session` in one outer `transaction.atomic()`; restore snapshots on exception
- [ ] 2.3 Ensure exam mode writes the exam outcome and the marker in the same atomic step as the clock advance, with session clear as the last step

## 3. Cross-change coordination

- [ ] 3.1 Declare the landing order: this change (outer transaction + marker) lands before `fix-combat-session-roster-and-overwhelm` and `fix-friendly-fire-reachability`; startup ordering is owned by `fix-startup-session-restore-order`
- [ ] 3.2 Add a cross-cutting integration test covering, in one session flow: a preflight rejection (no round), a reverse-overwhelm resolution, a friendly-fire penalty rollback, and a terminal settlement — so later changes cannot silently break the shared seam

## 4. Tests and verification

- [ ] 4.1 Test: hostile terminal session restored at startup settles exactly once (simulated restart after clock-commit-before-clear window)
- [ ] 4.2 Test: exam terminal session whose time would be lost settles its rounds exactly once after restart
- [ ] 4.3 Test: termination between round effects and `_persist` leaves either the full round or none of it
- [ ] 4.4 Run combat-session, guild-exam, and world-clock tests
