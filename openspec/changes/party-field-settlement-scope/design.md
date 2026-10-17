# Design: Party-wide field cast and item use settlement

## Context

See proposal.md. Observed: `settle_out_of_combat_cast` snapshots `_snapshot_settlement_state(request, clock)` for the actor and targets, then calls `clock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, (request.actor,))`; `world/rules/items/settlement.py` builds `build_advance_snapshot_registry(world_clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (actor,))` and restores `_restore_advance_registry(registry, (actor,))`. Both already restore all registry entries per entity.

## Goals / Non-Goals

**Goals:** widen both advances to `present_party_scope(actor)` with complete rollback.

**Non-Goals:** allowing a companion actor (later changes), combat paths, time costs, disguise or coercion scans.

## Decisions

- Compute the scope once before the outer transaction and pass the same tuple to the snapshot registry, the advance and the restore, so the three can never disagree. Alternative: compute inside the transaction; rejected because a member moving between snapshot and advance would leave an unsnapshotted settled entity.
- Targets that are also members are de-duplicated against the scope by identity inside the registry builder (it already keys by `id(obj)`).
- No new event; add `scope` to the existing clock-advance context.

## Risks / Trade-offs

- [Wider snapshot work per field action] → Bounded by party size; no per-quantum loop is added.

## Migration Plan

Pre-release; revert the implementation commit to roll back.

## Verification and documentation ownership

EvenniaTest: commander field heal with a present companion regenerates the companion and skips one elsewhere; a potion use settles both; injected failure after the advance restores both members and the tick; a rejected use or cast settles nobody. No command syntax changes. Observability lint, focused tests, shard contract, `tools.contract_gate`.
