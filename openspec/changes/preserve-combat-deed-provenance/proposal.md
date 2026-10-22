# Proposal

## Why

Production battlefields do not carry the encounter identity read by the deed adapter, collapsing repeated same-tick skill occurrences. Terminal selection also indexes distinct engagements by a reusable transport session identity.

## What Changes

- Carry typed engagement, round and slot provenance from the combat owner into source construction and evidence.
- Use the same unique engagement identity for action facts, upkeep milestones, terminal facts and selection joins.
- Preserve distinct zero-time re-engagements and repeated same-skill occurrences without changing combat transport tokens.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Specify distinct combat action and encounter provenance at settlement.
- `title-system`: Specify authoritative encounter joins without source loss or cross-encounter merging.

## Impact

world/rules/combat_session/{battlefield,lifecycle,settlement,rounds}.py, world/rules/combat/{battlefield,rounds}.py, action context/provenance readers, narrative adapters and selector; no transport redesign.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: repair-action-deed-results

Corrective batch ID: B. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
