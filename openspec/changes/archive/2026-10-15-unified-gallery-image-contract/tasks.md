# Tasks

Estimated total: **6.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [x] 1.1 **1 h.** Create production-used frozen world/art/descriptors.py and bounded presentation/artwork.py with the exact fields, origin/reason enums and limits in design.md. Implement exact selected gallery-card and official-row descriptor construction: one original identity plus attributed source/metadata facts and separately selected subject alpha terminal. Missing readable card output becomes a fault row rather than omission; card/pending/failed status and recorded generation remain independent. Add/register world.art.tests.test_descriptors with synthetic classification/order/read-only/size/surrogate tests and document the canonical wire fields in affected developer notes.

- [x] 1.2 **1.5 h.** Cut gallery schema v2→v3 in presentation/gallery.py and registry registration; migrate exact card/official row shapes from design.md. Update active protocol/artwork.js and panels/gallery.js, envelope/allowlist/constants/Vue mirrors and all protocol fixtures together, preserving subject authorization, selected membership, card counts/chips/order, official action governance and JSON/source URL ceilings. Add protocol_gallery_artwork.test.js plus dual-direction Python parity assertions for image/fault entries, invalid bounds/origins, forbidden URL in a fault, old flat fields and invalid candidate geometry. Completion means old fields are rejected by both validators and no production reader expects them.

- [x] 1.3 **1.25 h.** Reuse loading-core ArtworkFailure.vue/ArtworkAlpha.vue and resource driver; create only ArtworkPreview.vue and the canonical useArtwork/availability binding. Integrate GalleryPanel, GalleryDetailRail, GalleryBindingDrawer and GalleryGenerateDrawer thumbnails/reference previews for exact originals. Render alpha only after the same canonical mask resource succeeds; failure leaves identity text without rectangular fill. Migrate both original editors to direct v3 exact descriptor reads in this same wire cutover while retaining the original editing geometry lifecycle while its shared face-resource loading is already integrated by loading-core until the explicitly dependent editor slice. Remove preview-specific failed-URL/source caches, keep pending/failed cards truthful and never select another original. Component tests assert keyboard-accessible persistent markers and no save on substitutes.

- [x] 1.4 **0.75 h.** Update gallery/app-client/component tests, v3 fixtures/stories and existing Vue gallery evidence wrappers to substantively establish canonical preview states. Register new component families/stories in component-manifest.json and relevant frozen/evidence expectations, preserve coverage ownership and document expected absence versus reached failures. Do not create a second figure selector; ReferenceArtwork later reuses the alpha primitive, while editors consume exact originals only.

- [x] 1.5 **0.5 h.** Create/register web.tests.browser.test_browser_gallery_image_contract.GalleryImageContractBrowserTest.test_original_404_falls_back_with_local_failure. Through a real committed gallery selection, intercept only its original media after backend resolution with 404/invalid bytes; assert the correct subject alpha preview or text, persistent keyboard-accessible marker, unchanged card/job status, same selected image id and no substitute edit target. Run that one-method smoke below at 1451×790 and no live generation dependency. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.6 **1 h.** Register new non-browser and browser labels exactly once, derive effective canonical requirement IDs for substantive tests and update the existing traceability role/seed ledgers. Run focused backend, pnpm and Node files below, the single gallery smoke and final strict/contract commands; retain active protocol, shard, branch-coverage and observability gates without local CI shards/full browser/evidence verification. Completion means this first shared implementation is production-integrated, not scaffold-only, and every gallery reader runs on one v3 shape. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.7 **0.5 h.** Extend the existing test-only seed/image_editor_fixture.py from loading-core for gallery v3 exact original/runtime/official rows and pending/failed synthetic rows. Update seed/runner.py flag dispatch and gallery mode of the bounded test transition helper; use real append_card/set_default/select actions and actual descriptor serialization rather than injected business payloads. Add initial required-gallery unavailable and ready→unavailable→ready component assertions through shared availability. This fixture/availability work is included in this budget, not left to an unnamed final change.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_descriptors web.webclient.presentation.tests.test_gallery_panel web.webclient.presentation.tests.test_protocol
pnpm test -- web/webclient-app/tests/core/image_attempts.test.js web/webclient-app/tests/components/gallery.test.js web/webclient-app/tests/app_client_gallery.test.js
node --test web/static/webclient/js/tests/protocol_gallery_artwork.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_gallery_image_contract.GalleryImageContractBrowserTest.test_original_404_falls_back_with_local_failure
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-gallery-image-contract --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
