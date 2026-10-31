# Tasks

## 1. Owned implementation and mechanism evidence

- [x] 1.1 Add immutable query/member snapshot, exact request/result validation and canonical party/policy reads with no-write tests. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.2 Implement bounded deterministic revealed-window route selection, canonical diagonals/costs and each domain error. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.3 Implement per-step rounded reserve replay, stop indices/reasons and actual movement equivalence tests. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.4 Register result-only travel.plan and protocol data handling, test publication isolation and100ms benchmark; document the query. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.

## 2. Integration handoff

- [x] 2.0 Reuse the canonical admission-then-flight-waiver helper and implement the three named waiver tests, the paired initial-pace test and frozen-route-choice test in design.md. Evidence is zero-charge flight equivalence without bypassing sleeping/depletion admission.

- [x] 2.1 Add or update discoverable tests for every requirement/scenario and negative case in this delta, preserve unaffected existing contracts, and register new server test modules in exactly one shard. Completion evidence is focused test collection and passing assertions, not data snapshots.
- [x] 2.2 Record current canonical requirement associations and the planned equivalent-tree remount for new/renamed requirements using tools.spec_traceability list; no guessed IDs or coverage waiver. Completion evidence is a reviewed per-requirement mapping recorded in this change's design.md `## Review dispositions and concrete evidence` section.
- [x] 2.3 Main implementation owner runs the smallest affected locked pytest/server/Node/Vitest labels after all edits and the contract_gate plus strict OpenSpec validation; record outcomes and specified benchmarks. CI owns broad browser/evidence verification.
