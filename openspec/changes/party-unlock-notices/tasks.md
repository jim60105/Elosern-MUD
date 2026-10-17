# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Structured notices (2h)

- [ ] 1.1 Introduce `UnlockNotice`, make both practice entry points fill an optional notice sink, render the commander/companion line forms, and emit `practice_unlock` scheduled events from `_practice_settlement`; verify existing unlock-line tests still see the commander line, a companion learner yields 「艾拉 學會了 群體治癒」, and a rolled-back advance returns no unlock event.

## 2. Session unread store (1.5h)

- [ ] 2.1 Add `world/rules/unlock_notices.py` (`deliver_unlocks`, `record_unlocks`, `mark_unlocks_seen`, `unlock_flags`) and the copied `PresentationContext.unlocks` snapshot; verify in `world/rules/tests/test_unlock_notices.py` marks on every account session, clear keeps the recent set, a new session has no marks, possession keeps marks, and an attribute snapshot proves nothing persistent was written.

## 3. Delivery owners (2h)

- [ ] 3.1 Call `deliver_unlocks` after commit from `commands/action.py`, `skill_use_actions.py`, field item use (command and adapter), `rounds._deliver_after_commit`, and the skip command/adapter paths (rendering `practice_unlock` events in the summary); verify one line per unlock per path and no duplicate lines in combat.

## 4. Integration (1h)

- [ ] 4.1 Register the new module in one shard, annotate canonical IDs for the modified `skill-lineage-panel` requirement and the added `party-unlock-notices` requirements, run the focused labels, the observability lint if logging changed, the shard contract, `uv run --locked python -m tools.contract_gate` and `openspec validate party-unlock-notices --strict`.
