## 1. Duration cap

- [ ] 1.1 Add `MAX_ADVANCE_SECONDS` derived from `rulebook/clock.yaml["max_sleep_seconds"]` in `world/rules/time_skip.py` and clamp `parse_duration` results to it
- [ ] 1.2 Keep `sleep` (already capped) and `wait until` (bounded by a day) behavior unchanged; verify web bound unchanged

## 2. Atomic advance

- [ ] 2.1 In `world/rules/clock.py::WorldClock.advance`, enforce the bound check before any stage, raising a named `ClockAdvanceBoundError`
- [ ] 2.2 Wrap the stage settlement (gauge, buff/decay, magic study, daily resets, scheduled sources) plus the tick increment and `persist(self.tick)` in one `transaction.atomic()`
- [ ] 2.3 Snapshot caller-supplied entities before the transaction and restore on exception, reusing the shared snapshot/restore dispatch (action.py/surfaces.py pattern) so Evennia attribute caches are rolled back too

## 3. Tests and verification

- [ ] 3.1 Test: `rest 1000000000d` is capped at `MAX_ADVANCE_SECONDS`
- [ ] 3.2 Test: simulated mid-advance failure restores entity state and leaves the tick unchanged
- [ ] 3.3 Test: successful advance persists entity state and tick together across a simulated restart
- [ ] 3.4 Test: oversized `advance()` raises before any write
- [ ] 3.5 Run skip-command, clock, combat-session, and movement tests; run the world-clock and settlement-stage-order spec traceability checks
