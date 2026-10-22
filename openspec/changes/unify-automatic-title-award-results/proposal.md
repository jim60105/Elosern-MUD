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

### Dependency and conflict matrix

| ID | Change | Direct dependencies | Code conflicts |
|---|---|---|---|
| A | unify-automatic-title-award-results | none | B/C settlement contracts and event finalization; D/E/F title-system spec application; F source notifications |
| B | record-lifecycle-recent-deeds | A | C narrative event contract and narrative-events spec application; F quest/combat settlement notifications |
| C | record-action-adult-recent-deeds | A | B narrative event contract and narrative-events spec application; D adapter payloads; F combat/action settlement integration |
| D | select-authorized-recent-deeds | B, C | E/F composition-root context; A/E/F title-system spec application |
| E | cite-recent-deeds-in-epithets | D | F nomination service, prompt/service tests; A/D/F title-system spec application |
| F | trigger-epithets-on-committed-wake | A, B, C, D, E | A/B/C settlement observers; D/E nomination service; A/D/E title-system spec application |

Use A, then B and C with shared-file serialization, then D, E and F. B and C are semantically independent after A; their shared event contract and spec edits require integration ownership. No change automatically creates a new eligible trigger merely by producing an award result or evidence.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
