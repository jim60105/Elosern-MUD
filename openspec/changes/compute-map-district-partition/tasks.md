# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Implement deterministic offline multi-source walking-distance partition, region priority, coast refinement and tie ordering using the existing geometry/passability sources.
- [ ] 1.2 Generate RLE ownership and smoothed district outlines with an input fingerprint; add runtime lookup that never imports or invokes the generation computation.
- [ ] 1.3 Document the exact generator command, datum units, spacing validation and stale-artifact regeneration workflow.

## 2. Focused behavioral verification

- [ ] 2.1 Add proposed `tests.test_map_district_partition` pure tests with independently known miniature barriers, diagonal traps, border-crossing fords/passes and region priority; run only this module.
- [ ] 2.2 Add a tagged production recomputation/data-integrity test in proposed `world.maps.tests.test_map_district_partition`: regenerate and compare all stored data; prove exact mainland coverage, own-landmark membership, no illegal crossing and no runtime generation; run this exact module.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
