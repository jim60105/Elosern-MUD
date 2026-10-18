# Design: Party-wide rest and movement time settlement

## Context

See proposal.md. Observed: `advance_skip(actor, seconds, practice_skill=...)` calls `get_world_clock().advance(seconds, AdvanceSource.SKIP, [actor])`; `charge_movement(traversing_object, cost_key)` calls `advance(cost, AdvanceSource.COMMAND, [traversing_object])` from `typeclasses/exits.py::after_successful_movement`, which runs after the traverser relocated and **before** `follow_companions` moves the co-located companions. `settle_movement` snapshots a clock registry for the traverser only (`build_advance_snapshot_registry(..., (traversing_object,))`) and snapshots companions only for location compensation. `WorldClock.advance` settles exactly the entities it is given and restores its registry per entity on failure.

## Goals / Non-Goals

**Goals:** widen exactly the two named advances; keep every other `advance()` caller byte-identical; keep all-or-nothing rollback for every settled member.

**Non-Goals:** field cast and item use scope (owned by `party-field-settlement-scope`); booking semantics (owned by `party-practice-booking`); changing how `sleep` computes its duration; any per-entity "last settled" bookkeeping.

## Decisions

- **SKIP scope** = `present_party_scope(actor)`. `advance_skip` passes that tuple. The practice clause still books only the caller in this slice.
- **Movement scope** = the traverser plus the follower set `follow_companions` will move (from `party-follow-under-possession`): effective companions, and for a possessed traverser the commander's body, co-located with the **source** room (the same `_companion_co_located` predicate the follow and the movement snapshot already use, including wilderness registration). `charge_movement` gains a required `source_location` keyword (and the wilderness source coordinates) supplied by `after_successful_movement`. Alternative: settle after the follow step; rejected because the follow is exception-isolated and must stay after the raise-capable charge.
- **Possessed traversal** settles the whole travelling party. This follows the user's 2026-10-18 amendment of the possession non-goal: the whole party follows a possessed traversal, so party members are co-located by construction.
- **Rollback coverage.** `settle_movement` builds the registry with the same travelling scope, and `_restore_advance_registry` receives the same tuple; `advance_skip`'s failure path keeps restoring the caller's booking while the clock restores every member's surfaces from its own snapshot.
- **Observability.** Each widened call site's existing `clock_advance` info event (emitted by the clock) gains `scope` (member count) in its context; no new event name.

## Risks / Trade-offs

- [A companion left behind by a failed follow was still settled for the step] → It was co-located before the step and time passed for it too; the follow failure notice already reports it.
- [Larger snapshot cost per step] → Bounded by the party roster (at most 16 effective rows).

## Migration Plan

Pre-release clean cutover; no stored-data migration. Revert the implementation commit to roll back.

## Verification and documentation ownership

EvenniaTest with synthetic companions: rest regenerates a co-located companion and skips one in another room; buff expiry on the companion; movement settles followers and not a companion elsewhere; possessed traversal settles the traverser, the owner body and the companions; church/GM/defeat call sites unchanged (assert their entity tuples); injected failure after the clock write restores every member. No player command syntax changes, so command docs are untouched. Run the observability lint, the focused tests, the shard contract and `tools.contract_gate`.
