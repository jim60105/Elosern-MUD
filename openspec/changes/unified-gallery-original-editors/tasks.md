# Tasks

Estimated total: **5.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.5 h.** Replace GalleryFaceRectModal local load-success/dimension flags with useArtwork(exact original descriptor, terminalPolicy none). Reset eligibility synchronously on subject/image/revision changes; only active exact resource successful decode plus positive observed dimensions permits save. Remove broken original and crop-preview img elements on failure, distinguish loading/failed text and retain accessible failure indication. Preserve pixel-square non-square-image math, numeric draft editing, one dispatch and existing official component-only action ids. Create components/gallery_original_editors.test.js covering 768×1024 geometry, failed original, late old callbacks, harmless rerender and successful new original recovery.

- [ ] 1.2 **1.25 h.** Migrate GalleryStageTransformModal to the same original load proof and observe the fixed adult-size reference as a separate display-only subject/resource. Keep reference dimensions out of original success; failure of reference has its own marker and never authorizes saving. Preserve transform order, drag/range clamp, reset, existing correlated success/revision lock, rejection drafts and cancel/focus behavior. Extend the same focused tests for original-failed/ruler-healthy, original-healthy/ruler-failed and source replacement while save is pending; document this exact eligibility policy in existing editor development notes.

- [ ] 1.3 **0.75 h.** Update gallery original-editor/loading/failure/recovery stories and component/evidence registration, deleting only now-dead editor image flags/listeners. Confirm GalleryDetailRail official personal geometry dispatch still uses exact committed identity and only the edited component. Focused component assertions must prove no silhouette, other card, scene background or ruler becomes dimensions/edit target and no stale resource event closes the dialog.

- [ ] 1.4 **1 h.** Create/register both named OriginalEditorsBrowserTest methods below through real gallery/card and official selection/editing controls. After server resolution intercept original with invalid media and try keyboard save in crop/stage dialogs; outbound recorder must contain no geometry write. Then provide a repaired descriptor version and verify real dimensions enable exactly one save; intercept the adult reference separately and verify its own indication without changing original identity. Run each browser method as its own small command. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.5 **1 h.** Register new browser methods and any module/evidence claims exactly once, update effective requirement decorators and affected docs beside the assertions. Run the listed focused gallery/editor tests, the two separate browser methods and final strict/contract commands. Completion means failed/loading states are distinguishable, broken originals removed, only current decoded originals save and all existing accessibility/correlation/geometry semantics remain. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_gallery_panel
pnpm test -- web/webclient-app/tests/components/gallery_original_editors.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_original_editors.OriginalEditorsBrowserTest.test_failed_original_never_saves
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_original_editors.OriginalEditorsBrowserTest.test_new_original_recovers_and_ruler_failure_is_local
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-gallery-original-editors --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
