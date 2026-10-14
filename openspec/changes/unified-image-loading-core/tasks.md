# Tasks

Estimated total: **7.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.5 h.** Implement lib/image-attempts.js reducer for ordered image/fault attempts, stable source rank, canonical resource-key dedup, reached-only faults, permitted terminal and safe exhaustion. Input is a normalized internal load request, not an alternate panel wire shape. Add core/image_attempts.test.js synthetic assertions for higher success hiding lower fault, lower success retaining higher fault, duplicate terminal and no recursive/broken exhaustion. No business selector, generation scheduling, private subject lookup or retry timer belongs here.

- [ ] 1.2 **1.25 h.** Implement composables/useImageAttempts.js local resource driver with active subject/epoch/attempt token, actual load plus decode success/observed natural dimensions, stale callback rejection and disposal on replacement/unmount. Reuse a successful unchanged resource key on geometry-only updates; no source crossfade or extra request. Availability input ready/expected_absent/failed drives local panel_unavailable and invalidates original save eligibility. Tests cover initial unavailable, success→unavailable, unchanged rerender, replacement, stale decode and listener disposal.

- [ ] 1.3 **0.75 h.** Integrate the driver immediately in GalleryFaceRectModal using its current single gallery-v2 exact committed image id/URL/geometry as one rank-10 original resource request with no terminal. This is ordinary internal loading input construction for one existing exact original, not a full subject descriptor or old/new protocol adapter. Keep the v2 serializer/active validator unchanged; no reader accepts a new shape here. Require active decoded natural dimensions for save and remove broken original/crop elements. Gallery v3 later replaces this caller input with its backend descriptor; the same resource driver remains.

- [ ] 1.4 **0.75 h.** Create shared ArtworkFailure.vue/category mapping and ArtworkAlpha.vue drawing primitive. The alpha primitive consumes an already observed resource result, never selects demographic/source policy; failed alpha cannot paint an opaque rectangle. Failure marker uses keyboard/assistive text and persists after lower success; expected loading/absence has no error styling. Register core/editor/shared-indicator stories/component manifest and affected evidence expectations; use these same primitives in dependent gallery/figure/avatar renderers.

- [ ] 1.5 **1 h.** Add provisional resource result support to this same local driver/reducer, keyed by resource identity/version. Success cannot settle ordered priority; failure stays latent until that source is reached; reached cached provisional outcome/terminal is reused once. Pure tests specify delayed healthy preferred source + failed provisional, reached provisional failure, superseded epoch and same-resource terminal. The first production face-editor integration exercises common loading; scene owner later activates this tested option, not a second implementation.

- [ ] 1.6 **0.75 h.** Extend focused face-editor component tests to prove failed/loading original is unsaveable, stale old dimensions cannot restore eligibility, new exact original can recover and geometry-only changes do not refetch. Preserve existing non-square pixel-square crop arithmetic, numeric draft editing, mutation correlation, Escape/cancel/focus semantics. Update frontend-vue-architecture.md with single loading/resource/result ownership and internal request versus future canonical wire distinction.

- [ ] 1.7 **0.5 h.** Create/register test_browser_image_loading_core.ImageLoadingCoreBrowserTest.test_original_failure_has_persistent_local_state. Add test-only seed/image_editor_fixture.py and bounded transition helper wiring via seed/runner.py only under browser settings: append a real exact original card via gallery.append_card and use actual gallery action controls. Intercept its image after server resolution with invalid media, assert broken originals removed, keyboard explanation available and outbound geometry writes absent. Run this one method; no client-injected fake business snapshot establishes original identity. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.8 **1 h.** Register new component/browser/module ownership and substantive lifecycle/editor requirement claims, run focused pnpm/editor/browser and final strict/contract commands, preserving active v2 validators/shape and CI branch/evidence gates. Completion means the common mechanism has a real production editor consumer, no dual-shape shim or hidden future core implementation, and all provisional/state semantics are executable in focused synthetic tests. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_gallery_panel
pnpm test -- web/webclient-app/tests/core/image_attempts.test.js web/webclient-app/tests/components/gallery_original_editors.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_image_loading_core.ImageLoadingCoreBrowserTest.test_original_failure_has_persistent_local_state
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-image-loading-core --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
