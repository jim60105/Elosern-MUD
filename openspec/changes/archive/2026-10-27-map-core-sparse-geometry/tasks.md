# Tasks

## 1. Closed implementation units

- [x] 1.1 Extract sparse nodes/roads, validation and shortest paths with the existing game adapter as the real consumer; exercise directed routes and malformed graph rejection, and document the API.
- [x] 1.2 Extract explicit-input cell/local/world transforms and deterministic terrain; exercise two independent worlds and numeric unit cases, and document units/cache ownership.
- [x] 1.3 Migrate all pure algorithm imports, keep only XYMap/contrib/persistent adaptation game-side, declare locked local dependencies, and exercise existing movement and bootstrap consumers.
- [x] 1.4 Register discoverable top-level contract evidence and focused CI ownership for package tests; remove obsolete definitions/source-layout assertions and run the focused checks and contract gate.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
