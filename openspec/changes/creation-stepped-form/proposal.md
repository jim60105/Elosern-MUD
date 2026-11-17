# Proposal

## Why

The custom form currently displays independently scrolling regions, while concept mode gives little guidance. Split presentation without replacing creation validation.

## What Changes

- Extract `CreationCustomSteps`, `use-creation-steps` and an empty-state-only `CreationPortraitSlot`.
- Keep footer confirmation and remaining allocation points reachable across freely navigable steps.
- Extract `CreationConceptGuide`; derive completion marks from proposal fields and return a fresh concept apply to identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-character-creation-ui`: the creation contract owned by this slice.
- `concept-transient-fill`: step-aware proposal navigation while preserving unsent fill.

## Impact

Stepped custom form and concept guide. File/symbol boundaries and runnable acceptance commands are in `design.md` and `tasks.md`. Existing form state/handlers and field hooks move intact; only local navigation, error projection and concept checklist are new. No generation UI or server changes; one engineer-day.

Approved source: `docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md` (§§4–13); architecture: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`. Planning baseline is primary `master` at `e5108ba23b15de1be410e5df3bc297e2202c17cc`. Single repository; no child repository is needed. No compatibility layer or migration.

Visual fidelity, composition and player-facing wording are human-reviewed against the approved design, recorded during implementation in this change’s `visual-review.md` (named review document). Tests establish interaction/geometry, never copy, shipped content, preset counts or exact markup.

## Batch:

- depends-on: creation-preset-card-wall
- Code-conflict notes: serialize shared `creation.py`/browser validator/fixture schema edits in 1 → 4 → 5; shared overlay/stories in 2 → 3 → 7; rules/service/queue/receipt edits in 4 → 6. Detailed matrix is in `creation-draft-portrait/design.md`.
- No code/spec conflict with `ciaran-village-local-goods`, `fionnen-village-craft-homes` or `fionnen-village-fare-homes`: those change lore/commerce/maps and editorial documents; this batch changes creation/art mechanisms and frontend synchronization documentation. Shared CI shard manifests are integration-only conflicts if both deliveries register tests; regenerate registrations after earlier changes instead of replacing their entries.
