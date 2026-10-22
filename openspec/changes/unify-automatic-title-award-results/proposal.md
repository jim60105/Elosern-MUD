# Proposal

## Why

Automatic title grants currently return notification lines without a shared occurrence-linked result. Immediate nomination suppression needs authoritative grant results that remain correct under replay and future title producers.

## What Changes

Unify every automatic built-in-title grant behind one occurrence-linked rules entry point; preserve grant conditions and effects. Finalize immutable award results before the narrative event commits. Replace internal callers together without compatibility aliases.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Occurrence-linked automatic built-in-title grant results and transactional replay semantics.

## Impact

world/rules/titles/planner.py, world/rules/titles/ writers and exports, world/rules/action/contracts.py, world/rules/guild.py, world/rules/guild_exams.py, world/narrative/events.py. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: none

Code-conflict notes: Shared title writers, action result contracts, guild and examination settlements, narrative event finalization and title-system main-spec application conflict with later slices. Serialize these edits.

The authoritative proposal inventory, dependency/conflict matrix and parallel implementation waves are in [the approved design, section 12](../../../docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md#12-proposals-dependencies-and-parallel-implementation).

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
