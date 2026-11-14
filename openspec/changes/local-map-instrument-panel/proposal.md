# Proposal

## Why

The minimap is the second `map`-column surface the approved prototype (`docs/design/map-column-instrument-panels/LocalMapInstrument.vue`) restates as a borderless instrument panel. Today it is a 250px card (fill, hairline border, radius, shadow, 4px padding) whose header also carries a `北↑ 東→` renderer-axis legend. The minimap never rotates, so that legend states nothing the player can use and only takes header width from the map's title.

## What Changes

- `LocalMap.vue` renders its island inside an instrument panel (the shared `instrument-panel` chrome from `place-card-instrument-panel`) that spans the column. The island itself loses its card: no fill, border, radius, shadow or padding. The canvas keeps its own ink ground and four gold corner brackets.
- The canvas stands clear of the spine (22px × S right padding), so the brass spine runs unbroken; the panel's ink stays solid under the 240px canvas plus the 22px clearance and feathers out over a 24px band to its left, so the opaque canvas never sits on thinned ink.
- **BREAKING** (pre-release, no compatibility path): the renderer-axis orientation legend (`北↑ 東→`, `data-testid="local-map__orientation"`) is removed from the live component on every layout variant. The axis cross the lattice draws through the current node stays as the drawing's own geometry; it is no longer described as "licensed" by worded marks, and the full-map surface still draws none.
- The open-map glyph in the header takes over the hover feedback the border used to give: dimmed at rest, fully opaque while the island is hovered or holds focus.
- The `.elosern-root .local-map` border-colour duplicates in `styles/app-shell.css` are removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: the minimap island requirement places the island inside its own instrument panel, drops the orientation marks, keeps the lattice axis cross as geometry, and adds the no-card, spine-clearance and glyph-feedback scenarios.
- `webclient-local-map`: the legibility requirement and the minimap presentation requirement drop the orientation marks and the island's hairline frame and padding, and restate the axis-cross rule without worded marks.
- `webclient-vue-application`: the chrome-type requirement's island scenario no longer lists orientation marks.

## Impact

- Code: `web/webclient-app/components/LocalMap.vue` (template wrapper, orientation span and its computed removed, scoped styles); `web/webclient-app/styles/app-shell.css` (two `.elosern-root .local-map` lines).
- Tests: `web/webclient-app/tests/world/local_map.test.js`, `tests/world/map_layout_variants.test.js`, `tests/overlays/objective_tracker_integration.test.js` (anchor child order); browser tests `test_browser_contextual_hud_stage.py`, `test_browser_local_map_layout_variants.py`, `test_browser_map_legibility.py` (orientation probes removed or replaced by the axis), and a new method in `test_browser_map_column_instruments.py`, registered in `.github/browser-shards.json`.
- Stories: `web/webclient-app/stories/World/LocalMap.stories.js` (frame and header comment) and comments in `stories/fixtures/local_map.js`; the component manifest is unchanged.
- Human-reviewed: the minimap panel's visual fidelity against `LocalMapInstrument.vue`, recorded in the review document named in `design.md` (§ Visual review). No automated test judges the look.

## Batch:

- depends-on: place-card-instrument-panel
- conflicts: imports `components/instrument-panel.css` created by `place-card-instrument-panel`; adds methods to `web/tests/browser/test_browser_map_column_instruments.py` and appends to `.github/browser-shards.json` like `objective-tracker-instrument-panel`, and both edit `tests/overlays/objective_tracker_integration.test.js`. Land it third, before `objective-tracker-instrument-panel`.
