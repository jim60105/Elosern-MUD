# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Capacity read model and status cutover

- [ ] 1.1 Implement build_travel_status and capacity_by_stage using detached canonical traversal/prediction, exact status6 fields and Python/JS validators. Extend existing status tests and add world/rules/tests/test_travel_capacity.py with independent sequential assertions, no-create snapshots, possession, flight and refusal; register one evennia shard. Update protocol/status documentation. Acceptance: focused Evennia capacity/status tests and mirrored Node status tests exit0; current terrain capacity performs no neighbour discovery or game writes.

## 2. Preference contract

- [ ] 2.1 Extend preferences.js, layout_store.js exact wrapper validation, facade methods and travel projection. Add tests/travel/preferences.test.js for defaults, invalid values, reload and walking setter rejection; update existing view-settings documentation. Acceptance: pnpm test -- web/webclient-app/tests/travel/preferences.test.js exits0; reload restores standard/true defaults or the valid chosen pair.

## 3. Leg surface and actions

- [ ] 3.1 Implement leg-model.js/LegPanel.vue and mount it in AppClient, preserving Stop/aim behavior; migrate and delete TravelWalkControls. Wire real guarded look and existing sleep card through openTravelCamp; do not add camping rules. Add tests/travel/leg.test.js for every intent state, independent capacity ticks, disabled actions and non-colour stage cues; update controls HelpOverlay. Acceptance: pnpm test -- web/webclient-app/tests/travel/leg.test.js exits0; absent plan disables Depart and a look sends exactly explore.look {room:true}.

## 4. Accessible production evidence

- [ ] 4.1 Add capacity/blocked/night-advisory states to production stories using protocol fixtures, and TravelLegTests.test_gauge_preferences_and_actions to managed travel browser tests with exact shard ownership. Run the focused method at both acceptance sizes and record text minimum/focus/radio/switch checks plus screenshots. Acceptance: focused managed TravelLegTests method passes; controls are keyboard reachable, text is>=16px*scale and walking preferences are disabled.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
