# Proposal

## Why

Template-only summaries lose committed adult outcomes and provide no citation contract. Candidates need provenance tied to the exact material rendered for a request.

## What Changes

**BREAKING** Replace the event-log-only nomination input with structured recent deeds and add candidate source_ids validation. Remove the old serializer and migrate all generation callers together while retaining the ballot shape and existing consent writers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Structured nomination prompt, citations and unchanged deterministic ballot admission.

## Impact

world/ai/title_nomination.py, prompts title_nomination entry, server/title_nomination_service.py, world/ai/tests and server/conf/tests/test_title_nomination_service.py. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: select-authorized-recent-deeds

Code-conflict notes: Conflicts with D/F in nomination service context, F in service tests and A/D/F in title-system spec application. Batch matrix is in `../unify-automatic-title-award-results/proposal.md`.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
