# Proposal

## Why

Reaching a district's authored landmark lights the whole district in map knowledge, but the wilderness view only ever publishes a centred 41×41 one-kilometre window. The rest of the lit district is fog, so lighting a region feels like a local reveal instead of the high-tier exploration shortcut the design promises. A player can light 王都河谷 by standing on 中央廣場 and still see only the neighbourhood around the east gate.

## What Changes

- Add a bounded, coarse **district overview** to the wilderness `area_map` payload. When the party's current wilderness cell belongs to a lit district, the panel carries an RLE grid spanning that district's bounding box, with terrain facts only for cells owned by the lit district and unknown runs everywhere else.
- Choose the overview resolution adaptively from a fixed kilometre ladder so the section stays bounded; derive the district bounds from the exact ownership raster, not the smoothed display outlines; keep the existing 41×41 one-kilometre window as the live-sight frame.
- **BREAKING**: bump the `area_map` schema from 3 to 4. Wilderness bodies gain a required `district` field (`null` or the overview object); grid, instance and interior bodies keep their current shape under the new version.
- Render the overview behind the local window in the wilderness travel stage and the area-map drawer, in a dim explored style, clipped out of the 41×41 window so coarse terrain never bleeds into unrevealed fine cells or double-blends with the window fog.
- Change fine-window styling to distinguish **live sight** from **explored**: cells inside the supplied ground radius stay bright; every other revealed cell, whether already walked or only revealed by the lit district, uses one explored style.
- Add a symbolic whole-district fit state to the travel camera and a district stop to the area-map drawer, fitting the union of the overview and the local window inside the safe rectangle; the existing 18..46 px/km local ladder and all routing stay unchanged.
- Keep disclosure boundaries: the overview discloses only the lit district's terrain, never another district's cells, place identities, entities, or labels.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `wilderness-area-map-reveal`: the wilderness area map publishes a bounded coarse overview of the current lit district in addition to the 41-cell visible window.
- `webclient-map-panel-protocol`: `area_map` schema 4 adds the exact district-overview record and its bounds; wilderness schema 3 bodies are rejected.
- `webclient-area-map-view`: the view renders the district overview and uses live-sight versus explored styling for fine cells.
- `webclient-travel-map`: the travel stage paints the district overview behind the local window and keeps the same sight/explored compositing.
- `webclient-map-viewport`: the civic-area zoom stops gain a district-overview fit stop when the payload supplies one.

## Impact

- Server: `web/webclient/presentation/map_panels.py`, `web/webclient/presentation/area_map.py`, a new overview builder, exact-ownership district bounds, and protocol parity tests. The overview is cached per district, binding signature, partition fingerprint, elevation fingerprint and sight policy; no writes, no character knowledge mutation.
- Wire: `area_map` schema 4; new `district` field and constants mirrored in `web/static/webclient/js/elosern/protocol/panels/map_panels.js`.
- Client: `web/webclient-app/lib/wilderness-grid.js`, `area_map_view.js`, `travel-grid.js`, `travel-paint.js`, `travel-camera.js`, `map_stops.js`, `AreaMapView.vue`, `TravelMap.vue`, plus Node, Vitest and Storybook coverage.
- Docs: `docs/development/map-panel-protocol.md`, `web/webclient-app/AGENTS.md`, and an explicit amendment to the sight-and-fog design.
- No player command changes; no changes to lighting, reveal predicates, travel planning, or movement.
