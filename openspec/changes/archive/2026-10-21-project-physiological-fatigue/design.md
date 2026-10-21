# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

Use `world/rules/buffs.py`'s public application/removal paths, `world/rules/combat_modifiers.py` and `world/rules/status_display.py` registry metadata. Reserve/posture remain canonical; fatigue markers have no independent timed expiration. Reconcile projection inside the same owning write transaction. Apply agility/accuracy through matched combat-modifier rules, never by rewriting traits or encoding forbidden combat-stat modifiers inside buff definitions. The travel policy reads its own foot-speed scale once, without applying agility to movement again.

Extend shared external-removal eligibility so concrete, negative and all selectors preserve protected physiological instances and count only actual removals. Keep ordinary beneficial/debuff removal behavior and dispel hooks unchanged. Declare projection definitions and protection through validated rulebook metadata. Existing public grant-time immunity/unique-source guards remain binding; authored equipment immunity must not be used to erase canonical physiology or make the protected projection disagree with posture. Resolve that invariant at definition validation and deterministic projection, without an optional bypass of existing grant guards.

`world/rules/party_scope.py` acting authorization and canonical action blocking both consult actual sleep, including voluntary sleep; organizing and authenticated read/recovery remain lawful under their ordinary gates. Status queries stay no-create. Preserve A-keyed hybrid status under possession: show each body's fatigue with explicit member identity through existing member/status presentation instead of silently swapping unrelated resources to the host. Any necessary exact payload extension uses a coordinated schema cutover in server and both client validators; no legacy accepted form. Runtime status and command tests use synthetic bodies and assert threshold, cleanse, reload and action behavior.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/project-physiological-fatigue` in `.worktrees/project-physiological-fatigue` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

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

