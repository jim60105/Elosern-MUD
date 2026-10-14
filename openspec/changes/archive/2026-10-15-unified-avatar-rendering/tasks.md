# Tasks

Estimated total: **5.25 engineer-hours**, strictly below eight, including owned artwork, tests, fixture/smoke work, documentation and gates. Every numbered checkbox includes time, concrete files/algorithm/assertions and completion proof. Do not replace real deliverables with placeholders.

## Worker execution contract

Specified for a gpt-luna apply worker. Read this proposal/design/deltas and the shared exact interface in `../unified-gallery-image-contract/design.md`; apply only after Batch prerequisites land. No unresolved product decisions remain. Implement the specified slice without adding retries, telemetry, compatibility, migrations or unrelated cleanup. All new test files/methods named below are deliberate deliverables and must be created and registered by their owning task. Existing commands use actual repository labels/root pnpm scripts.

Record each changed assertion's role, effective requirement and detectable defect before changing it. Synthetic mechanism tests use independently expected inputs/outcomes; actual authored asset/registry checks carry `Data-contract test: <rationale>` and the existing freeze ledger; representative smoke uses real production construction/selection/serving rather than client-manufactured business facts. Obtain canonical IDs with `uv run --locked python -m tools.spec_traceability --repo-root=/tmp/mud-unified-image-effective-specs list` against a scratch equivalent merged specification tree and the same repository test sources; follow normal apply/archive activation of new IDs without unknown/retired claims or weakened current main gates.

## 1. Complete the owned vertical slice

- [x] 1.1 **1.25 h.** Implement AvatarArtwork.vue using the existing shared real-only lifecycle and successful candidate face geometry through faceCropStyle. Replace character-identity portraitGlyph/name initial with trim+Intl.Segmenter grapheme selection and a neutral empty-name symbol. Add core/avatar_artwork.test.js with combining, astral, ZWJ, whitespace/empty names, multiple real candidates with different face rectangles and a spy proving no silhouette URL is requested. Preserve zoom cap/geometry validation and ignore stage transforms; document the common avatar contract.

- [x] 1.2 **1.5 h.** Integrate AvatarArtwork into CharacterSwitcher pill/all roster rows, PresenceRail person slots, PartyDrawer companion rows, ParticipantFrame combat rows and any active dialogue avatar caller found in the portrait dependency caller inventory. Replace duplicate templates and source/failure logic, preserving object/count rail symbols, keyboard composites, focus, current ownership and actions. Update app_client_presence_rail and party_drawer component assertions plus existing switcher/participant tests; identical descriptors must have identical real-only attempt/fault behavior on every surface.

- [x] 1.3 **0.75 h.** Use the shared ArtworkFailure category mapper with a compact focusable marker and associated assistive text on every small avatar. Verify keyboard can reveal the explanation without hover and normal expected missing/pending/disabled state has no error style. Update avatar stories/component manifest and existing evidence wrappers/frozen required expectations; remove obsolete avatar-local failed-URL sets/helpers without new global cache.

- [x] 1.4 **0.75 h.** Create/register AvatarArtworkBrowserTest.test_roster_presence_party_participant_fallback_is_accessible in test_browser_avatar_artwork.py. In the real client exercise owned switcher, presence, party and a deterministic combat participant, intercept their selected real media after resolution, and verify correct grapheme initials or later portrait, persistent accessible marker, keyboard explanation and zero alpha resource requests. Run only this method at desktop viewport. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

- [x] 1.5 **1 h.** Register browser/component evidence and shard ownership, obtain effective requirement IDs and attach matching assertions, then run focused backend/JS commands, the one-method browser smoke and final strict/contract gates below. Completion means all listed avatar surfaces share one renderer with no per-caller source selection, Unicode breakage, silhouette requests or hidden reached faults. Concrete harness/seed/setup and transition ownership is specified in design.md under Concrete browser fixture ownership; select the owning mode only and set shipped catalogs before startup for real built-in inventory tests.

## 2. Focused commands and objective acceptance

Commands below are planned for implementation, **not proposal creation**. Run from repository root. Write `/tmp/mud-unified-image-tests.env` with exactly `MUD_TEST_SETTINGS=1` and trailing newline through the file-writing tool. Use the single-token --env-file spelling, never an inline environment prefix. Every local command stays under ten minutes; each browser line is its own one-method batch.

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_roster web.webclient.presentation.tests.test_party_panel
pnpm test -- web/webclient-app/tests/core/avatar_artwork.test.js web/webclient-app/tests/app_client_presence_rail.test.js web/webclient-app/tests/data/party_drawer.test.js
```

Changed-path real browser smoke, one independent command per method:

```sh
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_avatar_artwork.AvatarArtworkBrowserTest.test_roster_presence_party_participant_fallback_is_accessible
```

Objective completion requires zero exit status from these focused commands and the exact observable assertions in the checkboxes/delta scenarios. Record the successful resource/subject identity, reached failure, generation state or original dimensions relevant to the boundary. Existing wire owners also run the named parity/old-shape rejection controls. New browser fixtures use the concrete runtime/seed/transition plan in design.md; actual built-in inventory uses shipped mode before seed/startup, pure mechanism tests remain synthetic.

## 3. Required handoff gates

These checks are included in the implementation/gates checkbox time above. Register every new non-browser module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Update affected component/story/evidence/frozen registration and substantively matching traceability claims, preserving current validators, observability/test-data contracts and exact-root >=80% aggregate branch coverage. Run:

```sh
uv run --locked --env-file=/tmp/mud-unified-image-tests.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract
uv run --locked python -m tools.observability_lint check
openspec validate unified-avatar-rendering --strict
uv run --locked python -m tools.contract_gate
```

The contract gate covers current-spec traceability, test-data/observability lints and shard/frozen ownership. CI owns full managed-browser suites, CI shards, aggregate coverage and `tools.spec_traceability verify --evidence`; do not run them locally. Update affected sections of `docs/development/official-artwork-deployment.md` and/or `docs/development/frontend-vue-architecture.md` in the same owning work, not in a final catch-up batch. Production player command syntax/availability stays unchanged, so command docs are intentionally unchanged. Test-only transition commands exist only in isolated browser settings/cmdsets and must never be installed in production.
