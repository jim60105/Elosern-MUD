# Proposal

## Why

Quest completion, examination passage and encounter outcomes must survive beyond transient callbacks to support recent-deed nomination.

## What Changes

Persist deterministic completion and encounter facts in the existing narrative store, with actual outcomes, durable participants and finalized automatic-award results. Keep examinations evidence-only and protect other narrative consumers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Transactional quest, examination and completed-combat evidence.

## Impact

world/quests/runtime.py, quest settlement owners, world/rules/guild.py, world/rules/guild_exams.py, world/rules/combat_session/settlement.py, world/narrative/events.py. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: unify-automatic-title-award-results

Code-conflict notes: Conflicts with A in guild/exam writers and event finalization, C in narrative event contracts and narrative-events spec application, and F in quest/combat settlement notifications. Batch matrix is in `../unify-automatic-title-award-results/proposal.md`.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
