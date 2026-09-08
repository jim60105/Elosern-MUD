## 1. Seed writer

- [x] 1.1 Add `seed_affinity(npc, player, value)` to `world/rules/affinity.py` with a docstring stating it is the module's second writer and why a seed is not an interaction
- [x] 1.2 Reject a non-NPC owner, matching `apply_affinity_change`'s existing guard
- [x] 1.3 Reject a value outside `1..NATURAL_CAP` (booleans excluded), raising without writing
- [x] 1.4 Refuse to overwrite: raise without writing when `npc.relations.has_record(player)` is already true
- [x] 1.5 Write a fresh `AffinityRecord(value=value, cap=NATURAL_CAP, daily_gain=0, daily_tick=_current_day())` through the handler's save path, inside `transaction.atomic()`
- [x] 1.6 Snapshot and restore the host's `relations_data` surface on failure, following `apply_affinity_change`'s discipline
- [x] 1.7 Do not consume daily budget, resolve an `AffinitySource`, or call `run_auto_leave_recheck`
- [x] 1.8 Leave `apply_affinity_change` and every other function in the module untouched
- [x] 1.9 Emit the module's boundary info event for the write, per the observability catalog

## 2. Tests

- [x] 2.1 `world/rules/tests/test_affinity.py`: a seed creates the record at the requested value with `cap` `NATURAL_CAP`, `daily_gain` 0, and `daily_tick` equal to the current world day
- [x] 2.2 `world/rules/tests/test_affinity.py`: a seed on a pair that already holds a record raises and leaves the stored record byte-identical
- [x] 2.3 `world/rules/tests/test_affinity.py`: values 0, -1, and `NATURAL_CAP + 1` each raise without writing
- [x] 2.4 `world/rules/tests/test_affinity.py`: a non-NPC owner is rejected without writing
- [x] 2.5 `world/rules/tests/test_affinity.py`: after a seed, a capped interaction gain on the same world day still has its full daily budget
- [x] 2.6 `world/rules/tests/test_affinity.py`: a seed runs no auto-leave recheck, verified by seeding below `invite_threshold` for an NPC bound as a companion and asserting the binding survives
- [x] 2.7 `world/rules/tests/test_affinity.py`: an injected write failure restores `relations_data` in the in-process cache
- [x] 2.8 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 3. Verification

- [x] 3.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_affinity world.rules.tests.test_party`
- [x] 3.2 `uv run --locked python -m tools.spec_traceability check`
- [x] 3.3 `uv run --locked python -m tools.observability_lint check`
- [x] 3.4 `openspec validate affinity-seed-writer --strict`
