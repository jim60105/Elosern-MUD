# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Guarded route execution

- [ ] 1.1 Implement departedPlan route state and departTravel using the existing queue, enable real Depart actions and extend activateExit with exact optional walk context through common admission. Add tests/travel/route-walking.test.js for inclusive stop_index, changed exit refs, every flag/combination, both commit orders, dwell, preference freeze, late results and short-stop replan. Update synchronization and control docs. Acceptance: pnpm test -- web/webclient-app/tests/travel/route-walking.test.js exits0; injected hostile_in_sight prevents the next send even when dwell has already elapsed.

## 2. Shared observation integration

- [ ] 2.1 Integrate travel_events with the prerequisite interrupt collector as specified, preserving actor scoping, Deferred success and all other result-data keys. Extend existing travel-event/interrupt tests for one capture, nested foreign actor, rollback and successful simultaneous event/flag publication; update protocol composition documentation. Acceptance: focused Evennia travel-event/interrupt suites exit0; one committed step yields both its structured log event and interrupt data, rollback yields neither.

## 3. Landmark dialog and focus

- [ ] 3.1 Implement LandmarkCard with ArtworkPreview and existing focus trap; wire committed event-ID state and choices priority in AppClient/store, add tests/travel/landmark.test.js for art/disclosure, repeated arrivals, sleep priority, dismissal and epoch retirement. Add LandmarkArrival production story. Acceptance: pnpm test -- web/webclient-app/tests/travel/landmark.test.js exits0; Continue, Enter and Escape close once and restore map focus without restarting a walk. Require exact canonical arrival_node binding plus epoch before opening; add delayed notice after a later move and higher-priority-card dismissal after departure, both of which discard the old arrival.

## 4. Complete production acceptance

- [ ] 4.1 Add TravelRouteTests.test_hostile_interrupt and test_landmark_focus plus exact .github/browser-shards.json ownership; run these focused methods and the earlier gate/keyboard/viewports/repaint methods after all slices. Build production Storybook/showcase, capture all seven states at1451x790/2560x1440 and record human review against the approved reference. Update AGENTS.md final travel behavior and traceability mapping. Also implement/register TravelRouteTests.test_all_interrupt_flags with a table of all seven flags and a combined result. Acceptance: all named focused managed methods and pnpm run build-storybook && pnpm run showcase-coverage pass; every repaint sample is<=50ms, camera-only repaint count is0 and no prototype rule module enters production imports.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
