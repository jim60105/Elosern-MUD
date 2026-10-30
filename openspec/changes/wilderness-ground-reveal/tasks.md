# Tasks

## 1. Owned implementation and mechanism evidence

- [ ] 1.1 Integrate actual-radius arrival observation and PlayerCharacter/possession ownership with movement tests. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.2 Add WorldClock.advance's explicit ground_observer input and final-tick write; register knowledge in both its snapshot and continue_sleep's outer snapshot, with advance_wait/continue_sleep passing the authorized observer. Verify named clock-failure and post-advance receipt-failure tests plus zero/replay exclusion; update skip ownership documentation.
- [ ] 1.3 Implement bounded reveal/direct landmark checks, hidden gates and corrupt fallback with selected-chunk/no-write tests; update existing knowledge/protocol docs. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.

## 2. Integration handoff

- [ ] 2.1 Add or update discoverable tests for every requirement/scenario and negative case in this delta, preserve unaffected existing contracts, and register new server test modules in exactly one shard. Completion evidence is focused test collection and passing assertions, not data snapshots.
- [ ] 2.2 Record current canonical requirement associations and the planned equivalent-tree remount for new/renamed requirements using tools.spec_traceability list; no guessed IDs or coverage waiver. Completion evidence is a reviewed per-requirement mapping recorded in this change's design.md `## Evidence and requirement shape` and `## Review disposition and day boundary` sections.
- [ ] 2.3 Main implementation owner runs the smallest affected locked pytest/server/Node/Vitest labels after all edits and the contract_gate plus strict OpenSpec validation; record outcomes and specified benchmarks. CI owns broad browser/evidence verification.
