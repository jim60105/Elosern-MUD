# Tasks

Implementation budget: 8 hours total. Prerequisites are the exact `depends-on` lines in proposal.md.

## 1. Implement the bounded slice

- [ ] 1.1 Add the area_map presenter using the fixed shared schema/validators/codec and production registry/allowlist parity; implement sparse grid fog and bounded coordinate-free room-graph fog without spawning rooms.
- [ ] 1.2 Implement 15×15 wilderness, true gateway/adjacent move descriptors, current district caption and destination-resolver markers; measure full-area bounds without clipping required visited/frontier nodes.
- [ ] 1.3 Register exact map.view area action through the existing dispatcher and use the upstream explicit on-demand snapshot/movement exclusion and epoch-safe separate map storage; document full-snapshot interaction and leave world scope addition to its owner.

## 2. Focused behavioral verification

- [ ] 2.1 Create proposed `web.webclient.presentation.tests.test_area_map` focused classes for >two-hop grid visits, seen/seen edge rejection, dungeon/interior fog, gateway shapes, wilderness window and read-only state; run each smallest affected class.
- [ ] 2.2 Create one dependency-free Node test file for area-map validator parity, large valid graphs, malformed actions and no fabricated coordinates; run only that file.
- [ ] 2.3 Add focused dispatcher/coordinator tests proving map.view publication and no map computation/push on movement or text refresh; run only affected methods and measure the largest supported area graph/225-cell serialization, set adequate finite area limits and exercise the upstream bounded codec for oversized output.

## 3. Contracts and focused handoff

- [ ] 3.1 Register any new/moved Evennia package test modules in `.github/evennia-shards.json` and every new browser class/method in `.github/browser-shards.json`; use synthetic fixtures except explicitly registered production data contracts.
- [ ] 3.2 Copy the complete current implementation/tests/manifests/tooling into a disposable ordinary directory; merge prerequisite/current deltas into its copied main specs. Obtain canonical IDs with `tools.spec_traceability --repo-root <equivalent-root> list`, and retain literal intended `covers_requirement` annotations in implementation tests. Run `check` with that equivalent root and the copied contract gate from that directory before sync; the unsynced real-root gate is not an acceptance gate for new IDs.
- [ ] 3.3 Run only the focused labels/files/classes named above and observability lint if logging changes; run strict validation and the equivalent-tree gate before handoff, then normal root `tools.spec_traceability check` and `tools.contract_gate` after sync. Record commands/results and existing-doc updates; no broad suites, CI shard commands or local full evidence verification.
