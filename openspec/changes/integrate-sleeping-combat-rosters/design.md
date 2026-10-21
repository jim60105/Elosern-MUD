# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

Update the canonical roster opening/reconstruction, required-actor derivation and execution gates in `world/rules/combat_session/`. Existing companion knockout IDs remain HP-based persistence and are never reused as sleep flags. A sleeping living member remains targetable under `BattlefieldActionContext` and existing damage/recipient legality. Existing commander actor selection still changes no puppet; only the contextual handoff change owns puppet changes.

Record initial sleep posture with validated session participant identities and explicit posture transitions at completed-round boundaries in `world/rules/combat_session/records.py`. This is activity evidence for terminal accounting, not per-round reserve mutation. It must survive draft/reconnect/rebuild and join `snapshot.py` restoration. Synthetic tests may inject an explicit posture change to prove future effect compatibility, but no gameplay waking skill/item is authored.

Propagate truthful unable-to-act facts through the existing monster observation/legal-candidate boundary without excluding sleepers from target plans or predicting an automatic win. Show explicit sleeping/action-unavailable text in the existing combat member display. Preserve 6-second accounting, the 100-round cap, ordinary no-eligible-actor handling and all HP/MP/SP upkeep. The dependent terminal change supplies all-forced-sleep opening defeat, without an all-sleeping spectator mode.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/integrate-sleeping-combat-rosters` in `.worktrees/integrate-sleeping-combat-rosters` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

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

