# Tasks

## 1. Closed implementation units

- [ ] 1.1 Implement admission (session, snapshot revision, write pause), document presence-or-hash guards and the first layout handler; test absent first layout, stale create/remove rejection and no world-data side effects; document command envelopes.
- [ ] 1.2 Implement serialized internal create/replace/remove effects, flushed temporary publication, no-overwrite create and guarded unlink with injectable failures; test each pre-publication baseline, acknowledged presence/content and uncertain-durability pause without retries.
- [ ] 1.3 Implement draft/confirm/cancel, persistence states and history inverses through the same writer; test create to undo-absence to redo, remove to undo-restore, retained comments, stale/invalid inverses preserving disk/history and fresh external-reference checks for every object-removing inverse.
- [ ] 1.4 Test same-owner multi-selection and reject cross-owner mutation, register evidence/ownership, document refresh/history limitations and run focused writer/history/browser and contract checks.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
