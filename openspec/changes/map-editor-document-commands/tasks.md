# Tasks

## 1. Closed implementation units

- [ ] 1.1 Implement explicit manual admission, generations/document fingerprint and one-document layout handler; test stale requests and no world-data side effects and document command envelopes.
- [ ] 1.2 Implement temporary-file flush/replace and serialized saves with injectable failures; test pre-replace intactness, replacement acknowledgement and uncertain-durability pause without retries.
- [ ] 1.3 Implement draft/confirm/cancel and persistence UI distinctions plus manual-segment undo/redo through the same path; test drag once, invalid drafts never written and history failure behavior.
- [ ] 1.4 Test same-owner multi-selection and reject cross-owner mutation, register evidence/ownership, document refresh/history limitations and run focused writer/history/browser and contract checks.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
