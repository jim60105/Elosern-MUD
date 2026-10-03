# place-card-relocation

## Why

The place card sits alone in the stage's top-left corner above the vitals stack, pushing the vitals anchor down and splitting the stage's top edge into two unrelated clusters. The location label and world time are the reader's "where and when" companion to the minimap's "where am I" drawing, so the card belongs directly above the minimap island in the top-right `map` anchor, where the two read as one column.

## What Changes

- The PlaceCard moves from the `place` anchor (stage box's top-left) into the `map` anchor (top-right) as the first island, directly above the minimap island.
- The `place` anchor is removed from the stage: the `vitals` anchor becomes the stage's top-left island anchor and starts directly below the top band (no longer clearing the place card's fixed height), which also frees vertical space for the vitals stack at short viewports.
- The place card's width matches the minimap island's width, its heading drops from the `--text-xl` step to `--text-lg`, its fixed height token shrinks, and the decorative gold rule shortens so the card reads as a compact header of the map column.
- Mode visibility is behaviorally unchanged — the card is visible in exploration, combat, and dialogue and hidden in creation — but it is now hidden with the `map` anchor in creation, and in combat it stands above the participant frame while the minimap is hidden.
- The portrait face-clearing rule follows: the left island column is now only the vitals stack, and the right island column is the place card plus the minimap island (same column width, so the reference insets are unchanged in value).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `webclient-contextual-hud`: the stage-layout requirement redefines the anchors (no `place` anchor; `vitals` begins below the top band; the `map` column is the place card, then the minimap island, then the objective line and any other island); the island-stack requirement reorders both stacks; the place-card requirement relocates the card into the `map` anchor at the minimap's width with the smaller type step; the minimap-island requirement now sits directly below the place card; the visibility-matrix and face-clearing wording follows the new anchors.

## Impact

- `web/webclient-app/components/HudFrame.vue`: remove the `place` anchor div and its CSS; adjust the `vitals` anchor's `top`/`max-height` to no longer clear `--place-h`; update the creation-mode hide rule.
- `web/webclient-app/styles/app-shell.css`: mirror the `vitals`/`map` anchor offset changes and the short-viewport block (the `--place-h` shrink stays a token change).
- `web/webclient-app/styles/tokens.css`: shrink `--place-h`; the `--actor-left-inset`/`--actor-right-inset` formulas keep their values (columns' left/right edges are unchanged).
- `web/webclient-app/components/AppShell.vue`: render `PlaceCard` in the `#map` slot above the minimap instead of the `#place` slot.
- `web/webclient-app/components/PlaceCard.vue`: heading `--text-xl` → `--text-lg`, narrower/subtler rule, comment updates.
- Tests: `place_card.test.js`, `app.test.js`, `scene_transitions.test.js`, `stories/Core/PlaceCard.stories.js` (anchor placement expectations and story wrapper width).
