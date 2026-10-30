# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Projection and adapter

- [ ] 1.1 Implement applyTravel and decodeTravelGrid with the exact shapes above; export store.view.travel via stores/elosern.js and publishView. Add tests/travel/layout.test.js and grid.test.js for committed identity, south-to-north positions, gateway identities, sparse unknowns and no guessed facts. Update existing developer synchronization guidance for travel projection. Acceptance: pnpm test -- web/webclient-app/tests/travel/layout.test.js web/webclient-app/tests/travel/grid.test.js exits 0; an input without explicit terrain yields null terrain.

## 2. Refresh and shell

- [ ] 2.1 Implement use-travel-map, AppClient slot branches, HudFrame travel hook and MapDrawer allowed-tab filtering; keep ordinary controls mounted until later slices replace them. Extend tests/world/map_drawer.test.js and tests/travel/refresh.test.js for both result/body orders, close/epoch changes and unavailable maps. Update webclient-app/AGENTS.md drawer-only refresh wording. Acceptance: pnpm test -- web/webclient-app/tests/travel/refresh.test.js web/webclient-app/tests/world/map_drawer.test.js exits 0; hidden area shortcut sends no request. Distinguish normal refreshing (suspend, keep Stop) from unavailable/invalid/retired (cancel). Wire accepted external full snapshot and explicit-sync recovery to one fresh area request even with unchanged position/time, excluding self-triggered map results; add a two-step-refresh and same-position recovery case.

## 3. Sleep facts and medallions

- [ ] 3.1 Implement the schema5 asleep field in status presenter, status-query model/builder, registered Python and mirrored JS status validators, constants and frozen protocol fixtures. Add PartyMedallions and tests/travel/medallions.test.js; extend presentation/tests/test_status_panel.py and possession tests. Update docs/development/webclient-synchronization.md schema table. Acceptance: pnpm test -- web/webclient-app/tests/travel/medallions.test.js exits 0; focused Evennia status tests accept only schema5 and prove reads write nothing.

## 4. Production evidence

- [ ] 4.1 Add stories/World/WildernessTravel.stories.js with production layout/adapter fixtures and Morning/MotionOff states. Add web/tests/browser/test_wilderness_travel.py::TravelLayoutTests.test_settlement_gate_layout and register it in .github/browser-shards.json. Capture both acceptance viewports, preserving existing dialogue/combat layouts and visible focus. Record requirement-to-test mapping with generated IDs. Also implement/register TravelLayoutTests.test_refresh_adoption and test_medallion_subjects with result/body-currentness and body-keyed reserve/asleep assertions. Acceptance: pnpm run build-storybook && pnpm run showcase-coverage exits 0; focused managed browser method passes and produces 1451x790 and 2560x1440 screenshots.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
