# Tasks

Estimated total: **7.5 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [ ] 1.1 **1.25 h.** Repair world.rules.art_view and presentation/party.py/exploration.py membership/reference flow so existing-authorized roster/current figure/party/look/dialogue/combat subjects get complete admitted descriptors without real-URL gates. Preserve account ownership, discovered/visible view scope, bounds, current-character possession rules, ages and monster species; never scan unknown/private subjects to fill a catalog. Extend test_art_view, test_roster, test_party_panel and focused exploration tests for missing/pending/failed/alpha-only refs, capped/excluded controls and correlated same-snapshot catalog joins. Document catalog admission versus real-image eligibility in affected development notes.

- [ ] 1.2 **1.25 h.** Atomically change art portrait catalog to {artwork,context} at art v3 and roster portrait to full descriptor at roster v3. Keep scene shape unchanged in this slice, party v2/exploration v4 reference syntax unchanged. Migrate art.py/roster.py serializers, registry constants, active panels/art.js/misc.js and all envelope/allowlist/Vue version mirrors, worker completion paths and fixtures. Add protocol_roster_artwork.test.js; update protocol_art/protocol_party and Python parity tests for old-flat rejection, full terminal/fault fields, independent generation and bounded authorization. No dual-shape client fallback is allowed.

- [ ] 1.3 **1.5 h.** Migrate ReferenceArtwork to shared useArtwork and the existing observed alpha primitive in both stage and cover layouts, preserving successful resource geometry and separate terminal geometry. StageActor, AppClient drawer/current/focus figures, companion and foe lineups must pass the complete admitted descriptor. Remove figure failedUrl/mask probes and duplicate classification; mask failure means identity text plus persistent local indication, never rectangular fill. Migrate all avatar readers to the canonical shape and shared real-only load results now so no old reader ships on the new wire; next avatar slice owns template consolidation/grapheme policy. Update targeted component tests for alpha failure, reached preferred fault+lower success and stale subject events.

- [ ] 1.4 **0.75 h.** Update portrait/figure stories, source fixtures, existing evidence claims and the affected developer contracts for full descriptors and both-mode alpha policy. Preserve Core/ReferenceArtwork manifest family, layout/motion/targeting and true portrait versus silhouette placement. Delete only obsolete field-copy/selector code after every production import/caller is migrated; unrelated legacy protocol modules remain unless genuinely unused.

- [ ] 1.5 **0.5 h.** Create/register UnifiedFiguresBrowserTest.test_exploration_dialogue_combat_and_drawer_share_descriptor in test_browser_unified_figures.py and update the named existing stage-silhouette failure browser assertion. Use real exploration focus, dialogue, deterministic combat and character drawer paths; inject selected source error only after server resolution and assert correct species/demographic alpha, unchanged generation, local persistent failure and no broken img across these surfaces. Run each named method independently. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.6 **1 h.** Register all new labels/shard claims, update substantive effective requirement assertions without blanket decorator replacement, then run the focused backend/component/Node commands and small browser methods below plus final strict/contract gates. Completion means every portrait production reader, not only ReferenceArtwork, agrees on the canonical shape, no roster omission remains and refs exist without real imagery while privacy/eligibility/read-only boundaries remain intact. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [ ] 1.7 **0.5 h.** Extend the test-only unified image seed/transition fixture for scoped roster/co-located party/focus/dialogue/combat entries and caller visibility. Assert initial required-art failure, available→unavailable after success, expected creation absence and excluded-reference controls through artworkAvailability. Every avatar/figure joiner must route failed availability to the shared state rather than return silent null. Register test-only fixture symbols and changed methods in the existing harness/data ownership contracts; no production command route is added.

- [ ] 1.8 **0.75 h.** Migrate the existing direct presenter assertions in world/art/tests/test_species_portrait_identity.py, test_service/test_autogen_retrofit.py, test_service/test_monster_gallery.py, test_worker/test_store_isolation.py and world/rules/tests/test_character_creation/test_portrait_finalization.py to canonical candidate/terminal geometry and source facts, preserving species isolation, ages, no-write and distinct owner controls. Add the exact exploration package, protocol version parity, switcher and ParticipantFrame focused assertions. Include an art-v3 test proving canonical portraits coexist with unchanged flat scenes; do not accidentally change generic scene resolve_subject delegation. Create core/participant_frame.test.js and core/character_switcher.test.js for these exact current reader assertions if no equivalent focused file exists; register corresponding Vue evidence claims rather than leaving the listed commands uncollected.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_presenter world.art.tests.test_gallery_fallback world.rules.tests.test_art_view
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_art_panel web.webclient.presentation.tests.test_roster web.webclient.presentation.tests.test_party_panel
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_species_portrait_identity world.art.tests.test_service.test_autogen_retrofit world.art.tests.test_service.test_monster_gallery
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb world.art.tests.test_worker.test_store_isolation world.rules.tests.test_character_creation.test_portrait_finalization web.webclient.presentation.tests.test_exploration_panel
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_protocol
pnpm test -- web/webclient-app/tests/core/reference_artwork.test.js web/webclient-app/tests/app_client_stage_actor.test.js web/webclient-app/tests/core/companion_lineup.test.js web/webclient-app/tests/core/foe_lineup.test.js web/webclient-app/tests/core/participant_frame.test.js web/webclient-app/tests/core/character_switcher.test.js
node --test web/static/webclient/js/tests/protocol_art.test.js web/static/webclient/js/tests/protocol_party.test.js web/static/webclient/js/tests/protocol_roster_artwork.test.js web/static/webclient/js/tests/protocol_roster.test.js web/static/webclient/js/tests/protocol_exploration_a.test.js web/static/webclient/js/tests/protocol_exploration_b.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_stage_silhouette.StageSilhouetteBrowserTest.test_a_resolved_image_replaces_the_silhouette_and_failure_returns_to_it
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_unified_figures.UnifiedFiguresBrowserTest.test_exploration_dialogue_combat_and_drawer_share_descriptor
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-portrait-image-contract --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
