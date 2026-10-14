# Tasks

Estimated total: **5.75 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1 h.** Retain explicit ART_OFFICIAL_ROOT configuration provenance at settings import, without adding a runtime setting or guessing from empty catalog length. Add immutable bounded root-health facts distinguishing absent default optional root, healthy empty root, explicit missing root and unreadable root. Extend test_official_catalog with each configuration; completion means startup always proceeds and only unexpected conditions retain failure facts.

- [ ] 1.2 **1.5 h.** Extend OfficialCatalog snapshot with source-scoped rejected identity, requested manifest default, applicable malformed metadata and selected safe-geometry facts. Missing/rejected explicit default must precede deterministic substitute; unselected sibling refusal must never become a selected-source fault. Facts survive exhausted diagnostic budgets and do not include raw paths/exceptions in public reason values. Add/register world.art.tests.test_art_source_faults with synthetic independent source expectations and diagnostic-budget controls; assert matching requests retain faults while unrelated healthy entries stay clean.

- [ ] 1.3 **1 h.** Preserve named-import facade boundary diagnostics with kind/key/source business identifiers in context, distinct success/failure/fallback categories and exception or reasoned exemptions. Maintain no-write/snapshot-only reads and per-entry isolation. Update deployment guide troubleshooting to explain normal default absence versus explicit/unreadable failure and source-specific defaults. Focused tests patch caller bindings and compare records/files before/after startup/read.

- [ ] 1.4 **0.75 h.** Add/register web.tests.browser.test_browser_scene_media.SceneMediaBrowserTest.test_configured_root_failure_keeps_bundled_media. Start the real app with explicitly unavailable optional operator root, request admitted bundled media and verify 200/decode plus retained bounded startup source_unavailable diagnostics; missing operator media is 404, not substitute 200. This is startup/media-boundary smoke, not a premature claim that pending portrait/dream cutovers already display its marker. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests. In browser_settings.py isolate the absent default optional root under runtime cache while preserving unconfigured provenance; configured fault tests instead set the explicit override. This is test-only configuration, not a production knob.

- [ ] 1.5 **1 h.** Register every new test module/method exactly once, update affected requirement claims from effective specs and keep data-freeze roles explicit. Run the listed focused tests/browser method and final observability/strict/contract gates. Completion means an empty index cannot erase root/default/selected metadata facts, while a healthy image is unaffected by unselected rejection. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.6 **0.5 h.** Exercise a selected explicit default missing/rejected case through actual startup catalog indexing and a real selected-source lookup in world.art.tests.test_art_source_faults, without mocking the catalog accessor; assert default-fault-before-substitute fact order and unchanged source files/records. Record this changed-path runtime smoke result with the focused handoff, preserving browser-only versus backend diagnostic boundaries. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_official_catalog world.art.tests.test_art_source_faults
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_scene_media.SceneMediaBrowserTest.test_configured_root_failure_keeps_bundled_media
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-art-source-faults --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
