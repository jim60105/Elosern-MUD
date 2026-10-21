# Design

## Context

See proposal.md for motivation and dependencies. Baseline research found `WorldClock.advance` and `build_advance_snapshot_registry` in `world/rules/clock.py`, `advance_skip` and gauge-only `seconds_to_full_regen` in `world/rules/time_skip.py`, `present_party_scope` in `world/rules/party_scope.py`, verified `enter_possession` in `world/rules/possession.py`, and terminal `settle_session` plus player-centric outcome checks in `world/rules/combat_session/settlement.py`. SKIP currently has no per-body sleep selection, and `_practice_settlement` consumes bookings regardless of posture.

## Goals / Non-Goals

Implement the owning delta within one engineer-day using existing deterministic boundaries. No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Decisions

### Clock scope and settlement policy

`world/rules/clock.py::WorldClock.advance` remains the only time writer with integer seconds and the 86400-second bound. Add explicit optional mental interval context while preserving the existing ordered resource/boundary stages. Resolve `present_party_scope` before any writes; a distinct mental-scope channel covers present members even when a church rite or other accepted player-driven noncombat action retains a narrower resource scope. Do not widen gauges, quests, rites or practice merely to reach mental participants. Snapshot the union of ordinary and mental touched surfaces in `build_advance_snapshot_registry`; include durable attributes and in-process handler caches. Combat activity is supplied later by its own terminal owner, never inferred from SKIP.

Sample activity/posture at the beginning of an indivisible accepted field cast/item/rite interval. Consume the full interval, clamp, then collapse without converting a remainder into recovery. `world/rules/cast_settlement.py::settle_out_of_combat_cast` and `world/rules/items/settlement.py::use_item` retain complete action atomicity. Enumerate every `advance` production caller before cutover and classify it as player-driven noncombat, terminal combat or explicit GM-only; do not give future arbitrarily long work the indivisible policy by default.

### Interruptible orchestration and entry

Refactor `world/rules/time_skip.py::advance_skip` to return one immutable accepted result containing requested/elapsed seconds, member transitions, events and operation identity. Add proposed `enter_sleep` and `continue_sleep` operations. Safe voluntary entry commits only the explicitly selected body's posture at zero elapsed time. Handoff is offered through the dependent control component; continuation is a separate explicit decision. No other member is selected for sleep. Forced sleep begins at a settlement boundary even in an unsafe room, granting no skip or protection.

`seconds_to_full_regen` becomes the bounded maximum of current HP/MP/SP time-to-full and ceiling mental gap/12 for voluntary sleep. Forced sleep targets ceiling gap-to-72000/12. Waiting/custom duration and daypart requests use the same operation in `commands/skip.py` and `web/webclient/actions/exploration_actions.py::_wait_adapter`; retain `rest <duration> [practice <skill>]` as existing transport syntax, describe it consistently as waiting, and add no second quiet-rest command or stance. This is preservation of an existing entry point, not a compatibility shim. Existing text daypart vocabulary and browser twelve-hour protocol duration bound stay unchanged.

Predict the earliest forced-sleep entry, natural wake target or actual registered interactive event before advancing. Add a pure next-interactive-boundary query alongside registered clock events where needed; never execute a writer during prediction. Existing event-source surface declarations and order remain binding. Tie boundaries commit one shared interval and publish all due facts, with handoff candidates recomputed after the entire commit. Discard requested remainder. Operation admission/result identity prevents retry from replaying elapsed time; a new explicit wait has a new identity.

Practice settles only positive eligible awake SKIP intervals through `clock.py::_practice_settlement`; preserve sleeping and zero-time bookings. Keep the existing completed-whole-hours rule and eligible short-interval consumption; do not invent study accumulation across interrupted waits. Sleep and practice must not claim the same seconds.

### Movement and dream boundaries

After `charge-distance-based-travel` lands, add the present-forced-sleeper gate before every movement early return/relocation, including plain/costed exits, both wilderness gates and wilderness steps. Resolve intended source-present followers once and use that same set for refusal and rollback. `integrate-fatigue-aware-traversal` subsequently owns piecewise duration/depletion admission using the core API; this component neither duplicates geometry nor changes speed calibration.

Change `server.dream_service.enter_after_sleep` callers to consume only a real positive elapsed voluntary sleep receipt, never entry posture or forced sleep. Do not prompt for dream collaboration before the pre-elapsed handoff. Preserve existing offline departure and no-repeat-settlement behavior. The explicitly requested positive-elapsed rule supersedes the main dream spec's accepted-zero-duration entry scenario.

## Risks / Trade-offs

- Shared durable and cached attributes can diverge on a late failure. Extend existing snapshot owners and inject faults after both physiology and later enclosing writes.
- Dependent deltas share main capabilities. Apply in declared order, retaining earlier requirements when later deltas archive; no branch/worktree exists during planning.
- Interruptible integer-second boundaries need consistent rounding. The core API owns exact units and boundary offsets; consumers use the same accepted seconds for prediction and settlement.

## Migration Plan

Pre-release clean cutover, with no database/data migrations or compatibility layers. luna MUST apply on `feat/settle-party-sleep-and-wait` in `.worktrees/settle-party-sleep-and-wait` after prerequisites. Initialization belongs to deterministic construction/synchronization; failures restore the full prior state and do not silently refill malformed actors.

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

