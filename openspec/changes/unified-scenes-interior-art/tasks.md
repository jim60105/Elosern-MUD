# Tasks

Estimated total: **6.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.75 h.** Produce and commit the finished original `tavern_interior.webp` under `web/static/art/scenes/`, depicting timber floor, hearth and counter. Use painterly JRPG full-bleed landscape composition with open lower foreground; no UI, watermark, readable lettering, town/forest copy, placeholder or same-image rename. Deliver `tavern_interior.provenance.json` with actual source, distribution license/permission, author or model/input/seed when relevant, processing and SHA-256. Review at native scale and desktop cover crop; completion means the shipped image is visually scene-appropriate, lawful and matches its recorded bytes, not just a metadata entry.

- [ ] 1.2 **1.75 h.** Produce and commit the finished original `dungeon_interior.webp` under `web/static/art/scenes/`, depicting damp stone passage, barred cells and torchlight. Use painterly JRPG full-bleed landscape composition with open lower foreground; no UI, watermark, readable lettering, town/forest copy, placeholder or same-image rename. Deliver `dungeon_interior.provenance.json` with actual source, distribution license/permission, author or model/input/seed when relevant, processing and SHA-256. Review at native scale and desktop cover crop; completion means the shipped image is visually scene-appropriate, lawful and matches its recorded bytes, not just a metadata entry.

- [ ] 1.3 **1.75 h.** Produce and commit the finished original `ruin_interior.webp` under `web/static/art/scenes/`, depicting broken ancient columns and weathered wall fragments. Use painterly JRPG full-bleed landscape composition with open lower foreground; no UI, watermark, readable lettering, town/forest copy, placeholder or same-image rename. Deliver `ruin_interior.provenance.json` with actual source, distribution license/permission, author or model/input/seed when relevant, processing and SHA-256. Review at native scale and desktop cover crop; completion means the shipped image is visually scene-appropriate, lawful and matches its recorded bytes, not just a metadata entry.

- [ ] 1.4 **0.5 h.** Create `world/art/tests/test_bundled_interior_art.py` as a pure `unittest.TestCase` data-contract test. Decode each of the three actual shipped WebPs using the existing image admission limits; assert positive dimensions/resource bounds, three distinct checksums, matching provenance and explicit distribution terms. Tag the first docstring line `Data-contract test: bundled scene distribution and decode contract` and register the file in tools/test_data_freeze.json and exactly one non-browser shard. Run the focused command below; corruption and missing-file controls must fail naming the owned key. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.5 **0.5 h.** Create/register the exact browser method `web.tests.browser.test_browser_bundled_scene_assets.BundledSceneAssetsBrowserTest.test_interior_pack_static_decode` in the dedicated asset-browser module, using the existing real managed server and default absent operator root. Request the three actual `/static/art/scenes/<key>.webp` URLs and await image decode at 1451×790 with cover cropping. Assert successful image responses/natural dimensions, no broken img, and archive a visual-contact-sheet review in delivered provenance. Run only that one method; external generation must be unused. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.6 **0.25 h.** Document the owned files, licensing and visual acceptance in the delivered provenance records and update existing affected artwork development notes without claiming the later resolver is integrated. Obtain effective requirement IDs with the traceability tool, attach only substantively matching decode/serving assertions, update browser/shard ownership and run the final strict/contract commands below. Completion means artifacts/assets/tests/docs all belong to this pack and every gate is green. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_bundled_interior_art
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_bundled_scene_assets.BundledSceneAssetsBrowserTest.test_interior_pack_static_decode
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-scenes-interior-art --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
