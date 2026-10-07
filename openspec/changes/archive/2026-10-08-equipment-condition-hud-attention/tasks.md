## 1. Deterministic provenance

- [x] 1.1 Extend the frozen condition model with the exact bounded provenance contract in design D1 and add pure source resolution beside existing equipment accessors. Verify synthetic ownership tests establish exact instance/definition/source agreement, ordinary item-looking sources, declared-but-absent orphan versus undeclared colon-shaped instance classification, inconsistent unknown attribution, stable label ordering, and no handler mounting or Attribute writes.
- [x] 1.2 Capture actual and equipment-free condition contexts from one read snapshot, preserve independent buff instances, project logical buff definitions, and reuse the existing matcher once for each context as design D3 defines. Verify synthetic status-query tests cover equipment-induced and mixed exposure thresholds, saturated 極高 and net-zero/clamped overlays, unrelated gear, combined equipment/state prerequisites, and same-definition attached/independent buff rules; assert actual match and combat/breakdown adjustment parity.
- [x] 1.3 Classify each buff instance and matched rule without removing conditions or changing severity, stacking, duration, or values. Verify repeated materialized/unmaterialized reads in existing status-boundary tests leave storage and time unchanged, and possession tests use the resource owner's provenance while retaining the controlled actor identity.

## 2. Exact status schema cutover

- [x] 2.1 Serialize provenance from the frozen model, reject invalid model provenance through existing unavailable/error patterns, and advance the presenter-owned status version and browser allowlist/validator to 3, preserving full-title and unavailable-form behavior. Verify presenter, registered-version parity, and Node protocol tests accept both v3 availability forms, reject v2, and reject missing/extra/invalid provenance fields, inconsistent kind/source pairs, duplicate sources, invalid identifiers/labels, ordering violations, and source-count bounds without committing malformed messages.
- [x] 2.2 Cut over every affected condition/status fixture and producer in existing backend tests, browser support, dependency-free Node tests, Vue tests, stories, and possession coverage. Verify the focused schema/parity and existing fixture-consumer suites pass with no legacy severity-only defaults, aliases, or compatibility readers, and keep envelope protocol version 1 and unrelated panel versions unchanged.

## 3. Contextual attention and truthful detail

- [x] 3.1 Replace only the adverse-condition term in `isVitalsVisible` with the committed provenance-aware predicate; preserve status availability, dialogue/creation gates, combat, depleted resources, low HP, mounted trailing-bar memory, existing transitions and focus rescue. Verify `vitals_visibility.test.js` and focused store/component tests establish the full severity/provenance matrix, unavailable combat, mode precedence, same-code provenance replacements, accepted equip/unequip and stored-state changes, stale revisions, retired epochs, and a first hit while previously hidden.
- [x] 3.2 Extend existing shared condition detail with supplied equipment labels, mixed independent-source wording and neutral unknown-source wording. Preserve all rows and handle duplicate-code buff instances using local row/tooltip identities, including overflow. Verify condition-label/chips and character-status drawer tests establish identical accessible/tooltip/overflow source detail, exact durations/values, full-status visibility while the dock is hidden, and detail without an available character panel.

## 4. Integration and documentation

- [x] 4.1 Extend one focused managed browser journey using synthetic actor/equipment fixtures for hidden equipment-only adversity, full-status disclosure, an independent or depleted-resource revealing trigger, and focus rescue when that trigger clears. Register any new test methods in `.github/browser-shards.json` and any new non-browser modules in `.github/evennia-shards.json`; verify the focused journey and shard-ownership contract pass without live probes or shipped-content behavior fixtures.
- [x] 4.2 Update the existing relevant development/HUD documentation with the source contract, clean v3 cutover, unchanged dialogue/creation gates, and the stored 極高/Yuna caveat. Obtain canonical main-spec requirement IDs through `tools.spec_traceability list` at the workflow's spec-sync point and annotate substantive behavior tests for the changed requirements; verify traceability and documentation refer to actual behavior without promising baseline suppression.
- [x] 4.3 After all implementation edits land, run the smallest affected backend status/equipment/presenter and possession labels, Node protocol/parity files, and focused Vitest visibility/detail/store tests once as a final batch, plus the focused browser journey from 4.1. Run `openspec validate equipment-condition-hud-attention --strict` and `uv run --locked python -m tools.contract_gate`; record exercised outcomes and leave complete browser/evidence verification to CI. Verify all implementation tasks have observable evidence before marking them complete or requesting archive.

Traceability sequencing: apply annotates the changed existing canonical main-spec
requirement IDs. New canonical requirement IDs become available only after the
archive workflow syncs these deltas. Their substantive tests will receive those
annotations at the archive post-sync contract-gate repair on the feature branch,
before merge. Apply does not sync or archive main specs.

## Exercised verification

- The initial backend discovery exceeded the 100-test local guard and did not
  run. The narrowed 99-test status/equipment/breakdown batch exposed fixture
  mistakes and the new exposure-consumer classification. Corrected failed
  cases and affected breakdown/allowlist fixtures passed in a 32-test followup.
  The separate presenter/possession/schema/shard/frozen-contract batch passed
  all 41 tests.
- The four focused dependency-free protocol files ran 41 tests. One new source
  label minimum assertion exposed a missing minimum check; the corrected core
  file passed all 14 tests. Character/local-map/transport tests passed.
- The eight focused Vitest files ran 102 tests. The new mode/epoch fixture
  needed to respect existing shell-owned gates and transport transitions.
  Corrected visibility/application tests plus the mode-gate file passed all
  61 tests; the other seven initial files passed their detail/store/trail tests.
- `pnpm run build` passed. The focused managed
  `SceneTransitionsBrowserTest.test_vitals_reveal_and_inert` passed, including
  hidden equipment-only adversity, full-status source disclosure, depleted-HP
  reveal and focus rescue. An initial attempt before building the worktree's
  bundle could not initialize the browser bridge; rebuilding supplied the
  missing local bundle. No new browser methods or non-browser test modules
  were introduced, so shard ownership remained unchanged.
- Strict change validation passed. `tools.contract_gate` passed with 1996
  covered requirements, zero traceability/lint violations, and all 18 contract
  tests passing. Existing canonical IDs were obtained through
  `tools.spec_traceability list`; new IDs follow the sequencing note above.
- Complete managed-browser and evidence verification remain CI-owned.
