## 1. Remove dead legacy code

- [x] 1.1 Confirm the retired `js/plugins/*` dock plugins, the goldenlayout plugin, and `elosern_ui.js` are no longer imported by the Vue client, `base.html`, or any test
- [x] 1.2 Delete those files and their dead CSS (`goldenlayout.css`, the legacy `elosern.css` view sections); keep the preserved `js/elosern/*` logic and `evennia.js`
- [x] 1.3 Rerun the Node gate and all suites to confirm nothing broke

## 2. Update guidance and docs

- [x] 2.1 Update `AGENTS.md` with the frontend commands, the Python-vs-npm split, and which JS gates (Node/Vitest/Storybook) apply
- [x] 2.2 Amend the engine design doc D13/webclient row and `webclient-ui-design.md`: "GoldenLayout shell" → "Vue SPA on the same Evennia extension points" (Telnet unchanged)
- [x] 2.3 Finalize `docs/` links: link the 設計稿, the component showcase, and the frontend developer/architecture guide (entries authored by A1/A2 but left unlinked)

## 3. Lock the final gate + verify

- [x] 3.1 Set the mandatory quality gate to its final form (all Vue gates + the offline-degradation browser regression + exact-root and aggregate ≥ 80% branch + Codecov); confirm no gate is weakened
- [x] 3.2 Final verification: `openspec validate --all --strict`, static traceability, full Evennia + managed browser + Node + Vitest + Storybook + top-level suites, and the aggregate Python branch coverage ≥ 80% with the exact-root check
