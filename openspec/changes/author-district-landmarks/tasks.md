# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Author the final 110–130 district/landmark roster with stable keys and geographically suitable Traditional Chinese names; retain the one deep-forest district and its deep landmark.
- [ ] 1.2 Validate all seeds with the registry validator and regenerate ownership/outlines using the existing partition tool; correct invalid placement/spacing without weakening rules.
- [ ] 1.3 Update existing district-authoring documentation with naming/placement rationale and regeneration instructions.

## 2. Focused behavioral verification

- [ ] 2.1 Extend the existing focused registry data-contract class for total range, one-to-one landmark identity, spacing, registered grid membership and real reachability; do not echo every name as a duplicate approval list.
- [ ] 2.2 Run only `world.lore.tests.test_map_districts` and `world.maps.tests.test_map_district_partition` (or their smallest affected classes), including the complete frozen-data recomputation comparison.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
