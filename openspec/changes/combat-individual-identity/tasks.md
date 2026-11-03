# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Migrate shared identity and all consumers

- [ ] 1.1 Implement the identity contract and source boundary above, update existing combat fixtures with explicit `combat_identity`, and add same-label synthetic assertions to `world/rules/tests/test_combat_session_persistence.py`, `test_combat_session_targeting.py`, `test_disengage_integration.py` and `test_monster_ai_selection.py`. Update combat identity documentation in `docs/development/regional-monster-population.md`. Check: the focused labels below pass, same-label objects stay distinct after rename/reload, and no production name-key fallback remains.

## 2. Migrate session and presentation evidence

- [ ] 2.1 Update the remaining EventLog, quest/narrative, combat panel and beat callers in the named boundary; preserve dbref-backed a/e tokens and readable labels. Extend `test_combat_beats.py`, command combat tests and presentation tests with duplicate-label recipient controls and a post-write rollback. Check: selected ID and only its resources/effects change, fresh session reconstruction returns the same IDs, and exam opponent policy is unchanged.

## 3. Slice handoff

- [ ] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate combat-individual-identity --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
