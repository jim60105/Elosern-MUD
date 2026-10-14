# Tasks

Estimated total: **4.75 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1 h.** Replace world/narrative/dream_surface.scene_art_url raw helper with read-only world.art resolver invocation for explicit dream_throne and active owner/session subject_id. Preferred source stays exact npc/dream_goddess/dream-throne.webp; next are required bundled dream_throne then distinct city_street. generation_subject/state are null. Add/register web.webclient.presentation.tests.test_dream_artwork and extend world.narrative.tests.test_dream_surface for optional absence/configured fault/order, no sleeper-background inheritance and no queue/lifecycle/authoring mutations. Update the guide dream-source description.

- [ ] 1.2 **1 h.** Cut dream schema v2→v3 atomically across dream_surface state, presentation/dream.py constant/registry, active panels/dream.js/shared artwork validator, all envelope/allowlist/Vue mirrors and fixtures. state.scene_art becomes the descriptor rather than string; preserve every other bounded field including requirements, revision and owner/session identity. Extend protocol_dream and Python parity tests for canonical attempts/faults, old raw-URL rejection, source bounds and wrong-owner exclusion.

- [ ] 1.3 **1 h.** Integrate DreamPanel with the existing shared scene renderer/load/failure path; remove raw image-url failed flags/listeners and dead helper consumers. Preserve modal regions, text/reply pacing, unsent words, story requirements, focus traps, awaken/cancel semantics and no physical-state effects. Update dream component tests/stories/evidence registration for healthy optional source, offline bundled dream, preferred failure+bundled success, stale dream-session callback and fullview identical source/error state; a local media error must never mutate dream collaboration.

- [ ] 1.4 **0.75 h.** Create/register DreamArtworkBrowserTest.test_offline_dream_and_official_failure_use_shared_scene in test_browser_dream_artwork.py. Enter dream through the real committed sleep/action surface with optional art absent, verify bundled dream rather than physical scene, then use a configured preferred image with browser-invalid media after backend resolution. Assert bundled fallback and persistent accessible marker, shared fullview, usable dialogue/awakening and unchanged generation queue count. Run only this method, not the complete dream/browser suite. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.5 **1 h.** Register every new label/method/evidence claim exactly once, derive effective dream requirement IDs and update substantive tests/docs. Run the focused backend/JS/Node commands, one-method real browser smoke and final strict/contract gates below. Completion means all dream production consumers use one v3 shape and shared scene state without an operator-file move, generated dream job, sleeper background, lifecycle mutation or new player command. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.narrative.tests.test_dream_surface web.webclient.presentation.tests.test_dream_artwork
pnpm test -- web/webclient-app/tests/dream.test.js
node --test web/static/webclient/js/tests/protocol_dream.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_dream_artwork.DreamArtworkBrowserTest.test_offline_dream_and_official_failure_use_shared_scene
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-dream-rendering --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
