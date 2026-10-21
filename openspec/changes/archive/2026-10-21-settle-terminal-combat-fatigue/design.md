# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

Extend `world/rules/combat_session/settlement.py::settle_session` inside its existing serialized round/terminal transaction. Use the record's initial posture and explicit round-boundary transitions to derive exact awake/sleep seconds from `rounds_elapsed * 6`, then pass intervals to the core fatigue writer once with the existing settled marker. Awake participants clamp at zero only at terminal completion; never infer an earlier collapse and retrospective recovery. Sleeping intervals recover but cannot reverse established defeat. Existing terminal resource-scope policy and unrelated gauge/upkeep behavior remain unchanged.

After canonical target/participant validation and record construction, detect all present allied participants in forced sleep before draft/first-round scheduling. Enter the ordinary `settle_session` path with zero elapsed rounds and hostile defeat or exam_failed according to existing mode. Let the existing aftermath advance its own real time; do not fabricate a combat round. Invalid engagement never invokes defeat. Other no-eligible conditions keep their existing behavior.

Snapshot reserve/posture, projected buffs, activity records, session/draft/receipt and every clock/aftermath surface before the terminal unit. Extend `world/rules/combat_session/snapshot.py::_snapshot_round_touched` and `_snapshot_round_clock` with the fatigue declarations. A later failure restores all member caches, not merely persisted attributes. Emit handoff/status events through after-commit hooks only after final defeat/aftermath survivor resolution. A below-threshold surviving sleeper remains stationary after victory.

The all-sleeping opening is tested directly against a valid engagement boundary without introducing proactive monster encounters. No passive in-battle fatigue tick, natural wake poll, spectator round loop, round-cap exception or in-session cast-time charge is permitted.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/settle-terminal-combat-fatigue` in `.worktrees/settle-terminal-combat-fatigue` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

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

