# Minimap Auto-Scale Design

Date: 2026-10-22
Status: Implemented (all five changes in §9). Corrective follow-up `fix-map-design-integration-gaps` is merged; complete evidence verification remains with CI.
Amends: [World Map Scale and Metric Settlement](2026-10-21-world-map-scale-design.md) §11 for the minimap island only.
Follow-up: the separate full-map drawer design and its thirteen changes are integrated. The integration corrections are recorded in [fix-map-design-integration-gaps](../../../openspec/changes/archive/2026-10-24-fix-map-design-integration-gaps/design.md).

## 1. Problem

After the metric settlement cutover, the minimap island usually shows only the current node.

The browser model sets the lattice cell to the smallest positive in-view coordinate delta (`cellSize` in `web/static/webclient/js/elosern/local_map.js`). Metric coordinates contain deltas such as `3500` vs `3480` or `3000` vs `3010`, so around Altoria's central plaza the cell becomes 10 m. Each cell draws at a minimum 58 px pitch, so a 1 km street spans about 100 cells, more than 5,000 px. The island shows a fixed 240 px window and `ISLAND_MIN_SCALE = 1` forbids shrinking. Adjacent exits fall outside the window.

Storybook fixtures use unit coordinates, so no story reproduces the failure.

Two payload facts also matter:

- A registered gate's cross-layer node is placed one renderer cell (possibly 10 m) from the current node (`_free_slot` in `web/webclient/presentation/local_map/grid.py`). It is not a physical position.
- The grid payload sends star edges from the current node to every in-view node. Adjacent edges carry a direction label; two-hop edges carry an empty label. Drawing them as roads shows routes that do not exist.

## 2. Goal and scope

The minimap has no manual zoom, so its scale must be automatic and usable in every location. The player's decision is which exit to take next. The island must therefore always show the current node and every adjacent (one-hop) exit, with legible labels, and stay visually stable between moves.

Included: a client projection for the island, a gateway field on `local_map` nodes, island rendering changes, fixtures, stories, and tests.

Excluded: the full-map overlay (it keeps the existing lattice path until its own redesign), new map data such as whole-area or world maps, server-side display coordinates, and the `instance`/`interior` radial graph variant, which is unchanged.

## 3. Projection

The island canvas is 240 user units square with its centre at (120, 120). The current node is drawn at the centre. All bearings are exact.

### 3.1 Constants

| Name | Value | Meaning |
| --- | --- | --- |
| `R_MAX` | 88 | Largest exit-marker centre radius; the outer band holds labels at the 16 px floor |
| `R_MIN` | 36 | Smallest exit-marker centre radius; keeps exit markers and labels clear of the current marker |
| Level ladder | 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000 | Metres per 100 user units; adjacent levels differ by at most 1.67x |
| Default level | 100 | Used when no node provides a distance |

### 3.2 Node tiers

