# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Implement deterministic offline multi-source walking-distance partition, region priority, coast refinement and tie ordering using the existing geometry/passability sources.
- [x] 1.2 Generate RLE ownership and smoothed district outlines with an input fingerprint; add runtime lookup that never imports or invokes the generation computation.
- [x] 1.3 Document the exact generator command, datum units, spacing validation and stale-artifact regeneration workflow.

## 2. Focused behavioral verification

- [x] 2.1 Add proposed `tests.test_map_district_partition` pure tests with independently known miniature barriers, diagonal traps, border-crossing fords/passes, region priority, mixed coast/nation tiles, blocked owned land and footprint-contained grid landmark injection; run only this module.
- [x] 2.2 Add a tagged production recomputation/data-integrity test in proposed `world.maps.tests.test_map_district_partition`: regenerate and compare all stored data; prove exact mainland coverage, own-landmark membership, no illegal crossing and no runtime generation; run this exact module.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

- `uv run --locked python -m unittest tests.test_map_district_partition`: 14 OK (pure, no Django).
- `evennia test --settings test_settings.py --keepdb world.maps.tests.test_map_district_partition`: 8 OK
  (production regeneration takes about 6 s and is byte-identical to the committed file).
- `evennia test ... tests.test_evennia_test_optimization_contract`: 9 OK. The new module is owned by the
  existing `world.maps` label of the `maps-imports-prompts-observability` shard; no browser tests were added.
- `uv run --locked python -m tools.map_district_partition --check`: up to date.
- `tools.test_data_lint check`: 0 violations. The data-contract module is registered in
  `tools/test_data_freeze.json` and the seed ledger. `tools.observability_lint check`: 0 violations; no
  logging path changed.
- Equivalent root: an ordinary copy with a local git index, which the test-data lint needs, and
  `openspec/specs/map-district-partition/spec.md` merged from the delta. `spec_traceability list` gave the
  two `map-district-partition::` IDs, `check` reported 2470 covered and 0 errors, and the copied
  `tools.contract_gate` passed. Before sync the root `check` reports only the expected
  `unknown-requirement-id` for these two IDs; the post-sync root check and contract gate run at archive.
- `openspec validate compute-map-district-partition --strict`: valid.
- Docs: `docs/development/continental-geography.md` gains a "District partition" section.
- No UI changed, so there is no Storybook story to inspect.
