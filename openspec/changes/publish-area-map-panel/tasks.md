# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Add area_map presenter/schema and strict matching browser validator/allowlist/store handling with version parity; implement sparse grid fog and bounded coordinate-free room-graph fog without spawning rooms.
- [ ] 1.2 Implement 15×15 wilderness, true gateway/adjacent move descriptors, current district caption and destination-resolver markers; measure full-area bounds without clipping required visited/frontier nodes.
- [ ] 1.3 Register exact map.view area action through the existing dispatcher and add explicit on-demand snapshot/movement exclusion plus epoch-safe separate map storage; document full-snapshot interaction and leave world scope addition to its owner.

## 2. Focused behavioral verification

- [ ] 2.1 Create proposed `web.webclient.presentation.tests.test_area_map` focused classes for >two-hop grid visits, seen/seen edge rejection, dungeon/interior fog, gateway shapes, wilderness window and read-only state; run each smallest affected class.
- [ ] 2.2 Create one dependency-free Node test file for area-map validator parity, large valid graphs, malformed actions and no fabricated coordinates; run only that file.
- [ ] 2.3 Add focused dispatcher/coordinator tests proving map.view publication and no map computation/push on movement or text refresh; run only affected methods and measure largest supported area graph serialization.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Obtain canonical requirement IDs through `tools.spec_traceability list` on the current tree and an equivalent merged-spec tree for this delta; attach literal `covers_requirement` annotations to substantive discoverable Python unit/integration/browser tests. Run traceability check with the matching spec tree; never claim a pre-sync root pass covers new deltas.
- [ ] 3.3 Run only the focused labels/files/classes named above, run observability lint if server logging changes, then `uv run --locked python -m tools.contract_gate` and strict validation. Record commands/results and update the existing behavior documentation; no broad suites, CI shard commands, or local full evidence verification.
