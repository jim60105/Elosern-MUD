# Tasks

Estimated total: **4.75 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [x] 1.1 **1.75 h.** Deliver the finished lawful forest_path.webp and forest_path.provenance.json under web/static/art/scenes, depicting layered woodland path and open clearing with open lower foreground/full-bleed landscape composition. Produce a real original if existing sample rights are not documented; model request/seed alone is not a distribution license. Record actual author/source/license/model/input/seed where relevant, processing and checksum. Review original and 1451×790 cover crop; no placeholder, uncertain promotion, duplicated image or runtime acquisition is permitted.

- [x] 1.2 **1.75 h.** Deliver the finished lawful city_street.webp and city_street.provenance.json under web/static/art/scenes, depicting painted medieval town street and square with open lower foreground/full-bleed landscape composition. Produce a real original if existing sample rights are not documented; model request/seed alone is not a distribution license. Record actual author/source/license/model/input/seed where relevant, processing and checksum. Review original and 1451×790 cover crop; no placeholder, uncertain promotion, duplicated image or runtime acquisition is permitted.

- [x] 1.3 **0.5 h.** Create/register pure world.art.tests.test_bundled_terminal_art data-contract tests for actual two WebPs, resource limits, distinct checksums and lawful provenance. Keep the first-pack closed tracked-image exception unchanged; this pack adds owned actual coverage only. Test corrupt/missing controls name the affected terminal key, and register the module/data contract exactly once.

- [x] 1.4 **0.5 h.** Create/register BundledSceneAssetsBrowserTest.test_terminal_pack_static_decode in test_browser_bundled_scene_assets.py with shipped-catalog runtime set before seed/server startup. Request both actual /static/art/scenes paths on the real server, await browser decode and inspect cover composition. Record visual review in provenance; do not rely on metadata-only assertions or operator/generator services. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.5 **0.25 h.** Update exact artwork distribution/decode requirement claims and existing asset notes, register browser/shard/data ownership and run focused backend/browser plus final strict/contract commands below. Completion means both terminal scene members are complete lawful deliverables before the catalog change, with no reproduction branch hidden in catalog effort. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_bundled_terminal_art
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_bundled_scene_assets.BundledSceneAssetsBrowserTest.test_terminal_pack_static_decode
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-scenes-terminal-art --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
