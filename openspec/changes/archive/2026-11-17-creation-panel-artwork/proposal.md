# Proposal

## Why

Creation has no server-provided art for preset previews or the empty custom portrait slot. Land its bounded data contract before changing either UI.

## What Changes

- **BREAKING** creation panel 6 → 7, with exact rejection on both validators.
- Add server-built `presets[].artwork` and per-actor `custom.silhouettes`; preserve all existing draft/proposal behavior.
- Reuse catalog and fallback primitives without creating a character or touching portrait policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the creation contract owned by this slice.
- `art-gallery-fallback`: pure preview demographic resolution.
- `official-art-resolution`: catalog-only preset previews.

## Impact

Read-only creation artwork metadata. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. Only two pure preview builders, one serializer and its two validators change. Catalog scanning, assets, generation and UI remain unchanged, making this one engineer-day.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

## Batch:

- depends-on: none
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. The proposal list, dependency DAG, conflict matrix and parallel implementation batches are in `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` §9.
- No code/spec conflict with the open `ciaran-village-local-goods` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
