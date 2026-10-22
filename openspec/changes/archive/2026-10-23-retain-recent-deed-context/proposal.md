# Proposal

## Why

All current nomination projections omit stored event locations. The service also logs tick zero because the selector's frozen tick is not carried in NominationContext.

## What Changes

- Carry authoritative location identities and readable settlement snapshots through every supported adapter and bounded group.
- Retain occurrence-specific time/location provenance when repetitions or encounters span multiple locations.
- Freeze request time once at admission and reuse it for selection, request context and all workflow diagnostics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Specify settlement-time location snapshots for covered evidence.
- `title-system`: Specify location-preserving rendering and exact frozen-tick diagnostics.

## Impact

world/narrative/recent_deeds.py and supported producer metadata, server/title_nomination_service.py, world/ai/title_nomination.py plain context, focused selection/service tests; unchanged 48-hour, eight-group and 8000-code-point limits.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: repair-action-deed-results
depends-on: preserve-combat-deed-provenance
depends-on: commit-quest-deeds-before-notification
depends-on: authorize-adult-deed-memory-projections
depends-on: record-nonresolver-adult-milestones

Corrective batch ID: G. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
