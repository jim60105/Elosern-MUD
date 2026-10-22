# Proposal

## Why

The nomination service has no durable recent-history read. A bounded, authorized rolling feed must precede any prompt generation.

## What Changes

Read committed narrative facts through a closed deterministic adapter set. Filter the inclusive rolling 48-hour window and field-level access before aggregation, then render bounded complete factual groups with immutable provenance.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Recent-deed eligibility, authorization, time selection and bounded aggregation.

## Impact

world/narrative/events.py and a focused recent-deed read adapter under world/narrative/, canonical world clock configuration, server/title_nomination_service.py context boundary. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: record-lifecycle-recent-deeds
depends-on: record-action-adult-recent-deeds

Code-conflict notes: Conflicts with C in action adapter payloads, E/F in composition-root context, and A/E/F in title-system spec application. Batch matrix is in `../unify-automatic-title-award-results/proposal.md`.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
