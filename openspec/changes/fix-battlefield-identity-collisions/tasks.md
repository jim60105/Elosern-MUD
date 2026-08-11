## 1. Unique opponent keys

- [ ] 1.1 In `world/rules/guild_exams.py::_spawn_opponent`, change the opponent key to `guild-examiner-{target_rank}-{pk}` (spawn the object first, then use its pk)
- [ ] 1.2 Verify exam settlement/cleanup that references the opponent by key still works (use the spawned object reference, not a bare key lookup)

## 2. Skip-safety dbref indexing

- [ ] 2.1 In `world/rules/skip_safety.py`, key `_BATTLEFIELDS` by `str(entity.pk)` in register/unregister
- [ ] 2.2 Update `evaluate_skip_safety`'s IN_COMBAT lookup to resolve by the actor's dbref
- [ ] 2.3 Audit all other callers of `register_active_battlefield`/`unregister_active_battlefield` for key-format assumptions

## 3. Tests and verification

- [ ] 3.1 Test: player named `guild-examiner-E` starts and completes the E exam
- [ ] 3.2 Test: two same-key entities in separate battlefields do not cross-evict skip-safety state
- [ ] 3.3 Test: IN_COMBAT still rejects a mid-fight actor by dbref lookup
- [ ] 3.4 Run guild-exam, combat-session, skip-safety, and browser seed-related combat tests
