# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Store queue

- [ ] 1.1 Implement exact direction state/actions and timers in stores/elosern/travel.js, guarded activateExit calls and publishView projection. Add tests/travel/walking.test.js using fake timers for both completion orders, pooled room coordinates, foreign results, late commits, every cancellation and off motion. Update synchronization guidance for commit-qualified queue ownership. Acceptance: pnpm test -- web/webclient-app/tests/travel/walking.test.js exits0; no second send occurs at349ms or before the matching revision commits.

## 2. Inputs and working controls

- [ ] 2.1 Wire use-travel-input.js and TravelMap events to the store, reusing compass-model aims; add TravelWalkControls and remove only the travel branch of ExitCompass. Add tests/travel/input.test.js for400ms hold, persistent diagonal aim, Enter/Escape, focus exclusion and no double activation. Update existing HelpOverlay control reference for travel bindings. Acceptance: pnpm test -- web/webclient-app/tests/travel/input.test.js exits0; a short arrow release plus Enter sends exactly one existing explore.move payload.

## 3. Keyboard browser evidence

- [ ] 3.1 Add TravelWalkingTests.test_keyboard_only_step and test_held_walk_release to web/tests/browser/test_wilderness_travel.py and exact .github/browser-shards.json method ownership. Extend production stories with aimed/held states driven by a committed store harness, not a second movement model. Acceptance: focused managed TravelWalkingTests methods pass; release during dwell produces no next send and focus returns to map.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
