# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Current-only query owner

- [ ] 1.1 Implement token state and150ms debounce/latest-intent flush in the travel store, sharing dispatchAction without changing single-flight policy. Add tests/travel/planning.test.js for all result orders, token-input invalidations, dispatcher/domain refusals and response-only success; document exact request lifecycle in synchronization guidance. Acceptance: pnpm test -- web/webclient-app/tests/travel/planning.test.js exits0; no hover query sends at149ms and superseded errors cannot replace a newer plan.

## 2. Destination input

- [ ] 2.1 Extend use-travel-input and TravelMap event wiring with lock/cursor/Escape priorities and guarded revealed-cell membership; add tests/travel/destinations.test.js for neighbour gates, opaque directions, unknown/party clicks and keyboard cursor parity. Update HelpOverlay controls. Acceptance: pnpm test -- web/webclient-app/tests/travel/destinations.test.js exits0; Shift-arrow plus Enter locks the same synthetic cell as a pointer click without submitting explore.move.

## 3. Preview map and leg

- [ ] 3.1 Extend shared travel glyphs, TravelMap route overlay and leg-model projection using the exact planner schema. Add tests/travel/preview.test.js with independently known stop/night indices and empty-plan behavior; add RoutePreview production story and update existing developer UI guidance. Acceptance: pnpm test -- web/webclient-app/tests/travel/preview.test.js exits0; paint-call count remains unchanged when only the plan overlay changes. Exercise a canonical forced_sleep terminal step using LegPanel's shared severe-style-plus-crescent mapping, preserving the original stage and including its admitted count/duration.

## 4. Preview browser evidence

- [ ] 4.1 Add TravelPlanningTests.test_destination_preview_keyboard_and_pointer to managed travel browser tests, register exact method ownership and capture RoutePreview at both acceptance sizes. Include pending/error snapshots and accessible intent text. Also implement/register TravelPlanningTests.test_destination_query_supersession with delayed and superseded production results. Acceptance: focused TravelPlanningTests method passes; current planner errors clear map preview, and no route execution is claimed before route-ui.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
