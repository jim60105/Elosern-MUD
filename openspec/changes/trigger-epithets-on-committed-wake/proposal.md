# Proposal

## Why

Rest-day callbacks and examination triggers conflict with the approved wake-based workflow. Overlapping triggers currently have no per-player generation exclusion.

## What Changes

**BREAKING** Replace midnight-rest/exam nomination wiring with committed voluntary/forced awakening, logout and qualifying quest completion. Add generic source-award suppression, per-player single-flight lifecycle and real-boundary offline smoke coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Committed wake admission, extensible source-award suppression and per-player concurrency.

## Impact

server/title_nomination_service.py, server/conf/at_server_startstop.py, typeclasses/characters.py logout boundary, world/rules/fatigue.py, world/rules/time_skip.py, world/rules/combat_session/settlement.py, quest completion observers, command docs. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: unify-automatic-title-award-results
depends-on: record-lifecycle-recent-deeds
depends-on: record-action-adult-recent-deeds
depends-on: select-authorized-recent-deeds
depends-on: cite-recent-deeds-in-epithets

Code-conflict notes: Conflicts with A/B/C in settlement observers, D/E in nomination service and tests, and A/D/E in title-system spec application. Batch matrix is in `../unify-automatic-title-award-results/proposal.md`.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
