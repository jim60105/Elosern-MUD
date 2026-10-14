# Tasks

Estimated total: **7.25 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.25 h.** Add frozen world/art/scene_definitions.py declarations for all ten registered archetypes plus dream_throne using the exact terminal map, and a closed authored room-art-key registry. All eleven lawful scene files/provenance already exist from the four prerequisite artwork packs; do not reproduce/promote uncertain sample bytes in catalog. Add/register world.art.tests.test_bundled_scenes to enforce complete registry-to-decoded-file coverage, invalid terminal/unknown-key failure and asset resource bounds. Visually inspect the completed eleven-file inventory and record scene identity/composition review; catalog cannot land with a partial registry.

- [ ] 1.2 **1.5 h.** Extend official.py/service startup admission to immutable bundled-scene entries at the fixed web/static/art/scenes root and operator scene/room kinds at ART_OFFICIAL_ROOT. Reuse bounded decoder/fingerprints/no_follow, validate scene/room keys against authored registries and preserve per-entry admission isolation and restart-only replacement. Add synthetic catalog fixtures for unknown keys, corrupt files, symlinks and selected defaults in test_official_catalog; completion means unrelated valid entries still admit and no persistent record/root write occurs.

- [ ] 1.3 **1.5 h.** Extend existing web/art_media.py with closed /art/bundled-scene/<key>/<sha256>.webp identities; refactor common safe opening/response primitives in place rather than copying the handler. Admit current fingerprint only and use a distinct fixed trusted root, preserving actual 404, MIME, confinement and no-follow behavior. Extend test_art_media with missing file, traversal, stale fingerprint, symlink replacement and operator collision cases; all four existing media families must retain their current admission behavior.

- [ ] 1.4 **1 h.** Create/register web.tests.browser.test_browser_scene_media.SceneMediaBrowserTest.test_bundled_namespace_and_operator_isolation. On the real application request an admitted bundled scene, an optional operator scene and a stale/missing identity, proving correct decoded bytes, source-root isolation and actual 404 after resolution. No mock media handler or static-only bypass establishes this serving smoke. Run this one-method browser command below. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.5 **1 h.** Update official-artwork-deployment.md for scene/room external layout, registered keys, separate trusted bundled namespace, complete offline collection and unchanged no-write/restart semantics. Register new tests/data contracts and update traceability claims for the modified tracked-art exception without weakening the closed alpha vocabulary or runtime/seed exclusion. Completion means documentation no longer says all official artwork blobs are external, and missing definitions/images/terminals fail the named contract.

- [ ] 1.6 **1 h.** Run focused catalog/bundled/media tests, the single changed-path browser method and final strict/contract commands below. Classify mechanisms as synthetic and actual inventory checks as registered data-contract tests; retain >=80% exact-root aggregate branch and observability gates for CI without running local shards/full browser/evidence suites. Completion means source/type/root/fingerprint failures are independently covered and no generation service is needed to serve the collection. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_bundled_scenes world.art.tests.test_official_catalog web.webclient.tests.test_art_media
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_scene_media.SceneMediaBrowserTest.test_bundled_namespace_and_operator_isolation
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-scene-catalog --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
