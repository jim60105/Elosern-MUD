# Proposal

## Why

The approved party fatigue design requires independent sustained-activity physiology while preserving deterministic player time and existing combat settlement. Project protected physiological debuffs and shared action/status eligibility.

## What Changes

- **BREAKING** Project protected physiological debuffs and shared action/status eligibility.
- Deliver a bounded one-engineer-day component with behavior scenarios and rollback evidence; implementation remains assigned to luna.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `buff-handler-integration`: Apply the owning delta while preserving unrelated behavior.
- `cleanse-effect-handler`: Apply the owning delta while preserving unrelated behavior.
- `webclient-status-presentation`: Apply the owning delta while preserving unrelated behavior.
- `party-member-authority`: Apply the owning delta while preserving unrelated behavior.

## Impact

world/rules/buffs.py, status_query, party_scope.py; serialize with sleep and roster consumers. Source of decisions: `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md`, with metric movement integration owned by `integrate-fatigue-aware-traversal`.

## Non-goals

No compatibility layers or data migrations. No vehicles, fast travel, new movement enhancements, carrying sleepers, split-party exploration, party-capacity changes, active-monster encounters, waking abilities, reserve items, food/water/load simulation, quiet-rest surface/rate, per-round fatigue/recovery, natural in-battle wake, spectator mode or round-cap replacement.

## Batch:

depends-on: establish-mental-reserve-core
code-conflicts: world/rules/buffs.py, status_query, party_scope.py; serialize with sleep and roster consumers

Worker: luna
Branch: `feat/project-physiological-fatigue`
Worktree: `.worktrees/project-physiological-fatigue`

## Dependency and conflict matrix

| Change | Direct prerequisites | Code conflicts |
| --- | --- | --- |
| `establish-mental-reserve-core` | none | typeclasses/entities.py; new world/rules/fatigue.py and reserve snapshot declarations shared with projection/time/combat |
| `project-physiological-fatigue` | `establish-mental-reserve-core` | world/rules/buffs.py, status_query, party_scope.py; serialize with sleep and roster consumers |
| `settle-party-sleep-and-wait` | `project-physiological-fatigue`, `charge-distance-based-travel` | clock.py, time_skip.py, commands/skip.py, typeclasses/exits.py, movement.py; conflicts with charge-distance-based-travel and integrate-fatigue-aware-traversal |
| `handoff-sleeping-party-control` | `settle-party-sleep-and-wait` | possession.py, party_scope.py, exploration_actions.py, session presentation; conflicts with sleep adapters and combat authority |
| `integrate-sleeping-combat-rosters` | `project-physiological-fatigue` | combat_session records/rounds/opening, battlefield and AI; serialize with terminal fatigue |
| `settle-terminal-combat-fatigue` | `integrate-sleeping-combat-rosters`, `handoff-sleeping-party-control` | combat_session settlement/records/snapshot, clock snapshot declarations; conflicts with sleep settlement and handoff post-commit routing |
