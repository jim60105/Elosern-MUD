# Proposal: quest-auto-settlement

## Why

A private commission settles when the errand is done — the parcel reaches its recipient, the clue
leads to the place — not when the player walks back to a counter. `Settlement.AUTO` names that mode
but nothing executes it: today the only payout path is `turn_in_quest`, which requires a local
`GuildStaff`, a guild registration, and a branch offer.

The obvious hook is wrong. `register_quest_completion_observer` is documented as a scheduling seam:
observers must defer through `transaction.on_commit`, and an exception one raises is isolated and
logged so that "a broken observer can never change quest settlement". Paying a reward there would
pay after commit and swallow failures silently. Settlement has to be atomic with the completion that
earned it.

## What Changes

- New pure planner `plan_auto_settlement(actor, completed_records)`: for each record that just
  reached `COMPLETED` under an issuance whose settlement is `AUTO` and whose quest ID is not already
  claimed, compute the wallet delta, the inventory additions, and the claim append. It performs no
  write and reads no world clock.
- All three quest-log write paths commit the plan inside the transaction that writes the completing
  record:
  - `apply_quest_log_replacement` — inside its existing `transaction.atomic()`
  - `apply_quest_log_delta` — inside the caller's transaction
  - `pending_effects_for_transition` — as additional `PendingEffect` values so `ActionResolver`
    commits them with the originating action
- Automatic settlement appends to the same `guild_reward_claims` ledger the counter path uses, so
  the two settlement modes share one de-duplication record and a quest can never be paid twice.
- A record completing under a `COUNTER` issuance is untouched: it stays claimable at the counter
  exactly as today.
- A record whose issuance can no longer be resolved settles nothing and does not fail the
  transition — the quest still completes, and the read model reports no reward.

## Capabilities

### New Capabilities

- `quest-auto-settlement`: the automatic settlement contract — the pure planner, the all-three-paths
  atomicity rule, the shared claim ledger, the untouched counter path, and the degradation rules for
  an unresolvable issuance and a failed payout.

### Modified Capabilities

- `quest-reward-settlement`: the claim ledger is no longer written only by the counter turn-in; it
  gains automatic settlement as a second writer under the same exactly-once-per-quest-ID rule.

## Impact

- New module `world/quests/settlement.py` (the planner) and edits to `world/quests/transitions.py`
  (all three write paths).
- `world/rules/guild.py`: the claim parse/append helpers become shared rather than turn-in-private;
  no change to `turn_in_quest`'s own behavior.
- Reuses the existing `plan_inventory_delta` and wallet writers; introduces no new economy primitive.
- Focused tests across the three write paths plus an integration test that a DEFEAT completion in
  combat settles atomically with the action.
