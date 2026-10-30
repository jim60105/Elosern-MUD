# Tasks

## 1. Owned implementation and mechanism evidence

- [ ] 1.1 Implement typed config/raster and physical base using shared terrain geometry. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.2 Implement avalanche-hash domain warping/fBm, ordered shapes and fixed quantization. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.3 Implement river/sea postconditions, ring prominence and component/canopy suppression; add synthetic physical/determinism/noise tests. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.
- [ ] 1.4 Document config ownership and offline dependency boundary; keep artifact/runtime handoff out of this slice. Completion evidence is the corresponding delta scenario tests with synthetic inputs; update the named existing docs with this mechanism.

## 2. Integration handoff

- [ ] 2.1 Add or update discoverable tests for every requirement/scenario and negative case in this delta, preserve unaffected existing contracts, and register new server test modules in exactly one shard. Completion evidence is focused test collection and passing assertions, not data snapshots.
- [ ] 2.2 Record current canonical requirement associations and the planned equivalent-tree remount for new/renamed requirements using tools.spec_traceability list; no guessed IDs or coverage waiver. Completion evidence is a reviewed per-requirement mapping recorded in this change's design.md `## Evidence and requirement shape` section.
- [ ] 2.3 Main implementation owner runs the smallest affected locked pytest/server/Node/Vitest labels after all edits and the contract_gate plus strict OpenSpec validation; record outcomes and specified benchmarks. CI owns broad browser/evidence verification.
