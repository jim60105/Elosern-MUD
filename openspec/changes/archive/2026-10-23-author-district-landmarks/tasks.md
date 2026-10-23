# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Author the final 110–130 district/landmark roster with stable keys and geographically suitable Traditional Chinese names; retain the one deep-forest district and its deep landmark.
- [x] 1.2 Validate all seeds with the registry validator and regenerate ownership/outlines using the existing partition tool; correct invalid placement/spacing without weakening rules.
- [x] 1.3 Update existing district-authoring documentation with naming/placement rationale and regeneration instructions.

## 2. Focused behavioral verification

- [x] 2.1 Extend the existing focused registry data-contract class (`ShippedDistrictContractTests` in `world.lore.tests.test_map_district_content`) for total range, one-to-one landmark identity, spacing, registered grid membership and real reachability; do not echo every name as a duplicate approval list.
- [x] 2.2 Run only `world.lore.tests.test_map_districts`, `world.lore.tests.test_map_district_content` and `world.maps.tests.test_map_district_partition` (or their smallest affected classes), including the complete frozen-data recomputation comparison.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.

## Verification record

- Registry: 120 districts (the deep forest plus Voronoi districts for Altoria 45, Grandia 53 and Valhalla 21). `validate_map_districts()` passes. The nearest Voronoi landmarks are 139.5 km apart, and Voronoi areas run about 17,000–44,000 km² (mean 33,622 km²).
- `uv run --locked python -m tools.map_district_partition` rewrote `world/maps/data/district_partition.json` (333,319 bytes, 74,469 gzipped), and `--check` reports it up to date.
- Evennia runner, `--settings test_settings.py --keepdb`: `world.lore.tests.test_map_district_content world.lore.tests.test_map_districts world.rules.tests.test_map_district_lighting` ran 26 tests OK; after the review polish, those three plus `world.maps.tests.test_map_district_partition` ran 34 tests OK. `world.maps.tests.test_map_district_partition world.lore.tests.test_wilderness_regions world.maps.tests.test_wilderness_geography_contract` ran 37 tests OK, including the full frozen-data recomputation comparison.
- No test module was added or moved, and no browser test was added, so no manifest changed. No logging path changed, so the observability lint was not required. No UI file changed.
- Equivalent tree: a disposable copy with the delta merged into `openspec/specs/map-districts/spec.md`, given its own throwaway git index for the test-data lint. There, `tools.spec_traceability --repo-root . check` reports 2471 covered and 0 errors, and `tools.contract_gate` passed. `openspec validate author-district-landmarks --strict` passes.
- Before sync, the real-root `tools.spec_traceability check` reports only `unknown-requirement-id` for `map-districts::the-authored-continent-has-a-complete-discoverable-landmark-roster`. After sync at archive, run the root `tools.spec_traceability check` and `tools.contract_gate` with the annotations unchanged.
- Docs: the "Authored roster" section in `docs/development/continental-geography.md`.
