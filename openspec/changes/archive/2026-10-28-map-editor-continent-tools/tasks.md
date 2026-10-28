# Tasks

## 1. Closed implementation units

- [x] 1.1 Implement all mainland/waterway/forest/terrain/ridge/pass/ford/site geometry tools plus numeric add/remove/move alternatives; test one drag/one document, labelled units and core-derived terrain changes.
- [x] 1.2 Implement unbuilt-location creation/property/search and local-map navigation from settlement-owned refs; test no fabricated rooms and separate location/map commands.
- [x] 1.3 Implement district/landmark fields and settlement-owned footprint cell controls/binding inputs; test reference guards, reachability WIP and no multi-document writes.
- [x] 1.4 Implement derived-output stale/revision labels and non-editable border output; test no automatic partition rebuild and service rejection of tool commands while paused or stale (rejection while generating is integrated through the same admission by map-editor-partition-jobs task 1.2, which introduces the generation state).
- [x] 1.5 Add the continent rows to the design-fidelity review, register focused browser/component/service evidence, update docs and run focused and contract gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
