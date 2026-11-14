# Proposal

## Why

The approved map-column prototype (`docs/design/map-column-instrument-panels/`, after `docs/development/hud-instrument-panels.md`) turns the stage's right-hand `map` column into three borderless instrument panels. Before any of the three components can be restyled, the column itself must give them room and air: the minimap panel needs at least 282px (a 240px canvas, 22px of spine clearance and a 20px feather) where the live column is 250px at 1280x720, and an over-tall column's scrollbar would cross the three brass spines and cut the minimap feather to a hard edge.

## What Changes

- A new design token `--map-column-w` states the `map` column width once: `max(calc(var(--right-column) - 28px * var(--ui-scale)), calc(282px * var(--ui-scale)))`. Both geometry copies of the `map` anchor (`HudFrame.vue` and the `.elosern-root` rule in `styles/app-shell.css`) read it, and the neighbours that offset from the column's left edge (the `presence` anchor and the scene-backdrop placeholder) derive from it instead of re-deriving `--right-column`.
- The `map` anchor stacks its surfaces 10px apart in both copies (it was 9px in `HudFrame.vue`, 14px in `app-shell.css`, 10px under the short-viewport query) and still paints nothing itself.
- An over-tall `map` anchor keeps its max-height and vertical scroll but shows no scrollbar. Instead, while content lies beyond the top or bottom edge, that edge fades out over 32px; a column that fits is not masked. The state is measured from scroll events, a ResizeObserver on the anchor and its children, and a MutationObserver that re-observes the children when one mounts or unmounts.
- No component is restyled here; the place card, minimap and objective line keep their current chrome until `place-card-instrument-panel`, `local-map-instrument-panel` and `objective-tracker-instrument-panel` land.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: a new requirement states the `map` column's width floor, its 10px stack gap, its paint-free anchor and its scrollbar-free edge fade; the island-stack requirement is restated so a surface in an island anchor may wear either the island chrome or the instrument-panel chrome its own requirement names.

## Impact

- Code: `web/webclient-app/styles/tokens.css` (new `--map-column-w`), `web/webclient-app/components/HudFrame.vue` (`map` anchor width, gap, scrollbar, edge mask, ref and data attributes; `presence` offset), `web/webclient-app/styles/app-shell.css` (`.elosern-root` `map` rule width and gap, scrollbar rule, short-viewport gap line, placeholder offset), new `web/webclient-app/composables/use-scroll-edge-fade.js`.
- Tests: `web/webclient-app/tests/hud_frame.test.js` (both geometry copies, token, neighbours), new `web/webclient-app/tests/use_scroll_edge_fade.test.js`, a new live-client browser test file `web/tests/browser/test_browser_map_column_instruments.py`, registered in `.github/browser-shards.json`.
- Human-reviewed: the visual fidelity of the column against the approved prototype at 1280x720, 1451x790 and 2560x1440, recorded in the review document named in `design.md` (§ Visual review). No automated test judges the look.

## Batch:

- depends-on: none (first of the batch)
- conflicts: `place-card-instrument-panel` edits the same `@media (max-height: 820px)` block of `styles/app-shell.css`; `local-map-instrument-panel` and `objective-tracker-instrument-panel` add methods to the new `web/tests/browser/test_browser_map_column_instruments.py` and append to `.github/browser-shards.json`. Land this change first.
