# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Author the border river course and three fords using existing rasterization/passability; preserve all previous rivers and passes.
- [ ] 1.2 Author the meandering forest edge and river-derived western classifier; update enumeration windows and the shared coordinate-sensitive nation resolver while retaining seven terrain keys.
- [ ] 1.3 Derive map border polylines from those sources with deep-forest suppression; update region metadata/consumers and existing geography documentation.

## 2. Focused behavioral verification

- [ ] 2.1 Extend `world.maps.tests.test_wilderness_geography_contract` with river crossing, capital route, all anchors/harbours, forest extent and nominal-claim integrity; run that exact module.
- [ ] 2.2 Run the smallest changed classes in `world.maps.tests.test_monster_provisioning` and `world.maps.tests.test_wilderness_population_species`, plus focused affected quest destination tests, to prove no stale classifier assumptions.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