- `current`: the payload's current node.
- `exit`: a node joined to the current node by an edge with a non-empty label. Locked exits (`action: null`) are still exits.
- `context`: any other in-view node on the same layer (two-hop nodes).
- Cross-layer nodes (a node whose id layer prefix differs from the current node's, such as a `wild:` gate target in a grid payload) are never drawn as nodes; see §4.

### 3.3 Uniform mode (default)

1. Compute each exit's Euclidean distance `d` from the current node in payload metres and take `d_max`.
2. Choose the smallest ladder level `M` with `d_max * 100 / M <= R_MAX`.
3. Hysteresis: keep the previous level when it still fits every exit and is at most one ladder step coarser than the ideal level. Reset the previous level when the current node's map changes (its node-id map key differs).
4. Screen radius is `r = d * 100 / M`.

### 3.4 Compressed mode

Use compressed mode when uniform mode would place the nearest exit at `r < R_MIN`, or when no ladder level fits `d_max` (above about 4.4 km).

`r(d) = R_MIN + (R_MAX - R_MIN) * ln(d / d_min) / ln(d_max / d_min)` for `d >= d_min`, where `d_min` and `d_max` range over exits. For context nodes closer than `d_min`, `r = R_MIN * d / d_min`. The mapping is monotonic, so distance order is preserved. When all exits share one distance, place them at `0.75 * R_MAX`.

### 3.5 Edge cases

- No exits: choose the level from the drawable context nodes; with none, use the default level.
- Zero distance: an exit with no defined bearing takes an angle assigned in payload order, starting north and spaced evenly.
- Overlapping exits: when two exit markers at similar radii would overlap, spread them symmetrically about their mean bearing, by at most ±20°.
- Context nodes use the same mapping. Omit any that land outside the canvas. They are drawn as small background dots with no connecting line.
- Remembered remote nodes keep the existing edge-direction markers.

### 3.6 Worked examples

- Altoria central plaza: exits at about 850–1,090 m select `M = 1500`, placing them at r ≈ 57–72 in uniform mode.
- Wilderness: eight neighbours at 1 km and 1.414 km select `M = 2000`, placing them at r = 50 and 71 in uniform mode.
- An 80 m exit beside a 1.2 km exit triggers compressed mode.

## 4. Gateways

The island shows the gate, never the far-side layer's nodes. Standing in a city, the player sees the gate but not wilderness cells; standing in the wilderness, the player sees the adjacent city gate but not city streets.

### 4.1 Payload field

Every `local_map` node gains `gateway`: either `null` or `{ "leads_to": <string> }`.

- A grid room hosting a registered gateway carries the far-side wilderness region name (the existing `_wild_region_label` / `_gateway_far_side_label` helpers).
- A wilderness payload's adjacent grid gateway node carries the settlement name.
- Every other node carries `null`.

The server validator (`web/webclient/presentation/local_map/validate.py`) and the browser validator (`web/static/webclient/js/elosern/protocol/panels/local_map.js`) accept the field under their exact-field checks together. `leads_to` is a non-empty string bounded by `LOCAL_MAP_MAX_STRING`. `schema_version` stays 1: server and client ship from one repository in one deployment, and no compatibility alias is kept.

### 4.2 Rendering

- A gateway node draws a gate glyph with its room label and a second line, `通往 <leads_to>`.
- When the current node is a gateway, the server still sends the cross-layer target node with its `move` action. The client does not draw it as a node. It draws an exit stub: an arrow on the exit ring at that node's bearing from the current node, labelled `通往 <leads_to>` and activating the node's move action.
- Cross-layer nodes take part in no scale calculation, so the renderer-local slot offset no longer affects the projection.

## 5. Scale-true background

- Uniform mode: grid dots are spaced `M / 5` metres apart (20 user units) and anchored to integer multiples of that spacing in world metres, not to the current node. Moving slides the dots with the ground; the existing pan transition moves them too, replacing the stationary dot field. A scale caption states the spacing, for example `格距 300 m`.
- Compressed mode: the dot field is replaced by concentric distance rings at readable distances (for example 100 m, 300 m, 1 km), placed with the same mapping and labelled. The change from dots to rings signals compression by shape and text, not by colour alone.

## 6. Architecture

### 6.1 Server

`web/webclient/presentation/local_map/grid.py` and `wilderness.py` populate `gateway` on every node. No other payload change.

### 6.2 Browser model

`web/static/webclient/js/elosern/local_map.js` passes `gateway` through to the node model unchanged. `cellSize` and the lattice placement remain for the overlay.

### 6.3 Projection module

New pure module `web/webclient-app/lib/minimap_projection.js`, with no Vue or DOM access.

- Input: model nodes and edges, the previous level (or `null`), and the canvas constants.
- Output:
  - `mode`: `"uniform"` or `"compressed"`.
  - `level`: the chosen `M`, for the next call's hysteresis.
  - `nodes[]`: `{ id, x, y, tier, gateway }` in user units.
  - `exitStubs[]`: `{ bearing, label, action }`.
  - `grid`: dot spacing and world anchor offset in uniform mode, or the ring list in compressed mode.
  - `scaleLabel`: the scale caption text.

### 6.4 Renderer

- In `MapLattice.vue` and `use-map-lattice-geometry.js`, the `canvasSize` (island) branch consumes the projection. Remove `islandWindow`, `windowed`, and the island pitch iteration. The `canvasSize == null` overlay branch is unchanged.
- `LocalMap.vue` holds the previous level as presentation state.
- The dot field is generated from the projection's spacing and anchor instead of a fixed SVG pattern; compressed mode draws the rings and their labels.
- Only exit edges are drawn as routes.
- Label placement tries eight candidate positions per marker, in priority order: exits, then the current node, then context nodes. An exit label that fits nowhere is truncated to `labelMax` and drawn with a leader line, never dropped. A context label that fits nowhere is omitted. The full name always remains in the accessible name.

### 6.5 Transitions

The FLIP pan in `web/webclient-app/lib/map_pan.js` assumes equal scales before and after a move. When the level and mode are unchanged it applies as now, moving the dots as well. When either changes, `full` motion uses a short crossfade, and `reduced`/`off` switch immediately.

Implementation note (animate-minimap-scale-transitions): `scaleKey`/`islandMotion` in `map_pan.js` decide pan, crossfade or switch, including a replacement that keeps the current node. The crossfade (`composables/use-island-dissolve.js`) lays an inert, aria-hidden copy of the previous drawing, opaque canvas included, over the committed one and fades it over `--motion-base` on `--ease-enter`. Pixels both frames share, such as the centred current marker, the axis cross and the frame, therefore stay still. A cross-layer gateway step follows the same decision and never synthesises a shared frame.

## 7. Accessibility

- Mode differences use shape and text in addition to colour.
- Scale captions and `通往` labels respect the 16 px floor.
- An exit stub is a focusable button whose accessible name is `往 <leads_to> 移動`.
- Scale changes follow the effective `motionLevel`.

## 8. Verification

- Unit tests for `minimap_projection.js`: level selection, hysteresis keep and reset, the compression threshold, monotonic mapping with unchanged bearings, cross-layer exclusion, exit stubs, overlapping-exit spreading, dot anchoring, and every edge case in §3.5.
- Metric fixtures built from the authored coordinates in the parent design (Altoria's 21 nodes, Ciaran's 10 nodes), plus a wilderness 3x3 neighbourhood, Altoria's south gate, and an extreme distance ratio. Existing unit-coordinate fixtures remain for the overlay.
- Storybook: metric `World/LocalMap` stories, one per fixture, whose `play` functions assert that every exit lies inside the canvas and no two exit markers overlap.
- Browser: capture the stories with agent-browser; after implementation, walk south gate → wilderness → back in the real client.
- Server tests: `gateway` values for a city gate room, an adjacent city gate in the wilderness, and an ordinary node; validator rejections for malformed values.
- OpenSpec: modify the `webclient-local-map` requirements that describe the island window, the stationary dot field, and cross-layer gate nodes.

## 9. Proposed changes

This design was turned into five proposal-only OpenSpec changes on `master`, each
sized at 8 hours or less for a mid-tier implementing worker. Apply them strictly
in the listed order; each change's delta requirements come from the completed
predecessor.

| Order | Change | Hours | Depends on | Scope |
| --- | --- | ---: | --- | --- |
| 1 | `add-local-map-gateway-metadata` | 6.5 | — | `gateway` payload field, server and browser validators, model pass-through, fixture cutover |
| 2 | `compute-minimap-auto-scale-projection` | 7.5 | 1 | Pure `minimap_projection.js`: uniform and compressed modes, level ladder and hysteresis, exit stubs, background geometry, every §3.5 edge case |
| 3 | `render-auto-scaled-minimap-island` | 8 | 2 | Island renderer cutover, scale-true dot field and distance rings, five metric Storybook fixture families |
| 4 | `label-minimap-exits-and-gateways` | 7.5 | 3 | Eight-position label placement, gate glyphs, accessible exit-stub controls |
| 5 | `animate-minimap-scale-transitions` | 7 | 4 | Scale-aware motion, inherited HUD contract amendment, complete gateway visual journey |

Total: 36.5 hours. Every change requires Storybook `play` assertions,
agent-browser inspection of the affected stories, and focused single-file or
single-class tests with the shard, traceability, and contract gates. The final
change adds the real-client walk south gate → wilderness → back.

## 10. Alternatives rejected

- Quantising the lattice cell and relaxing the island minimum scale: smallest change, but snapping shifts bearings, merges nearby nodes, and cannot compress extremes.
- Server-computed minimap display coordinates: moves presentation into the server against the parent design's rule that server coordinates are authoritative and display coordinates are presentation-only.
