## 1. Public-contract bridge

- [x] 1.1 Implement the browser-bridge shims: `window.Elosern.Protocol` and `.KeyboardRouter` = the imported UMD modules; `window.Elosern.narrativeInput` = the store's single narrative/choice-point append path; `window.Elosern.actions.submit` = the single action-dispatch entry
- [x] 1.2 Route document key events through the KeyboardRouter, claimed exactly when consumed (unconsumed keys fall through to the text path)
- [x] 1.3 Add a browser check that the façades resolve and route through the store/bridge dispatch path (live transport is C3's) with no duplicated append or action path

## 2. Apply the frozen contract deltas (per A1's list)

- [x] 2.1 Apply A1's frozen `MODIFIED`/`RENAMED` deltas to the façade-referencing `webclient-*` capabilities (the audit's list), editing each requirement to preserve the façade/keyboard contract
- [x] 2.2 Re-point the affected capabilities' traceability tests to the bridge (so each re-expressed requirement has a passing test at this change's archive)
- [x] 2.3 Confirm the applied delta set matches A1's frozen list and surfaces any omission

## 3. Gate

- [x] 3.1 The existing façade + keyboard Playwright/Node contracts stay green through the bridge; `openspec validate` for every touched capability passes `--strict`

## 4. Traceability (archive gate)

- [ ] 4.1 Author/apply A1's frozen delta specs only from the committed `docs/development/webclient-vue-frozen-contract-audit.md` (only the entries whose `applying_change` is this change), re-point every re-expressed requirement's traceability test to the bridge, add `@covers_requirement`-annotated Python tests where a new main requirement is introduced, then run `uv run --locked python -m tools.spec_traceability check` and the `verify --evidence` flow so every touched capability's gate is green at this change's archive
