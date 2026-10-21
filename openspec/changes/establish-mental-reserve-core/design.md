# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

### Policy and state owner

Add `world/rules/fatigue.py` and one read-only authored policy source under `world/rules/rulebook/`; validate through the existing schema loader. Persist `mental_reserve_units` and `sleep_posture` on owning entities through the deterministic fatigue writer. `typeclasses/entities.py::LivingEntity.at_object_creation` explicitly initializes full/awake; authored construction/synchronization calls that initializer only for absent construction state, never as a malformed-data repair or repeated refill. No migration or read-time default materialization is permitted.

### Consumer API for metric traversal

The proposed public functions in `world/rules/fatigue.py` are `read_fatigue_state(entity) -> FatigueState`, `fatigue_stage(state)`, `foot_speed_scale(state)`, `predict_interval(state, activity, seconds, policy) -> FatiguePrediction`, `next_fatigue_boundary(state, activity) -> FatigueBoundary | None`, and `settle_fatigue_intervals(intervals, *, context)`. These names are newly proposed interfaces, not claims about baseline symbols. `FatigueState` carries validated integer `reserve_units` and closed `posture`; predictions carry start/end state, next exact threshold/depletion/wake offset and transition reason. Activities are ordinary awake, foot travel, awake combat, actual sleep. Policy explicitly selects interruptible, indivisible completion or terminal combat; combat natural release is forbidden until terminal completion. Settlement receives entity identity, immutable start state, sampled activity intervals and exact integer elapsed seconds, validates all members before writes and rejects a stale start state rather than applying a prediction twice. Owning clock/movement/session transactions remain responsible for request idempotency.

Boundary offsets use exact rational arithmetic where the reserve is not divisible by its rate. Interactive clock advances use the first integer second at or after a boundary. Movement integrates rational distance/time across each terrain/member-threshold event, then applies its existing declared final whole-second rounding once. It asks `predict_interval` again for that accepted integer duration before admission and commits that identical duration and state. No fractional percentage is discarded: one stored unit equals 1/3600 percentage point, and every accepted integer second has an exact integer unit delta. There is no second floating-point reserve or independent movement remainder to synchronize. Zero reached exactly at the accepted destination is allowed and latches forced sleep there; depletion before the next destination refuses before any mutation. The caller owns geometry and slowest-party-speed selection, not this policy module. This API supplies `integrate-fatigue-aware-traversal` without inventing another balance table.

### Transactions and independent verification

Pure arithmetic can land and be tested without changing current world-time callers. This component supplies snapshot field declarations for later clock/movement/terminal consumers; projection and live call-site cutovers belong to the dependent changes. Failure tests prove the core multi-member writer restores cache and persistent state. Document the exact units/rates/API in the owning rules module and existing command reference when exposed by later components.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/establish-mental-reserve-core` in `.worktrees/establish-mental-reserve-core` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

## Recorded assumptions

A boundary tie publishes every due fact from one committed elapsed interval and recomputes handoff choices afterwards. Integer clock seconds use the first accepted whole-second boundary, with exact reserve units retained. Existing `rest` syntax remains a waiting transport, with no independent quiet-rest action or rate. These details resolve minor orchestration choices without changing approved physiology. No material design question remains open.

## Cross-batch contract

Replace the literal `external:party-fatigue-and-sleep` token with `settle-terminal-combat-fatigue` during the later integration step. That final component transitively requires every component here, so the single replacement preserves a full-design scheduling barrier and supplies the earlier pure API without a dependency cycle. Existing seven changes are intentionally unmodified in this pass.

| Existing map change | Relationship to this batch | Shared surfaces / scheduling |
| --- | --- | --- |
| establish-continental-geography | transitively prerequisite through charge-distance-based-travel | lore geometry; no direct physiology write conflict |
| implement-sparse-settlement-graphs | independent declarations | no direct prerequisite; runtime activation waits for traversal |
| project-metric-local-maps | independent projection | no direct prerequisite; status/selection integration may share client registration |
| charge-distance-based-travel | direct prerequisite of settle-party-sleep-and-wait | serialize exits, movement and clock edits |
| integrate-fatigue-aware-traversal | direct prerequisites charge-distance-based-travel and settle-terminal-combat-fatigue after external-token integration | consumes core prediction API; serialize movement/clock surfaces after batch |
| rescale-wilderness-geography | downstream of integrate-fatigue-aware-traversal | no new reverse edge; existing prerequisites retained |
| activate-metric-settlements | downstream of integrate-fatigue-aware-traversal and wilderness rescaling | no new reverse edge; existing prerequisites retained |

