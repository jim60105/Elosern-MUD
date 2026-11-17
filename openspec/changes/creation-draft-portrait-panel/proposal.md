# Proposal

## Why

Creation reconnects need authoritative progress rather than browser guesses. Expose the draft portrait receipt through the creation panel and existing publication owner.

## What Changes

- **BREAKING** creation panel 7 → 8 adds required `portrait` and rejects every other version.
- Serialize the closed portrait state union read-only; mirror validation in the browser.
- Publish pending/settled portrait changes to creation watchers without resetting unsent form state.
- Project the request slice's transient server availability into `portrait.unavailable`; explicit synchronization can clear a stale display refusal without probing or actor-state writes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-art-panel`: bounded per-image completion notifications, including applied client-construction failures, and pending-creation qualification.
- `webclient-character-creation-ui`: the creation contract owned by this slice.
- `official-art-resolution`: pending receipt eligibility authorizes only its exact validated runtime card.

## Impact

Portrait state, reconnect reconstruction and art-completion publication. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. One finite union, bounded per-image completion cutover and content-guarded form synchronization plus mirror validation; it reuses the request slice's state rather than adding a second state machine. This bounded state-delivery slice is one engineer-day; no request, cleanup or drawer work is included.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

## Batch:

- depends-on: creation-draft-portrait-request
- depends-on: creation-stepped-form
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. The proposal list, dependency DAG, conflict matrix and parallel implementation batches are in `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` §9.
- No code/spec conflict with the open `ciaran-village-local-goods` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
