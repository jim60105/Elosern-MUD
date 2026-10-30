# Tasks

## 1. Owned implementation and mechanism evidence

- [x] 1.1 Implement exact bounded pure codec, source/data signatures and partial-edge encoding. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.2 Implement atomic regeneration command; generate and commit full production artifact within budget. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.3 Add pure runtime adapter/LRU and freshness/integrity checks before runtime adoption and in check_map_sources.py. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [x] 1.4 Test stale/corrupt/oversize/edge/cache/import-without-numpy paths; update existing authoring documentation. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.

## 2. Integration handoff

- [x] 2.1 Add or update discoverable tests for every requirement/scenario and negative case in this delta, preserve unaffected existing contracts, and register new server test modules in exactly one shard. Completion evidence is focused test collection and passing assertions, not data snapshots.
- [x] 2.2 Record current canonical requirement associations and the planned equivalent-tree remount for new/renamed requirements using tools.spec_traceability list; no guessed IDs or coverage waiver. Completion evidence is a reviewed per-requirement mapping recorded in this change's design.md `## Evidence and requirement shape` section.
- [x] 2.3 Main implementation owner runs the smallest affected locked pytest/server/Node/Vitest labels after all edits and the contract_gate plus strict OpenSpec validation; record outcomes and specified benchmarks. CI owns broad browser/evidence verification.
