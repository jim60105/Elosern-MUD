# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement deterministic offline multi-source walking-distance partition, region priority, coast refinement and tie ordering using the existing geometry/passability sources.
- [ ] 1.2 Generate RLE ownership and smoothed district outlines with an input fingerprint; add runtime lookup that never imports or invokes the generation computation.
- [ ] 1.3 Document the exact generator command, datum units, spacing validation and stale-artifact regeneration workflow.

## 2. Focused behavioral verification

- [ ] 2.1 Add proposed `tests.test_map_district_partition` pure tests with independently known miniature barriers, diagonal traps, border-crossing fords/passes, region priority, mixed coast/nation tiles, blocked owned land and footprint-contained grid landmark injection; run only this module.
- [ ] 2.2 Add a tagged production recomputation/data-integrity test in proposed `world.maps.tests.test_map_district_partition`: regenerate and compare all stored data; prove exact mainland coverage, own-landmark membership, no illegal crossing and no runtime generation; run this exact module.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
