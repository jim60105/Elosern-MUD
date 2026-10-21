# Proposal

## Why

The approved party fatigue design requires independent sustained-activity physiology while preserving deterministic player time and existing combat settlement. Offer verified contextual possession handoff and authenticated recovery controls.

## What Changes

- **BREAKING** Offer verified contextual possession handoff and authenticated recovery controls.
- Deliver a bounded one-engineer-day component with behavior scenarios and rollback evidence; implementation remains assigned to luna.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `companion-possession-core`: Apply the owning delta while preserving unrelated behavior.
- `companion-possession-transition`: Apply the owning delta while preserving unrelated behavior.
- `webclient-possession-presentation`: Apply the owning delta while preserving unrelated behavior.

## Impact

possession.py, party_scope.py, exploration_actions.py, session presentation; conflicts with sleep adapters and combat authority. Source of decisions: `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md`, with metric movement integration owned by `integrate-fatigue-aware-traversal`.

## Non-goals

No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Batch:

depends-on: settle-party-sleep-and-wait
code-conflicts: possession.py, party_scope.py, exploration_actions.py, session presentation; conflicts with sleep adapters and combat authority

Worker: luna
Branch: `feat/handoff-sleeping-party-control`
Worktree: `.worktrees/handoff-sleeping-party-control`

## Dependency and conflict matrix

| Change | Direct prerequisites | Code conflicts |
| --- | --- | --- |
| `establish-mental-reserve-core` | none | typeclasses/entities.py; new world/rules/fatigue.py and reserve snapshot declarations shared with projection/time/combat |
| `project-physiological-fatigue` | `establish-mental-reserve-core` | world/rules/buffs.py, status_query, party_scope.py; serialize with sleep and roster consumers |
| `settle-party-sleep-and-wait` | `project-physiological-fatigue`, `charge-distance-based-travel` | clock.py, time_skip.py, commands/skip.py, typeclasses/exits.py, movement.py; conflicts with charge-distance-based-travel and integrate-fatigue-aware-traversal |
| `handoff-sleeping-party-control` | `settle-party-sleep-and-wait` | possession.py, party_scope.py, exploration_actions.py, session presentation; conflicts with sleep adapters and combat authority |
| `integrate-sleeping-combat-rosters` | `project-physiological-fatigue` | combat_session records/rounds/opening, battlefield and AI; serialize with terminal fatigue |
| `settle-terminal-combat-fatigue` | `integrate-sleeping-combat-rosters`, `handoff-sleeping-party-control` | combat_session settlement/records/snapshot, clock snapshot declarations; conflicts with sleep settlement and handoff post-commit routing |
