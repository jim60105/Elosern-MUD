# Proposal

## Why

Completion records read awards from a completion source while the generic title planner associates grants with action sources. The approved future quest-title contract therefore has no complete production forwarding seam.

## What Changes

- Finalize quest-completed predicate awards through the unified rules entry point under the completion occurrence before its immutable fact is written.
- Remove that predicate family from unrelated action-time automatic grant discovery while retaining predicate semantics.
- Forward committed results to immediate nomination and cover nested rollback, replay and recipient-specific suppression with synthetic registry rows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Specify quest-owned occurrence association and complete grant/evidence rollback.

## Impact

world/rules/titles/{awards,planner}.py, world/quests/transitions.py, quest-delta/enclosing-owner snapshot surfaces and focused title tests; no new shipped titles or changed starter reward-claim attribution.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: commit-quest-deeds-before-notification

Corrective batch ID: D. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
