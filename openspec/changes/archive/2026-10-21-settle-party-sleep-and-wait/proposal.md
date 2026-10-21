# Proposal

## Why

The approved party fatigue design requires independent sustained-activity physiology while preserving deterministic player time and existing combat settlement. Settle player-driven party time with per-body sleep, bounded waits and stationary travel.

## What Changes

- **BREAKING** Settle player-driven party time with per-body sleep, bounded waits and stationary travel.
- Deliver a bounded one-engineer-day component with behavior scenarios and rollback evidence; implementation remains assigned to luna.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `party-time-settlement`: Apply the owning delta while preserving unrelated behavior.
- `time-skip-commands`: Apply the owning delta while preserving unrelated behavior.
- `world-clock`: Apply the owning delta while preserving unrelated behavior.
- `settlement-stage-order`: Apply the owning delta while preserving unrelated behavior.
- `dream-sleep-surface`: Apply the owning delta while preserving unrelated behavior.
- `companion-field-actions`: Apply the owning delta while preserving unrelated behavior.
- `party-system`: Apply the owning delta while preserving unrelated behavior.
- `webclient-exploration-menu`: Apply the owning delta while preserving unrelated behavior.

## Impact

clock.py, time_skip.py, commands/skip.py, typeclasses/exits.py, movement.py; conflicts with charge-distance-based-travel and integrate-fatigue-aware-traversal. Source of decisions: `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md`, with metric movement integration owned by `integrate-fatigue-aware-traversal`.

## Non-goals

No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Batch:

depends-on: project-physiological-fatigue
depends-on: charge-distance-based-travel
code-conflicts: clock.py, time_skip.py, commands/skip.py, typeclasses/exits.py, movement.py; conflicts with charge-distance-based-travel and integrate-fatigue-aware-traversal

Worker: luna
Branch: `feat/settle-party-sleep-and-wait`
Worktree: `.worktrees/settle-party-sleep-and-wait`

## Dependency and conflict matrix

| Change | Direct prerequisites | Code conflicts |
| --- | --- | --- |
| `establish-mental-reserve-core` | none | typeclasses/entities.py; new world/rules/fatigue.py and reserve snapshot declarations shared with projection/time/combat |
| `project-physiological-fatigue` | `establish-mental-reserve-core` | world/rules/buffs.py, status_query, party_scope.py; serialize with sleep and roster consumers |
| `settle-party-sleep-and-wait` | `project-physiological-fatigue`, `charge-distance-based-travel` | clock.py, time_skip.py, commands/skip.py, typeclasses/exits.py, movement.py; conflicts with charge-distance-based-travel and integrate-fatigue-aware-traversal |
| `handoff-sleeping-party-control` | `settle-party-sleep-and-wait` | possession.py, party_scope.py, exploration_actions.py, session presentation; conflicts with sleep adapters and combat authority |
| `integrate-sleeping-combat-rosters` | `project-physiological-fatigue` | combat_session records/rounds/opening, battlefield and AI; serialize with terminal fatigue |
| `settle-terminal-combat-fatigue` | `integrate-sleeping-combat-rosters`, `handoff-sleeping-party-control` | combat_session settlement/records/snapshot, clock snapshot declarations; conflicts with sleep settlement and handoff post-commit routing |
