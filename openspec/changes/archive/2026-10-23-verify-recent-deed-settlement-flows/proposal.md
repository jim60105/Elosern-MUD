# Proposal

## Why

The named end-to-end smoke inserts narrative rows directly and does not verify gameplay settlement, complete rollback or committed reload. Component tests therefore miss the reviewed producer-to-consumer failures.

## What Changes

- Replace seed-only smoke claims with real synthetic quest, adult-action and multi-round combat settlement through production composition.
- Verify committed selection, exact rendered citations, fake external transport and fresh persisted ballot/title reads.
- Exercise rollback after actual gameplay/title/evidence writes, private-field controls and real overlapping/late generation outcomes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: Specify representative real-settlement evidence for the existing nomination contract.

## Impact

server/conf/tests/test_title_nomination_service.py and focused owner integration tests, shard manifest only if modules move or are added; no new production generation behavior or live external service.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

depends-on: repair-action-deed-results
depends-on: preserve-combat-deed-provenance
depends-on: commit-quest-deeds-before-notification
depends-on: associate-quest-completion-title-awards
depends-on: authorize-adult-deed-memory-projections
depends-on: record-nonresolver-adult-milestones
depends-on: retain-recent-deed-context

Corrective batch ID: H. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).
