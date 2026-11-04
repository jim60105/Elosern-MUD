# Tasks

All tasks are future implementation work. Follow design.md verbatim for signatures, state shapes, boundaries, prohibited scope and canonical-ID handling. Do not begin without the Batch prerequisites.

## 1. Activate the completed owner and remove room-entry births

- [x] 1.1 Wire source registration/stage order and fresh-world initialization using the exact startup contract. Remove provider ensure_population calls, migrate session protection imports and delete old ambient helpers/registries/exports and every caller in the deletion boundary. Update `world/maps/tests/test_bootstrap.py`, `test_wilderness_population.py`, `test_wilderness_population_species.py` and startup-order tests with fresh world, repeated sync, incompatible uninitialized world refusal, session protection and multi-zone rollback. Update developer operational repair/initialization docs. Check: fresh startup seeds constrained actual population once; revisit/reload never changes living IDs/resources, and old symbols have no remaining production callers.

## 2. Run real end-to-end smoke and finish contract retirement

- [x] 2.1 Implement and run the retained smoke entrypoint above against a disposable configured world; record actual bounded evidence and human tutorial/ecology review in the developer document. Reattach retired requirement tests through the assertion-role ledger, amend existing capability Purpose text during implementation, remove obsolete tests/shard entries and register new smoke-mechanism tests once. Check: construction/view/whole-cell selected effect/defeat/delay/undersupplied acceptance/manual exception/cancellation/fault-retry/reload all produce the specified observable report; final strict validation and contract_gate pass with no retired annotation, compatibility reader or guarantee remaining.

## 3. Slice handoff

- [x] 3.1 Run the focused labels in design.md, changed-logging observability lint, command documentation contract when applicable, `openspec validate regional-population-runtime-cutover --strict` and `uv run --locked python -m tools.contract_gate`; record actual evidence and the assertion-role/requirement mapping in the named developer document. Check: all required commands exit zero, new test ownership is exact, no retired annotations remain, and no unexecuted check is reported as passed. Do not run CI shard/full-browser or complete evidence verification locally.
