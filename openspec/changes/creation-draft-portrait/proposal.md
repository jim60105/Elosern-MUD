# Proposal

## Why

The backend and empty slot do not yet let the player request and inspect a portrait while filling the form. Connect those existing slices end to end.

## What Changes

- Make `CreationPortraitSlot` render all committed states and emit generation intent.
- Mount the real `GalleryGenerateDrawer` in creation context with free-text-only capabilities.
- Correlate admission/results/revisions, keep refused input, and render completion without losing unsent form edits.
- Display server-provided offline refusal and offer explicit status refresh through existing synchronization, never a client probe or automatic generation retry.
- Add real-component stories and managed fake-client journeys for generation, reconnect and reset.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the creation contract owned by this slice.

## Impact

Live creation portrait slot and drawer integration. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. This is a concrete UI integration delivery, not an umbrella or a duplicate backend requirement. Two existing components, one focused composable and deterministic end-to-end journeys fit one engineer-day after the prerequisites.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

Visual fidelity, composition and player-facing wording are human-reviewed against the approved design, recorded during implementation in this change’s `visual-review.md` (named review document). Tests establish interaction/geometry, never copy, shipped content, preset counts or exact markup.

## Batch:

- depends-on: creation-stepped-form
- depends-on: creation-draft-portrait-cleanup
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. The proposal list, dependency DAG, conflict matrix and parallel implementation batches are in `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` §9.
- No code/spec conflict with the open `ciaran-village-local-goods` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
