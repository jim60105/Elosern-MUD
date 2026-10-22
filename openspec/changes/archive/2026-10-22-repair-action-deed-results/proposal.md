# Proposal

## Why

The deed hook rejects valid auto-comply actions and filters out effect names emitted by production handlers. Adult transitions and counters are then discarded by the nomination projection.

## What Changes

- Accept the existing absent-roll sentinel without changing resistance mechanics.
- Normalize actual emitted skill/adult effects and preserve authorized transitions, counters and resistance semantics through grouping.
- Remove the divergent production-versus-test serialization behavior and add producer-to-renderer regression coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `narrative-events`: Specify accepted settled result vocabulary and failure-safe legal action recording.
- `title-system`: Specify preservation of authorized adult result families during grouping.

## Impact

world/narrative/action_adapters.py, world/narrative/recent_deeds.py, focused action/title tests; no dependencies or player command changes.

## Size and non-goals

One engineer, one workday (8 hours). Planning artifacts only. No backward compatibility, migrations, historical backfill, balance changes, new shipped titles, new trigger categories or automatic epithet adoption.

## Authority

Approved design: `docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md`. Architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` section 3.1. Existing main specs remain current until archive synchronization.

## Batch

Direct dependencies: none.

Corrective batch ID: A. Scope and conflict ownership are in the [batch matrix](../repair-action-deed-results/proposal.md#corrective-batch-matrix).

## Corrective batch matrix

The IDs below belong to this corrective batch, not the archived original A-F implementation batch. Every change is capped at one engineer-day (8 hours), including focused verification and integration bookkeeping. Proposal creation authorizes no implementation.

| ID | Change | Direct dependencies | Shared implementation/spec surfaces |
| --- | --- | --- | --- |
| A | repair-action-deed-results | none | B/E/F/G: action adapters or recent_deeds; narrative-events/title-system |
| B | preserve-combat-deed-provenance | A | E/G: recent_deeds; F: combat rounds/adapters; narrative-events/title-system |
| C | commit-quest-deeds-before-notification | none | D: quest transitions/snapshots; G: quest metadata/service; H: service tests; narrative-events/title-system |
| D | associate-quest-completion-title-awards | C | G: quest transitions; H: award/service tests; title-system |
| E | authorize-adult-deed-memory-projections | A | B/G: recent_deeds; F/G: action projection contract; narrative-events/narrative-memory |
| F | record-nonresolver-adult-milestones | A, B, E | G: producer metadata/adapters; narrative-events |
| G | retain-recent-deed-context | A, B, C, E, F | D: quest producer; H: service tests; narrative-events/title-system |
| H | verify-recent-deed-settlement-flows | A, B, C, D, E, F, G | all behavior owners' tests, shard manifest; title-system |

Recommended integration waves: **A + C**, then **B + D**, then **E**, **F**, **G**, **H**. These are future implementation waves; proposal drafting and the single critique run sequentially. Parallel pairs have separate production edit surfaces; one integration owner serializes main-spec synchronization and any manifest edits. Do not parallelize B with E/G or F with G. If shared-file ownership is unavailable, apply A through H sequentially. Main capability deltas are proposed, not synchronized by this batch.

## Review finding coverage

| Finding from the final review | Owning corrective change |
| --- | --- |
| 1: absent resistance roll breaks auto-comply | A |
| 2: combat action identity collapse and missing encounter join | B |
| 3: quest completion notification during planning | C |
| 4: missing effects, adult transitions and counters | A |
| 5: late upkeep snapshot and missing item/defeat owners | F |
| 6: terminal encounter overwrite on reusable session identity | B |
| 7: private adult fields copied into shared memory | E |
| 8: incomplete quest objective | C |
| 8: lost locations | G |
| 9: seed-only end-to-end smoke and incomplete rollback/reload proof | H |
| Diagnostic frozen-tick mismatch | G |
| Future quest-completed title/source association | D |

No historical backfill, data migration, compatibility parser or deprecated API is part of any corrective change. The original approved design remains authoritative. Gameplay-resolver idempotency for arbitrary duplicate user submissions is not introduced; replay guarantees cover committed settlement notifications and immutable evidence.
