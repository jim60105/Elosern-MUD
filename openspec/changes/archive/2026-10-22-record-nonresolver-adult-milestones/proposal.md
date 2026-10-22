# Proposal

## Why

Combat upkeep snapshots sexual state after buff reactions can change it, while item and defeat-aftermath owners omit their transition-time evidence. Later clock reads cannot reconstruct when an onset or unlock occurred.

## What Changes

- Capture milestone baselines before buff ticks and write newly crossed milestones in the owning transaction.
- Integrate item-use and defeat-aftermath transition owners with stable operation/attempt identities and exact affected recipients.
- Record actual defeat adult acts and resistance outcomes through the existing eligible adult-action contract, keeping all existing mechanics and timing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Specify evidence from upkeep, item and defeat adult transition owners.

## Impact

world/rules/combat/rounds.py, world/rules/items/settlement.py and request provenance, world/rules/defeat_aftermath/violation.py, world/narrative/action_adapters.py, scoped owner tests; no ordinary item or upkeep nomination trigger.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: repair-action-deed-results
depends-on: preserve-combat-deed-provenance
depends-on: authorize-adult-deed-memory-projections

Corrective batch ID: F. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
