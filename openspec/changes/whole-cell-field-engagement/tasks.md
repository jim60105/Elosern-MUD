# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Separate admission from action selection

- [ ] 1.1 Implement the exact helper and preview contract above in combat_initiation and lifecycle, migrate every preview constructor/consumer, and add `A + A + B` mechanism tests in `world/rules/tests/test_combat_initiation.py` and `test_combat_session_flow/test_engage_group_flow.py`. Check: SINGLE admits all three and seeds only selected A, AREA retains normal recipients, explicit staged and exam rosters remain exact, and failure restores session, dialogue, skip safety and caches.

## 2. Update transport callers and player documentation

- [ ] 2.1 Migrate ordinary text/browser entry in commands and webclient action/presentation adapters; extend `commands/tests/test_combat_actions.py` and authoritative webclient action tests with player and companion entries and stale-target refusal. Update `docs/game/commands.md`, `docs/game/command-reference.md` and the population developer document. Check: transports persist the same roster/recipient IDs and command-doc contracts pass.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate whole-cell-field-engagement --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
