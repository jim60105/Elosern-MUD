# Tasks

## 1. Closed implementation units

- [ ] 1.1 Implement authoritative state transitions, draft resolution and flush-before-handoff with tests for admitted-save drain/failure and every mutation route denied externally; document external cooperation assumptions.
- [ ] 1.2 Implement directory event coalescing and complete candidate preview adoption; exercise actual create/replace/rename/delete plus malformed/corrected sources and no-prior-preview state.
- [ ] 1.3 Implement explicit stop-confirmed return and manual unexpected-write reload; test semantic repair versus structural rejection and prove no old-memory rewrite or pending-command replay.
- [ ] 1.4 Implement reconnect/restart generation invalidation and stable-ID view/selection preservation; test old tab rejection, disconnected stale inspection and explicit resume after fresh load.
- [ ] 1.5 Register focused browser/shard/traceability evidence, document failure/recovery states and run service/real-file/browser and contract gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
