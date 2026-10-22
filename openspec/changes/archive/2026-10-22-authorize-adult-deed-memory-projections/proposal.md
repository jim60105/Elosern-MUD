# Proposal

## Why

A third living occupant currently makes a mixed-private adult payload public, and generic memory projection copies all of its fields to each participant. Nomination-only filtering cannot protect those owner-readable memories.

## What Changes

- Reuse one deterministic per-recipient adult field projection in recent-deed selection and shared memory projection.
- Keep participant knowledge separate from public visibility; never grant knowledge from proximity alone.
- Preserve restart-safe projection progress and immutable provenance without exposing other participants' private milestone or resistance internals.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-memory`: Specify recipient-authorized adult memory projection and replay boundaries.
- `narrative-events`: Specify that event-level visibility never authorizes all adult content fields.

## Impact

world/narrative/{action_adapters,recent_deeds,memory}.py and an existing-or-small shared projection module, focused memory/selector tests; no historical memory rewrite or reputation changes.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: repair-action-deed-results

Corrective batch ID: E. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
