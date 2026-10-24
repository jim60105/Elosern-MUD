# Proposal

## Why

Voluntary sleep currently retains no durable per-body wake plan across control handoff, and continuation wakes only the explicitly continued actor. A sleeping owner can saturate reserve while remaining asleep indefinitely; explicit party sleep and duration sleep need deterministic operations before consumers can present truthful choices.

## What Changes

- Persist one accepted sleep receipt per body, including duration/recovery target, progress and completion, and reconcile voluntary wakes on every applicable deterministic advance without changing possession.
- Add an explicit atomic all-present-effective-party sleep operation. Ordinary SKIP never selects additional sleepers.
- Expose supported `sleep [<duration>|until-recovered]`, `sleep all [<duration>|until-recovered]`, and `sleep continue` text forms with browser payload parity. Reuse the existing duration parser and bounds.
- Preserve independent HP/MP/SP and mental targets, sleeping practice exclusion, clock ownership and full persisted/cache compensation.
- Define the receipt interface consumed by the dependent handoff/dream change. No automatic dream behavior is added here.

## Capabilities

### New Capabilities

None. Extend existing deterministic sleep and party-settlement owners.

### Modified Capabilities

- `time-skip-commands`: body-scoped accepted sleep lifecycle, explicit modes and party operation.
- `party-time-settlement`: passive wake completion and receipt rollback with actual per-member activity.

## Impact

Primary consumers are `world/rules/time_skip.py`, `mental_time.py`, `clock.py`, fatigue settlement, `commands/skip.py` and the exploration wait adapter. Update both command documents, focused command/clock tests, shard ownership and requirement traceability. Amend the approved fatigue/sleep design's receipt, duration, explicit-party-operation and passive-wake wording during apply; do not edit its unrelated combat design. This pre-release cutover adds no migration, compatibility aliases, live-save repair or new posture enum.

## Batch:

depends-on: none

worker: gpt-luna
branch: feat/fix-body-sleep-lifecycle
worktree: .worktrees/fix-body-sleep-lifecycle

Bounded workday unit: deterministic receipt/settlement and thin transport syntax only. Contextual selection, dream orchestration and automatic owner continuation belong to `align-sleep-handoff-and-owner-dream`. Code conflicts with that dependent change include time_skip, commands/skip, exploration_actions, command docs, fatigue/sleep design and test manifests. Shared documentation/manifests with `block-travel-for-all-party-sleep` require serial integration, despite independent runtime algorithms. `unify-map-glyphs-across-map-surfaces` is unrelated; preserve it and serialize any shared manifest/traceability edits.
