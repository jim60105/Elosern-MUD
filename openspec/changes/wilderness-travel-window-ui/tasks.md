# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Schema3 display facts

- [ ] 1.1 Extend area_map.py _wilderness_area and map_panels.py plus mirrored JS validators/constants with the exact display/landmark/count/threat fields above, after existing reveal filtering. Extend existing area-map/protocol tests for synthetic hidden/unknown/entity cases and byte limits; do not alter sight or reveal rules. Update protocol docs and frozen audit fixtures. Acceptance: focused existing area-map/protocol server and Node suites exit0; no private source key, unknown display fact or unsupported old schema passes either validator.

## 2. One decoder and real overlays

- [ ] 2.1 Extract the prerequisite decoder to lib/wilderness-grid.js and migrate both AreaMapView and TravelMap; delete the temporary node adapter and obsolete tests. Add tests/travel/window.test.js for run sums, origin axes, sparse nodes, unknown rejection, stale map and phase/radius passthrough; wire PlaceCard/chips from display facts. Acceptance: pnpm test -- web/webclient-app/tests/travel/window.test.js exits0; changing supplied radius/phase changes presentation without a client rule lookup. Preserve the base refreshing versus unavailable/invalid/retired lifecycle; cover normal queued continuation after refresh and one same-position sync recovery request without recursive map refresh.

## 3. Canonical event enrichment

- [ ] 3.1 Update travel_events sight/phase fact capture to canonical functions, remove current-view comparison and add synthetic before/after identity, interval-crossing and rolled-back skip tests in existing test_travel_events.py. Document log event completion and raw-identity privacy. Acceptance: focused Evennia travel-event tests exit0; prospective-to-materialized same observation emits no extra hostile notice and an unchanged read emits none.

## 4. Production phase evidence

- [ ] 4.1 Convert Morning/Dusk/Night/Woodland/MotionOff production stories to exact schema3 fixtures and add TravelWindowTests.test_live_memory_and_distant_cards to managed browser tests and its shard. Capture both viewports and repeat map repaint benchmark on the real41x41 decoder output. Acceptance: focused TravelWindowTests method and TravelMapTests.test_repaint_budget pass; screenshot review has no chips under protected controls and all repaint samples remain<=50ms.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
