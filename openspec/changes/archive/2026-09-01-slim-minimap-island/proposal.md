# Slim Minimap Island

## Why

The right-rail minimap island carries the full state legend below its canvas,
duplicating what the full-screen overlay already shows, and it spends island
height on the legend instead of on the map. At the same time it shows no
position information on the layers that actually have world coordinates: the
current spec forbids a bearing mark or a coordinate figure outright. The
player asked for the legend gone from the island (map first) and for the
minimap to state direction and coordinates whenever the layer is a coordinate
layer (grid / wilderness).

## What Changes

- The minimap island no longer renders the state legend. The full-screen
  overlay keeps it unchanged (dot-chips, border-style redundancy, text
  labels).
- `MapLattice.vue` (the shared renderer) gains a `showLegend` prop (default
  `true`, legend rendered); the island passes `false` and the legend DOM is
  not mounted at all on that surface.
- New live position readout: on coordinate-bearing layers (`grid`,
  `wilderness`) the island's detail line states the current node's payload
  world coordinates as `座標 <x>,<y>` when no other node is hovered/selected,
  and the header keeps the existing `北↑ 東→` orientation marks as the bearing
  statement. On graph layers the detail line keeps its existing node
  label/visibility content and renders no coordinates. Hover/selection of
  another node keeps its existing detail behavior on every layer.
- `LocalMap.vue`'s dynamic canvas height budget drops the legend from the
  measured chrome (section list, gap count), returning that height to the
  canvas.
- The remembered-places list, the expand control, the click-body-opens-overlay
  behavior, tap-to-move, and the accessible summary stay exactly as they are —
  they are the island's interactive/keyboard surface, not legend chrome.
- Spec amendments (this is the cost of doing it legally): `webclient-local-map`
  ("The browser minimap renders states without relying on color alone" —
  legend becomes overlay-only, island budget chrome list, the "No surface
  SHALL render … a coordinate figure" clause is amended to permit exactly the
  island's two-integer current-coordinate readout on coordinate layers), and
  `webclient-contextual-hud` ("The minimap island states only its own drawing
  convention" — same amendment on the island's ban, with the graph-layer ban
  and the no-interpretation rule intact).

Out of scope: the full-map overlay's chrome (it keeps its ban on
bearings/coordinates via `the-map-settings-and-help-surfaces…` requirement,
unchanged), the server presenter, the `local_map` v1 payload (the `legend`
field stays in the payload; the island just stops rendering it), map
interaction, and any player command.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: the shared renderer's legend becomes an overlay-only
  presentation; the island's viewport budget no longer measures a legend; the
  island gains a coordinate readout on coordinate layers while the graph layer
  keeps the no-coordinate rule.
- `webclient-contextual-hud`: "The minimap island states only its own drawing
  convention" is amended — the island MAY render the current node's coordinate
  figure (two payload integers) and the north mark on coordinate layers; the
  ban stays for graph layers, distances, compass angles, and any
  interpretation-layer content.

## Impact

- Affected code: `web/webclient-app/components/MapLattice.vue` (`showLegend`
  prop), `web/webclient-app/components/LocalMap.vue` (passes `false`, budget
  measurement, detail-line coordinate part), stories
  (`World/LocalMap.stories.js`, `World/MapLattice.stories.js` if legend
  stories need the prop's knob), Vitest suites
  `web/webclient-app/tests/world/local_map.test.js`,
  `world/map_lattice.test.js`, `world/map_layout_variants.test.js`,
  `overlays/map_overlay.test.js` (legend still present on the overlay),
  browser suite `web/tests/browser/test_browser_local_map.py` (island legend
  assertions flip to legend-absent-in-island / present-in-overlay; new
  coordinate-readout assertions under the existing requirement anchors).
- No server, protocol, or store change; the payload is untouched, so the
  Node-gate renderer model (`web/static/webclient/js/elosern/local_map.js`)
  and the Python/JS validator parity contract are untouched.
- Requirement titles are MODIFIED in place (no rename), so every existing
  `@covers_requirement` anchor keeps its ID; `covers_requirement` anchors for
  the new readout live on the updated tests.
- No player-facing command changes; `docs/game/commands.md` untouched.
