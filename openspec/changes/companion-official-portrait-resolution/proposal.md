# Proposal

## Why

Companions with official artwork show an initial-letter placeholder in the lineup because the party presenter requires a runtime default card, even though the art panel resolves their official image. The gallery also tells the player that no portrait exists when official rows are available and the selected card filter is empty.

## What Changes

- Resolve companion `portrait_ref` eligibility through the existing read-only art chain, including personal official selections, classic runtime assets and mounted official defaults. Keep equipment-bound card precedence and truthful null portraits.
- Suppress the existing `gallery-panel__empty` paragraph whenever committed `official_entries` is non-empty and the selected filter has no visible cards. Preserve its text, class and cards-area location when no official entries exist.
- Extend synthetic Evennia and Vitest regressions and deterministic gallery showcase coverage. Document the preset-born `yuna_darknight` / `yuka_darknight` example without using shipped content in behavior tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-panel`: amend portrait eligibility in the existing exact read-only version-2 requirement while preserving its title and other scenarios.
- `webclient-gallery-ui`: add official-aware empty-guidance scenarios to the existing official-row requirement while preserving its title and other scenarios.

## Impact

Implementation is limited to the party portrait gate, `GalleryPanel.vue`, their existing tests and gallery stories. No wire schema, server gallery payload or dependency changes are required. Existing art resolution functions and the art panel catalog entry builder remain unchanged.

This is one engineer-day change. The two small presentation fixes share the same official-only artwork acceptance state, require no new subsystem and can be reviewed and released together. Implementation and focused evidence are bounded to existing files; no separate prerequisite change is needed.

## Non-goals

No changes to `set_official_selection` / `set_default` mutual clearing, `art-gallery-resolution` precedence, official catalog admission or `/art/official/...` routing. Do not change combat or dialogue portrait references, generation, seeding, gallery record ownership, or catalog membership/bounds. Official files remain read-only and official entries never become cards. No compatibility layer or migration is needed for this unreleased project.

## Scheduling

No dependencies on the active exploration or monster-AI changes. Proposals remain on `master`, and implementation is a later apply operation.

| Related change | Depends on | Spec conflict | Code conflict |
| --- | --- | --- | --- |
| `exploration-presence-rail` | None | None in the two modified capabilities | None for the planned existing-story approach; `component-manifest.json` / `.github/browser-shards.json` are conditional shared files if new exports or browser tests are added. |
| `exploration-room-actions` | None | None in the two modified capabilities | Same conditional showcase/browser manifest conflict. |
| Active `monster-ai-*` changes | None | None in the two modified capabilities | None in planned files; `.github/evennia-shards.json` is a conditional shared file if a new Python module is added. |

The planned path adds no story export, browser method or Python module, avoiding those shared manifest edits.
