# Tasks

Read design.md contracts before starting each group. Paths without a web/ prefix are relative to web/webclient-app/ unless the design names a server module. Use only this slice's named symbols/files and their focused evidence/docs; do not change sub-project1 rule semantics, authored content, camping, other layouts or unrelated windows. Prerequisites are the exact depends-on lines in proposal.md; shared-code conflicts are integration ordering only. Preserve existing non-travel tests and use real protocol fixtures rather than prototype rules.

## 1. Event facts and committed producers

- [ ] 1.1 Implement world/rules/travel_events.py and the concrete movement/skip/look producer hooks above, preserving existing prose. Add world/rules/tests/test_travel_events.py with synthetic changes, repeats, positive/zero skips and rollback/failed look; register this new module in exactly one evennia shard. Update docs/development/webclient-synchronization.md event-source table. Acceptance: focused Evennia test_travel_events exits0; rollback produces no TravelLogFact and repeated unchanged views produce no entries.

## 2. Transport and schema

- [ ] 2.1 Implement coordinator.record_travel_events, PresentationContext field, presenter/push/registry and mirrored JS validation; extend existing publication and protocol fixtures without replacing data slots. Add presentation/tests/test_travel_log.py and matching Node schema tests, registering the server module in one shard. Document exact union and byte cap. Acceptance: focused server travel_log tests plus node --test web/static/webclient/js/tests/travel_log.test.js exit0; both validators reject extra kind-specific fields and stale batches cannot reappear for another puppet.

## 3. Log rendering and retention

- [ ] 3.1 Implement applyTravelLog and TravelLog.vue, replace only travel MessageWindow, append structured text once to the existing full log, and add tests/travel/log.test.js with replay/day/malformed-text/overflow/epoch assertions. Add production log story using schema-shaped synthetic events. Acceptance: pnpm test -- web/webclient-app/tests/travel/log.test.js exits0; repeated snapshot of one batch adds no entry or full-log line.

## 4. Cross-client evidence

- [ ] 4.1 Add TravelLogTests.test_committed_log_and_full_prose browser method and exact browser-shard ownership. Exercise a move, explicit look and failed move with real producers and verify safe accessible log/full-log availability. Record canonical requirement mappings. Acceptance: focused managed TravelLogTests.test_committed_log_and_full_prose passes; a refused step appears once and per-step prose appears in the full log only.

## Integration handoff

- [ ] 5.1 After all owned groups are complete, run the focused commands named above, the existing local contract gate and strict OpenSpec validation for this change. Record exercised command output, requirement-to-test mapping and any visual review separately; expected result is no uncovered requirement, schema mismatch, manifest ownership error or validation warning. Do not run broad CI/browser suites locally. Do not implement a dependent slice, sync or archive from this task list.
