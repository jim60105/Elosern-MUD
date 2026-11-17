# Proposal

## Why

Browsing art must not save a preset or open activation confirmation. Separate local expansion from the existing deliberate selection path.

## What Changes

- Replace the preset grid with `CreationPresetWall` and move shared mode tabs into the header.
- Route pointer, arrows and digits to local expansion; the primary action and Enter on the expanded card select through the existing save/confirmation pipeline.
- Render server descriptors with `ArtworkPreview`, including metadata crop and existing fallback.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the creation contract owned by this slice.

## Impact

Preset card wall and overlay shell. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. One mode, its keyboard ownership and shared shell styling; no form rewrite or server change. Existing ArtworkPreview and confirmation handlers bound the work to one engineer-day.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

Visual fidelity, composition and player-facing wording are human-reviewed against the approved design, recorded during implementation in this change’s `visual-review.md` (named review document). Tests establish interaction/geometry, never copy, shipped content, preset counts or exact markup.

## Batch:

- depends-on: creation-panel-artwork
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. The proposal list, dependency DAG, conflict matrix and parallel implementation batches are in `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` §9.
- No code/spec conflict with the open `ciaran-village-local-goods` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
