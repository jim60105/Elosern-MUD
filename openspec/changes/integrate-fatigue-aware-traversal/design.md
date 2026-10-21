# Design

## Context

See proposal.md for scope and dependency ordering. Source research located world/rules/movement.py::charge_movement, world/rules/party.py::follow_scope, typeclasses/exits.py traversal preflight, world/rules/movement_settlement.py::_snapshot_movement_state/_compensate, world/rules/clock.py::build_advance_snapshot_registry. Existing runtime dense/grid and pooled wilderness identities must survive this pre-release cutover.

## Goals / Non-Goals

Implement the owning delta with deterministic single-writer boundaries and bounded edge-local work. Lore stays frozen/read-only, world/maps owns persistent room lifecycle, deterministic rules own eligibility/resources/time, and WorldClock remains the clock writer. No AI module writes geometry or movement outcomes. Non-goals are listed in proposal.md.

## Decisions

The external fatigue proposal slug/API does not yet exist. The external dependency token is a scheduling block until the later companion pass supplies its actual change ID and prediction/settlement API; this change defines no rates, thresholds, recovery, storage, sleep/wait mechanics or indivisible-action physiology.

Prefer stable sparse authored identity and explicit physical segments to dense meter ASCII or uniform coordinate multiplication. Distances use local-to-world anchor transforms; z remains logical. Snapshot intended source-present travellers once and reuse that scope before relocation, cost, followers and compensation. Refusals occur before writes. Runtime activations depend on projection, cost and external physiology integration; declarations/support can land earlier without exposing a mixed-unit runtime.

## Risks / Trade-offs

- Shared bootstrap/exit consumers can retain old assumptions. Mitigation: enumerate consumers in tasks and execute end-to-end owning tests before handoff.
- Persistent coordinates participate in identity. Mitigation: deterministic in-place synchronization, preflight conflict rejection, durable/cache rollback and repeat-start idempotence, never delete/recreate occupied rooms.
- The companion fatigue batch is now implemented. Mitigation: the dependency is bound to `settle-terminal-combat-fatigue`, which transitively requires every fatigue component, so traversal integrates against the complete physiology contract rather than a partial one.

## Migration Plan

No database schema/data migration or compatibility layer. luna uses `feat/integrate-fatigue-aware-traversal` in `.worktrees/integrate-fatigue-aware-traversal`. Apply prerequisite changes first; synchronization converges owned declarations in place before accepting play. If synchronization fails, restore the whole transaction/cache snapshot and keep the prior authoritative runtime, rather than partially activating coordinates.
