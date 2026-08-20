## 1. Phase-0 public contract audit

- [x] 1.1 Enumerate every implementation-bound contract across `openspec/specs/webclient-*/spec.md` and the `web/tests/browser/` suite: the `window.Elosern.*` façades, the WebClient-plugin `onKeydown` path, `getElementById` / `#` target ids the keyboard router and Playwright assert, and the versioned layout-persistence keys
- [x] 1.2 Classify each identified contract as preserve-via-bridge or delta, recording the affected requirement, the decision, the applying change named per entry (the bridge change `webclient-vue-08-wire-bridge-contracts` (C2) for bridge-contract re-expressions; the flip change `webclient-vue-10-wire-views-browser` (C4) for shell-identity and DOM-remap edits), and the rationale
- [x] 1.3 Freeze the façade-bridge surface (the exact `window.Elosern.{Protocol, KeyboardRouter, narrativeInput, actions}` members) and the complete `MODIFIED`/`RENAMED` delta list; commit both as `docs/development/webclient-vue-frozen-contract-audit.md` (a stable path that survives this change's archive, so the applying changes consume one canonical deliverable)
- [x] 1.4 Confirm the frozen list is self-contained (C2 can apply it without re-deriving it) and that A1 modifies no source spec, server, transport, or `js/elosern` file

## 2. Commit the 設計稿 to docs

- [x] 2.1 Copy the validated 設計稿 (`index.html` + its self-hosted font/asset files) into `docs/design/` as a self-contained offline file set with no CDN references
- [x] 2.2 Add a `docs/_sidebar.md` design-draft entry linking the 設計稿
- [x] 2.3 Add a dependency-free top-level test asserting the 設計稿 file exists under `docs/`, is linked from `docs/_sidebar.md`, and references no remote/CDN asset
- [x] 2.4 Run the new top-level test and the docs check green; confirm this change touches no other capability, server, OOB, or transport file

## 3. Traceability (archive gate)

- [x] 3.1 Add the dependency-free top-level behavior test for the new `webclient-browser-verification` frozen-contract requirement (asserting the frozen-contract audit exists at its stable path with the frozen façade surface + the complete, non-overlapping `MODIFIED`/`RENAMED` delta list, and is declared the bridge change's binding input); run it, and run `uv run --locked python -m tools.spec_traceability check` green (the test carries no annotation yet: the canonical requirement ID exists in the main spec only once the delta is synced)
- [x] 3.2 At archive, after the delta is synced into `openspec/specs/webclient-browser-verification/spec.md`, annotate the 3.1 test with `covers_requirement` using the literal canonical ID from `uv run --locked python -m tools.spec_traceability list`, run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow (shared `OPENSPEC_TEST_EVIDENCE` across the test entry points) so the gate is green at this change's archive (done 2026-08-20: delta synced, the 3.1 test's five substantive methods annotated with the canonical ID, `check` green at 1008/1008 covered, `verify --evidence` green for the new requirement under the shared evennia + top-level evidence; the 32 remaining uncovered requirements are all managed-browser-suite evidence, parity with master since A1 touches no browser code — the CI quality gate supplies their evidence)

## Post-archive revision (2026-08-20, synchronous rubber-duck critique)

The synchronous critique reviewed this change's frozen deliverable and surfaced two blocking gaps,
both fixed in the deliverable itself (the stable docs path is the binding input, so the revision
does not reopen the archived artifacts):

- **§2.3 completeness:** five missed managed-browser target groups were frozen as
  `REMAP-TO-TESTID` rows (`creation-concept-submit` / `creation-form-message` / `creation-race-<i>`,
  `exploration-detail` + class, `services-quantity` / `services-quantity-value`); the harness login
  selects were documented as out of shell scope. A new test extracts every `getElementById` / `#id`
  target from `web/tests/browser/` and fails on any uncovered one.
- **C2-04 → C4-03 re-assignment:** the `webclient-narrative-markup` delta moved from
  `webclient-vue-08-wire-bridge-contracts` to `webclient-vue-10-wire-views-browser`, because the
  stock plugins it stops naming stay in the legacy load path until C4's atomic flip; the C4 change's
  artifacts were revised in the same pass (new `webclient-narrative-markup` delta spec, task 2.4,
  D1/D2). The C4-01 `rename_to` word order was also aligned with the C4 delta + roadmap.

See the audit's §6 revision log (A1.1) for the authoritative record.
