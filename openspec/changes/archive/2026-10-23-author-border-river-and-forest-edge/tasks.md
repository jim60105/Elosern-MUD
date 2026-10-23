# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [x] 1.1 Author the border river course and three fords using existing rasterization/passability; preserve all previous rivers and passes.
- [x] 1.2 Author the meandering forest edge and river-derived western classifier; update enumeration windows and the shared coordinate-sensitive nation resolver while retaining seven terrain keys.
- [x] 1.3 Derive map border polylines from those sources with deep-forest suppression; update region metadata/consumers and existing geography documentation.

## 2. Focused behavioral verification

- [x] 2.1 Extend `world.maps.tests.test_wilderness_geography_contract` with river crossing, capital route, all anchors/harbours, forest extent and nominal-claim integrity; run that exact module.
- [x] 2.2 Run the smallest changed classes in `world.maps.tests.test_monster_provisioning` and `world.maps.tests.test_wilderness_population_species`, plus focused affected quest destination tests, to prove no stale classifier assumptions.

## 3. Contracts and focused handoff

- [x] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [x] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [x] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
