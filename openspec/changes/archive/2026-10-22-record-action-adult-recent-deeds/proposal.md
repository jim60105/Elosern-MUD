# Proposal

## Why

Transient action logs contain deterministic effects that the nomination serializer omits. Lifetime adult state cannot establish when an experience happened.

## What Changes

Persist settled skill and adult-action outcomes plus newly crossed adult milestones through the existing narrative store. Preserve actual actor/recipient roles and knowledge boundaries without adding immediate skill triggers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Deterministic skill/adult action evidence and transition-time milestones.

## Impact

world/rules/action/resolver.py, world/rules/action/event_log.py, world/rules/action/contracts.py, world/rules/sexual_state/handler.py, adult settlement owners, world/narrative/events.py. Focused synthetic tests, shard registration and spec traceability are included. One engineer-day, limited to the listed behavior slice.

## Non-goals

No implementation in this proposal. No migrations, historical backfill, compatibility layers, fatigue or adult-mechanic rebalance, reputation system, or automatic adoption of generated names.

## Batch:

depends-on: unify-automatic-title-award-results

Code-conflict notes: Conflicts with A in action/title result contracts, B in narrative event contracts and narrative-events spec application, D in adapter payloads, and F in combat/action integration. Batch matrix is in `../unify-automatic-title-award-results/proposal.md`.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture ownership remains as defined in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1. The batch replaces the old trigger/input contracts in `title-system`; other title behavior remains intact.
