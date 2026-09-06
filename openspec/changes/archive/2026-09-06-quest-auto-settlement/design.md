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

### D5: Reward items complete other ACQUIRE objectives (chain folded into the plan)

`turn_in_quest` applies the ACQUIRE replacement of its reward items, so excluding the same items
when they are paid automatically would make quest progress depend on the settlement mode rather
than on the acquisition itself. `plan_auto_settlement_chain` therefore feeds every paid item to
the ACQUIRE runtime against the VIRTUAL post-transition record set (the package-private
`_compute_acquire_replacement_for` variant — no stale store read), and chain completions join the
same plan. The loop terminates because every iteration either pays a new quest ID (claim
identities are unique within one plan) or stops. On the pending-effects path the whole chain is
computed at planning time and folded into the quest-log and pin effects, so the resolver writes
the final record state exactly once and never applies a replacement computed against pre-action
state.

### D6: The counter claim appends before the nested ACQUIRE delta

`turn_in_quest`'s writer appends its own claim BEFORE invoking the ACQUIRE quest-log delta. A
counter reward whose items complete an AUTO quest settles inside that nested delta; appending the
counter claim afterwards (the pre-transaction list) would erase the nested settlement's claim and
let the quest be paid again later. The fix is a two-line reorder; the `first_claim` epithet
decision stays precomputed from the pre-append list.

### Retired: the "full inventory" reading of the rollback scenario

`plan_inventory_delta` has no inventory-capacity concept — additions are always appendable. The
only settlement failures are genuine write failures, and those roll the completion back together
with the payout exactly as the delta spec requires. No capacity rule is introduced here.

## Risks / Trade-offs

- **`apply_quest_log_delta`'s caller contract widens** → Callers must now also snapshot wallet,
  inventory, and claims. Enumerated and updated in this change; the function's docstring states the
  extended contract, and the rollback test covers the inventory-driven path.
- **`PendingEffect` ordering with the action's own economy effects** → Settlement effects are keyed
  per surface like the existing quest-log and instance-pin effects, so the resolver's existing
  per-surface commit ordering applies. A combat-completion test pins the behavior.
  Implementation note: the settlement rides one `PendingEffect` declaring the union of the wallet,
  inventory, and reward-claim surfaces (the resolver aggregates per-entity surfaces anyway), and
  its apply re-checks claim eligibility before writing, so all three surfaces land together or the
  commit fails and the action rolls back.
- **A ledger named for the guild now records private settlements** → Cosmetic. Renaming is out of
  scope and noted; the docstring states the widened meaning.
- **Detecting "just reached COMPLETED" at three sites** → All three already compute the new record
  list, so the transition is a diff between old and new entries at the write boundary — the same
  diff `_schedule_transition_events` already computes. Reuse that comparison rather than adding a
  second notion of "just completed".
- **Path-test fidelity** → The replacement-path test drives `apply_quest_log_replacement` directly
  — the same writer the REACH/ESCORT observation path calls — because the room-match and
  companion-presence machinery above it is change-agnostic and already covered by the existing
  room-observation tests. The delta and pending-effects tests likewise drive their writers, the
  latter through the real `ActionResolver` combat pipeline.
