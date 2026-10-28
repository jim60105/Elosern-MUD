# Tasks

## 1. Closed implementation units

- [x] 1.1 Implement the write-pause and stale-preview admission checks on every mutation route with session/token/fingerprint validation and no turn or ownership state; test that each route is rejected while paused or stale and admitted otherwise, and document the operator's no-simultaneous-editing assumption.
- [x] 1.2 Implement directory event coalescing, committed-fingerprint reconciliation and complete candidate preview adoption; exercise two service saves with delayed notifications preserving history, then actual external create/replace/rename/delete adopted automatically with history cleared, malformed/corrected sources and the no-prior-preview state.
- [x] 1.3 Implement draft-held adoption (banner naming the document and discarded draft/history, explicit 載入新版) and stale-to-current automatic recovery; test that a draft submitted against an old snapshot is rejected by the fingerprint guard and that no external file is ever rewritten from memory.
- [x] 1.4 Implement reconnect/restart session invalidation and stable-ID view/selection preservation; test old tab rejection, disconnected stale inspection, reread-then-write after restart and no command replay.
- [x] 1.5 Register focused browser/shard/traceability evidence, document file-following/recovery states and run service/real-file/browser and contract gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
