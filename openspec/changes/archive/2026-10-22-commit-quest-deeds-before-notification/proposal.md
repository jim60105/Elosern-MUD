# Proposal

## Why

Quest completion observers run during pure planning, including before the purchase transaction starts. Completed-objective evidence also loses destination and role bindings before immutable persistence.

## What Changes

- Move completion notification to the actual quest write boundary after outer commit, keeping planning side-effect-free.
- Snapshot completed objective, destination and settled participant/escort roles before terminal bindings are cleared.
- Suppress duplicate completion notifications on unchanged record replacement and preserve transactional failure behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Specify complete quest settlement snapshots before binding cleanup.
- `title-system`: Specify owner-committed quest nomination with available source evidence.

## Impact

world/quests/runtime.py, transitions.py and completion planners/owners, server/title_nomination_service.py, quest/purchase/service tests; quest gameplay rules remain unchanged.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

Direct dependencies: none.

Corrective batch ID: C. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
