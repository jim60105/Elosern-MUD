# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

Keep fatigue arithmetic in its core module. Add proposed `sleep_handoff_candidates(account, commander, current_body)` and `confirm_sleep_handoff(...)` orchestration around `world/rules/possession.py::enter_possession`, `release_possession`, `_transfer_puppet`, `restore_possession_surfaces` and existing full handback compensation. Server confirmation receives exact candidate/session identity and the contextual unavailable-body transition identity; recompute every mutable gate under the owning serialized write boundary.

Relax combat/already-possessing gates only inside the validated sleep-driven context. An old companion to a new companion transfer cannot nest possession or leak a released binding if the second hop fails. Reuse the existing session retire/epoch reset and verified puppet checks for every hop, with compensation of locations/logout residuals, locks and cmdsets. Preserve other account characters' single-possession restriction. Candidate inspection, cancel and control transfer have zero game time and do not edit commander-owned combat draft state.

Deliver the contextual choice only after sleep-entry or accepted action/terminal commit. An unselected sleeper only produces status. Bind response admission to the authenticated account and current session even if the controlled body cannot act. Provide narrowly non-acting status, handoff and safe recovery controls on text and browser surfaces, without authorizing the sleeper to cast/move/use an item. No awake candidate gives explicit recovery waiting from the prior change; unsafe rooms keep existing refusal and valid engagement semantics. Existing `web/webclient/actions/exploration_actions.py` transition helpers and `web/webclient/presentation/ingress.py` handle client synchronization. Follow existing modal keyboard focus and stale epoch conventions, without new UI design.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/handoff-sleeping-party-control` in `.worktrees/handoff-sleeping-party-control` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

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

