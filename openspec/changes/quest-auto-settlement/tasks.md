# Tasks: quest-auto-settlement

## 1. Shared claim ledger

- [x] 1.1 Promote the reward-claim parse/append helpers in `world/rules/guild.py` to a shared seam
  both settlement modes call (`parse_reward_claims` is already public; add the append helper).
  `turn_in_quest`'s own behavior does not change.
- [x] 1.2 Confirm by test that the counter path refuses a quest ID already appended by automatic
  settlement, returning the existing already-claimed error rather than a new one.

## 2. Pure planner

- [x] 2.1 New `world/quests/settlement.py` with `plan_auto_settlement(actor, completed_records)`
  returning a frozen plan carrying the wallet delta, inventory additions, and claim identities.
- [x] 2.2 Contribution rules: include a record only when its issuance resolves, its settlement is
  `AUTO`, and its quest ID is absent from the claim ledger. A `COUNTER` issuance, an already-claimed
  ID, and an unresolvable issuance each contribute nothing, the last without raising.
- [x] 2.3 Rewards come from the resolved issuance's immutable `QuestReward`, never from a value on
  the record. No write, no clock read.

## 3. Commit on all three write paths

- [x] 3.1 `apply_quest_log_replacement`: detect records transitioning into `COMPLETED`, plan, and
  commit the plan inside the existing `transaction.atomic()`; extend the existing snapshot/restore
  to cover wallet, inventory, and claims so a settlement failure restores everything.
- [x] 3.2 `apply_quest_log_delta`: same detection and commit, performing no nested transaction — the
  caller owns the transaction and the snapshots, so extend the documented caller contract to say the
  caller must also snapshot wallet, inventory, and claims.
- [x] 3.3 `pending_effects_for_transition`: emit the settlement as additional `PendingEffect` values
  (wallet, inventory, claims) keyed so the resolver commits them with the quest-log effect.
- [x] 3.4 Reuse `plan_inventory_delta` and the existing wallet writer; introduce no new economy
  primitive.

## 4. Observability

- [x] 4.1 Emit the settlement boundary event with `char`, `quest`, and `issuer` context on each
  payout; emit nothing when the plan is empty.
- [x] 4.2 Register the new event in the observability catalog section of
  `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.

## 5. Tests

- [x] 5.1 Planner unit tests: automatic contribution, counter contribution empty, already-claimed
  empty, unresolvable issuance empty without raising, and the no-write assertion.
- [x] 5.2 Path tests, one per write path: REACH arrival (replacement), ACQUIRE inventory delta
  (delta), DEFEAT combat action (pending effects) — each asserting the record, wallet, inventory,
  and claim all land together.
- [x] 5.3 Rollback test: fault-inject during the settlement write and assert quest log, wallet,
  inventory, claims, and their in-process caches equal pre-transition values.
- [x] 5.4 Cross-mode tests: an automatically settled quest is refused at the counter; one automatic
  and one counter settlement both appear exactly once in the shared ledger.
- [x] 5.5 Isolation tests: an automatic settlement writes no merit and needs no host — assert a
  wilderness completion with no NPC present succeeds.
- [x] 5.6 Annotate with `covers_requirement` against the new `quest-auto-settlement` and modified
  `quest-reward-settlement` requirement IDs; update `.github/evennia-shards.json` for new
  integration modules.
  - The modified `quest-reward-settlement` requirement is annotated now. The
    `quest-auto-settlement::*` annotations are deliberately withheld until this change archives and
    syncs (the traceability tool rejects not-yet-canonical IDs — the same convention batches 1-4
    followed); the establishing tests and their mapping are documented in the
    `world/quests/tests/test_settlement.py` module docstring. `.github/evennia-shards.json` needs no
    edit: shard 4 owns the `world.quests` package label, and the ownership contract test passes.
- [x] 5.7 Run the observability lint plus the focused quest, transition, reward, and combat
  settlement test modules in the same batch.
