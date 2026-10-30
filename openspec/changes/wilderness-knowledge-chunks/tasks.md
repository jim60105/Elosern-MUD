# Tasks

## 1. Owned implementation and mechanism evidence

- [ ] 1.1 Implement exact schema2/chunk parse/write and finite frame-derived bounds with synthetic boundary/rejection tests. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.2 Retain full NodeVisit projection and add bounded/direct APIs; adapt pruning/remapping preserving metadata. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.3 Cut over all schema1-shaped consumers/fixtures with no decoder shim, test non-player no-op/rollback and selected-chunk instrumentation, update knowledge docs. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.

## 2. Integration handoff

- [ ] 2.1 Add or update discoverable tests for every requirement/scenario and negative case in this delta, preserve unaffected existing contracts, and register new server test modules in exactly one shard. Completion evidence is focused test collection and passing assertions, not data snapshots.
- [ ] 2.2 Record current canonical requirement associations and the planned equivalent-tree remount for new/renamed requirements using tools.spec_traceability list; no guessed IDs or coverage waiver. Completion evidence is a reviewed per-requirement mapping.
- [ ] 2.3 Main implementation owner runs the smallest affected locked pytest/server/Node/Vitest labels after all edits and the contract_gate plus strict OpenSpec validation; record outcomes and specified benchmarks. CI owns broad browser/evidence verification.
