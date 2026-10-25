# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Persistent narrative API and locking

Shared contract v2 uses stable host_key/source-aware topic IDs for both providers. Test equal local IDs in different package roles, dbid rematerialization, save/reload and phase-return completion; preserve receipt/byte budgets without a static membership check.

- [ ] 1.1 Implement pure reader, locked raw-read/merge writer, revision and cache compensation in dialogue_reading.py. Add world/narrative/tests/test_dialogue_reading.py for host/owner keys, same-topic duplicates, concurrent merge and rollback; document SQLite guarded-lock ownership.

## 2. Receipts completion and pure-chain delivery

- [ ] 2.1 Extend sole session writer with bounded receipt set and completion action validation; issue effect-free public-chain receipts, retain prior-topic receipts and reject stale/foreign/refusal/out-of-order acks. Add focused action/selection tests and record boundary logs.

## 3. Text parity and owner fan-out

- [ ] 3.1 Wire successful full attributed emission to completion, stop after failed chain node, and push saved reading to owner current watchers without crossing account characters or replacing another connection scene. Add text failure, two-connection possession and delayed A-after-B tests.

## 4. Unread projection and docs acceptance

- [ ] 4.1 Expose server unread/reading_revision and saved predecessor gates with no notification observation mutations yet. Update command docs for text completion and author docs for pure/qualified chain separation, register tests and run focused narrative/action/command tests and contract_gate.

