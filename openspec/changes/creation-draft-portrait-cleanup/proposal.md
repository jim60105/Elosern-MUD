# Proposal

## Why

Early portrait ownership must survive custom activation rollback, yet explicit reset and preset activation must remove only creation-owned output.

## What Changes

- Reset clears the draft and cancels/removes its portrait jobs/cards transactionally.
- Custom activation keeps the subject and existing art; activation guard prevents duplicate generation.
- Preset activation removes draft art before the preset portrait finalizer; late canceled settlements cannot resurrect it.
- Identity edits and concept fills do not invalidate or warn about retained portraits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: reset and preset/custom activation disposition.
- `art-gallery-autogen`: draft-age exception and activation/rollback ownership.
- `webclient-character-creation-ui`: the creation contract owned by this slice.

## Impact

Draft portrait reset and activation lifecycle. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. Reuse the receipt and queue-token guards for two lifecycle entrypoints and rollback tests. No UI redesign, new subject, or gallery policy change; one engineer-day.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

## Batch:

- depends-on: creation-draft-portrait-panel
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. Detailed matrix is in `creation-draft-portrait/design.md`.
- No code/spec conflict with `ciaran-village-local-goods`, `fionnen-village-craft-homes` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
