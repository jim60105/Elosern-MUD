## Context

Quest completion converges on `fulfill_record_for()`, but the resulting record reaches storage
through three different write paths in `world/quests/transitions.py`, each with its own transaction
ownership. Settlement must be atomic with the completion, so it has to ride all three.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §6.

## Goals / Non-Goals

**Goals:**

- A quest is never observed complete-but-unpaid or paid-but-incomplete.
- One exactly-once ledger shared by both settlement modes.
- The counter path's behavior is unchanged.

**Non-Goals:**

- No new economy primitive — wallet and inventory writes reuse the existing planners.
- No merit for private commissions.
- No "return to the commissioner to claim" flow; `npc:` issuances are always `AUTO` for now, and the
  `settlement` field is already there if that changes.

## Decisions

### D1: Not the completion-observer seam

`register_quest_completion_observer`'s contract is explicit: observers "must defer side effects
through `transaction.on_commit`" and "an exception they raise is isolated and logged — a broken
observer can never change quest settlement". Both properties are exactly wrong for a payout: money
would move after commit, and a failure would vanish into a warning. Title nomination belongs on that
seam because scheduling a nomination is genuinely best-effort. Payment is not.

The observer seam stays untouched.

### D2: One pure planner, three commit mechanisms

The alternative — settlement logic inlined at each of the three write paths — would triple the
place where "which quests pay, and how much" is decided. Instead one pure function answers that,
and each path only knows how to commit a plan in its own transaction idiom: inside its own
`atomic()`, inside the caller's, or as `PendingEffect` values.

This mirrors how `acquire.py` already separates `compute_acquire_replacement` (pure) from the
callers that apply it.

### D3: An unresolvable issuance degrades silently, and the quest still completes

The generative pipeline can unregister a definition and its issuance while a player holds the quest.
Raising there would make an ordinary content edit able to break a player's arrival into a room.
Instead the quest completes, nothing is paid, and the read model shows no reward line. The record
still names its issuer key, so the situation is diagnosable.

### D4: The shared ledger, not a parallel one

Automatic settlement appends to `guild_reward_claims` rather than a second list. A single ledger is
what makes "exactly once per quest ID" true across both modes; two ledgers would let a quest be paid
once by each. The attribute name mentions the guild for historical reasons only, and renaming it is
deliberately out of scope — the rename would touch every reward test for no behavioral gain.

## Risks / Trade-offs

- **`apply_quest_log_delta`'s caller contract widens** → Callers must now also snapshot wallet,
  inventory, and claims. Enumerated and updated in this change; the function's docstring states the
  extended contract, and the rollback test covers the inventory-driven path.
- **`PendingEffect` ordering with the action's own economy effects** → Settlement effects are keyed
  per surface like the existing quest-log and instance-pin effects, so the resolver's existing
  per-surface commit ordering applies. A combat-completion test pins the behavior.
- **A ledger named for the guild now records private settlements** → Cosmetic. Renaming is out of
  scope and noted; the docstring states the widened meaning.
- **Detecting "just reached COMPLETED" at three sites** → All three already compute the new record
  list, so the transition is a diff between old and new entries at the write boundary — the same
  diff `_schedule_transition_events` already computes. Reuse that comparison rather than adding a
  second notion of "just completed".
