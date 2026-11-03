# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Record exact map population loss occurrences

- [ ] 1.1 Implement the required session started_tick, candidate/storage caller cutover and round-finalization owner notification above, extending `test_combat_session_persistence.py` and `world/maps/tests/test_regional_population_recovery.py`. Include upkeep, late-round loss, duplicate delivery, nonterminal restart and foreign local defeats; do not treat fled or absent IDs as deaths. Document timestamp and pending-loss shapes. Check: start100/round3 death/delay10 never yields due before128 and an older due110 wave cannot borrow that loss.

## 2. Settle durable delayed episodes chronologically

- [ ] 2.1 Implement source registration callable, pure boundary query, state machine and complete compensation. Add before/at-due, two waves, further-loss no-reset, blocked retry, manual-return cancellation without sequence increment, active/historical-session exclusion and partition-equivalence tests in the recovery module. Register the new test module once. Check: before due no birth, due cancels at restored L, blocked retries at positive interval, a later clock-stage fault restores all previous waves/live caches, and retries select the same plans. Do not wire startup yet.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-population-recovery --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
