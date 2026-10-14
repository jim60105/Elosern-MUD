# Tasks

Estimated total: **7.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [x] 1.1 **1.25 h.** Implement read-only room-aware scene resolution in world/art/presenter.py using the canonical descriptor and map logical identity. Enumerate room official/fault → existing shared generated archetype/fault → optional operator type/fault → required trusted bundled type/fault → distinct declared terminal. Invalid scene metadata adds configuration_invalid before town terminal; generation disabled never erases recorded failure or static fault. Add/register world.art.tests.test_scene_resolution with synthetic source precedence, root/default attribution, same-terminal dedup, malformed metadata and no queue/gallery/room/status writes. Document the source chain in the affected guide.

- [x] 1.2 **1 h.** Cut art schema v3→v4 atomically in art.py/art_view.py read inputs, registry/worker push, panels/art.js/shared validator, protocol version tables/Vue mirrors, fixtures and SceneBackdrop/AppClient readers. Scene is exactly {archetype,label,alt,artwork}, portrait catalog remains canonical. Update test_art_panel/test_art_push/protocol_art for both-side old-shape rejection, logical identity, invalid URL/version/fault entries, correlated updates and bounded envelope. No old scene serializer or alias remains.

- [x] 1.3 **1.5 h.** Rewrite SceneBackdrop display retention separately from current attempt state with scene subject_id, generation_subject, prior successful resource/version/priority/applicability. Preserve good generated image for same-scene pending/failed regeneration despite lower bundled load, while current reached faults still update. Same/higher-priority decoded source replaces it; new logical place, binding removal, revoked access or known failed retained source invalidates immediately. Fullview consumes the same displayed source and failures, keeps keyboard trap/Escape/opener restoration and cannot open broken-only content. Component tests cover fresh page, mode-only change, new place while load delayed, binding/access loss and stale events.

- [x] 1.4 **0.75 h.** Remove app-shell.css sample pseudo-elements/background URLs and SceneBackdrop sample nodes/captions, component failedUrls/independent decoder and now-unused sample-town/forest copies after their complete production reference cutover. Preserve unrelated sample-guild and any still-used legacy protocol code. Update scene/motion/fullview stories, evidence/frozen component expectations and developer docs; keep caption non-overlap and reduced/off motion but never crossfade a retained previous-place background across a move.

- [ ] 1.5 **0.75 h.** Create/register the two exact UnifiedScenesBrowserTest methods below in test_browser_unified_scenes.py with real authored room binding, generated and operator fixtures. First covers exploration/dialogue/combat same-place mode changes, same-scene pending+failed regeneration retaining good generated art, different-scene movement including pool reuse, explicit binding removal and fullview shared state. Second injects browser failures after server resolution, delays preferred room art, proves latent provisional failure, preferred room win, reached lower fault persistence, distinct terminal once and exhausted no-broken-img. Run each method independently, with no full browser batch. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.6 **1 h.** Register new backend/browser labels and substantive traceability annotations, update affected assertion role/seed ledgers rather than weakening former sample tests, then run focused backend/JS/Node commands, the two small scene smoke commands and final strict/contract gates. Complete only when fresh data with optional services disabled shows proper bundled scenes without error, all failures stay local/reached, same-scene retention never hides failed regeneration, and no previous-place image/key survives movement. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.7 **0.5 h.** Apply the explicit stable rank/source_id/retention_sources algorithm from shared design, not attempt-array index or opaque revision guesses. Add independently expected tests for metadata fault + rank-10 room replacement over retained rank-20 generated art, changing fault counts, pending with no current generated candidate, same-subject access revocation and geometry-only successful-resource reuse. Required art unavailability with no trusted current logical identity must synchronously discard prior pixels and show panel_unavailable, including initial render and movement+unavailable controls.

- [ ] 1.8 **0.75 h.** Extend the test-only unified transition fixture and seed runner for shipped scene binding/generation states. Use queue.requeue/claim/settle with the actual scene record generation_token for same-scene pending/failed/done, maps-owned authored metadata sync for room binding removal/move and real coordinator refresh. Never mutate the browser store to claim backend transition acceptance. Split shipped inventory smoke from synthetic state-machine tests, and register data-contract/browser roles. A bounded isolated test-only transition command/helper may invoke these real owners only under browser settings; it is not installed in the production cmdset. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_scene_resolution web.webclient.presentation.tests.test_art_panel web.webclient.presentation.tests.test_art_push
pnpm test -- web/webclient-app/tests/scene_backdrop.test.js web/webclient-app/tests/scene_transitions.test.js web/webclient-app/tests/core/image_attempts.test.js
node --test web/static/webclient/js/tests/protocol_art.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_unified_scenes.UnifiedScenesBrowserTest.test_room_precedence_retention_movement_and_fullview
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_unified_scenes.UnifiedScenesBrowserTest.test_provisional_and_terminal_failures_are_reached_once
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-scene-rendering --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
