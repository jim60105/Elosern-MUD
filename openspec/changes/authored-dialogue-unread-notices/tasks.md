# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Durable first-open observation

Shared contract v2 observes stable host_key and first-seen topic ID for both sources. Test new-phase initial observation without popup, phase-return history and permitted-current-phase-only batches; no static registry gate.

- [x] 1.1 Implement narrative observe_availability with initialized/ever_open/announced fields under reading-server lock discipline; add world/narrative/tests/test_dialogue_unread.py for initial open, hidden/locked, refusal, completion and relock/variant cases. Document no presenter writes.

## 2. Claim and post-commit live delivery

- [x] 2.1 Implement persisted bounded batch claim and ephemeral owner/current-context pusher, suppress all snapshots/reconnect popups and handle no-watcher/failure without replay. Add two-connection, rollback and duplicate-refresh tests with facade boundary event dialogue_unlock_batch_claimed.

## 3. Deferred frontend notice and markers

- [ ] 3.1 Add lock/unread visual+accessible text, memory dedup and defer-until-choices toast using existing toasts.js without focus changes. Add synthetic component/store tests for concurrent completion suppression and stale host discard.

## 4. Focused full lifecycle acceptance

- [ ] 4.1 Add one browser method exercising unlock-during-scene, final return, single batch, relock/reload and persistent marker; register ownership and update dialogue help/author docs. Run focused narrative/Vitest/browser tests and contract_gate, keeping party skill notice behavior unchanged.

