# World Map Drawer Design

Date: 2026-10-22
Status: Implemented (all thirteen changes in §9). The corrective follow-up [fix-map-design-integration-gaps](../../../openspec/changes/archive/2026-10-24-fix-map-design-integration-gaps/design.md) is merged; complete evidence verification remains with CI.
Depends on: [Minimap Auto-Scale](2026-10-22-minimap-auto-scale-design.md) for the `gateway` node field.
Amends: [World Map Scale and Metric Settlement](2026-10-21-world-map-scale-design.md) §6 (terrain and political geography).
Prototype: `docs/design/world-map/` (Storybook `Design/WorldMap`, layout option A).

## 1. Goal

Replace the full-map overlay with a map drawer that has two tabs:

- **區域 (area)**: the whole current settlement, dungeon, or interior under fog of war, or the local wilderness neighbourhood.
- **世界 (world)**: the continent, revealed district by district as the player reaches landmarks.

Maps are scarce in the setting; civilians do not own detailed continental maps. The world map therefore starts nearly empty and grows with exploration. Long journeys take weeks of game time, so the world map earns its place during wilderness travel and when a commission points somewhere far away.

## 2. Current state

The overlay (`web/webclient-app/components/MapOverlay.vue`) receives the same `local_map` payload as the minimap: the current node, its two-hop neighbourhood, gates, and remembered gateways, at most 64 nodes. It has no whole-area or continental data. It projects through the smallest-delta lattice, which the metric cutover broke the same way it broke the minimap.

Map knowledge (`world/rules/map_knowledge.py`) records visited node IDs only, with first and last tick. Every wilderness cell entered is a visited `wild:` node.

The wilderness model has no elevation data. Reachability comes from the mainland polygon, a one-cell summit-ridge wall with three passes, impassable rivers with fords, and terrain speed by region.

## 3. Geography changes

These amend the parent design's §6. They are real terrain, not display layers.

### 3.1 Border river

Add a river, provisionally named 界河, to `WATERWAY_ROUTES` in `world/maps/wilderness_provider.py`.

- Course, in wilderness cells: rises on the central range's western flank near `(1300, 1410)` and flows west, meandering between Y 1290 and Y 1410, to the west coast near `(170, 1290)`. Intermediate bends follow the shape `(1100, 1350)`, `(900, 1380)`, `(650, 1310)`, `(400, 1340)`; the exact vertices are authoring discretion inside that band, provided the mouth is on the coast and the source meets the mountain corridor.
- Three fords: the principal one near `(823, 1366)` on the line between the Altoria and Valhalla capitals, plus one upstream and one downstream. Every other river cell is impassable on foot.
- The river is the Altoria–Valhalla border.

### 3.2 Northern deep forest edge

Move the northern deep forest's southern edge from the straight line Y = 2200 to a meandering line averaging about Y 1920, so the forest covers about one fifth of the land. The forest is narrative wilderness that humans and beastfolk do not penetrate; it adds no movement block and keeps ordinary forest travel speed. The summit ridge keeps its current northern limit.

### 3.3 Political territory

Every land cell has a nominal nation:

- East of the summit ridge: Grandia, including the eastern half of the central range and the eastern deep forest.
- West of the ridge and south of the border river: Altoria, including the western flank of the central range.
- West of the ridge and north of the border river: Valhalla, including the western deep forest.

The resulting land shares are about Grandia 43%, Altoria 30%, Valhalla 27%. This matches the setting's 38 : 27 : 25 ratio once the formerly neutral 10% is shared out. The setting's percentages describe effective rule; the central range and deep forest are nominal claims. Elven valleys lie inside nominal territory and remain outside any nation's administration in narrative. The map does not mark nominal versus effective control.

National borders are derived from the ridge and the border river; no separate political polyline is authored. Inside the deep forest the map draws no national border line.

### 3.4 Terrain classifier

`region_for_coordinates` keeps its region keys but changes boundaries: the western hills / northwest highland forest boundary becomes the border river, and the deep forest boundary becomes the line in §3.2. Each region's `nation_key` follows §3.3; `central_mountains` and `north_deep_forest` gain nation keys or are split per side as the implementation requires. Content keyed by region (monster placement, species hunts) must be re-checked.

### 3.5 Existing anchors

- 咆哮王城 `(780, 1910)` sits about 10 km south of the forest edge.
- 幽月谷村 `(1410, 2150)` falls inside the deep forest, consistent with a hidden elven valley.
- 永夜迷宮 `(900, 2350)` stays in the deep forest under nominal Valhalla claim.
- All nine anchors and six harbour sites must remain on land and reachable.

## 4. Map districts and landmarks

### 4.1 Registry

New frozen lore module `world/lore/map_districts.py`. Each district has exactly one landmark:

| Field | Meaning |
| --- | --- |
| `key` | Stable district key |
| `district_name_zh` | District display name |
| `landmark_name_zh` | Landmark display name |
| `landmark_node` | Canonical node ID: `wild:elosern:<x>:<y>` or `grid:<map>:<x>:<y>` |
| `kind` | `voronoi` or `region` |
| `region_key` | For `region` districts only: the terrain region whose cells form the district |

Validation: landmarks are on walkable land and reachable; grid landmark nodes exist; Voronoi landmarks are not closer than a minimum spacing; every land cell belongs to exactly one district.

### 4.2 Partition

- `region` districts take every cell of their terrain region. The northern deep forest is one region district, deliberately hard to light. Its single landmark lies deep inside, near the forest's centre by the north coast (for example 古樹之心 near `(1250, 2420)`), about 500 km from the forest edge.
- `voronoi` districts partition all remaining land by walking distance from their landmarks on a 5 km raster (540 × 540), using 8-connected moves with diagonal cost √2. The summit ridge, rivers, sea, and national borders are barriers; passes and fords are open for movement but national borders stay closed for the partition, so no Voronoi district straddles a border.
- Target size about 200 km across, which gives roughly 110–130 districts in all.
- An offline tool computes the partition and the smoothed outlines. It stores them as run-length-encoded frozen data in version control. A test recomputes the partition and compares it with the stored data. The runtime never recomputes.

### 4.3 Lighting

A district is lit when its landmark node appears in the player's map-knowledge visited record. No new persistent state is introduced and the knowledge writer is unchanged.

On an arrival whose node is a landmark not previously in the record, the movement narrative adds `已探明：<district>`.

### 4.4 Visibility rules

- Always shown (common knowledge): the simplified coastline, national borders, nation names.
- Shown for lit districts: name, outline, terrain wash, rivers, ridge, roads, and the non-hidden places inside.
- Shown for unlit districts: outline only, drawn hatched with a dotted border and labelled `未探明`.
- Capitals and other places are not common knowledge; they appear when their district is lit or after a visit.
- Hidden places (elven villages, dungeons) appear only after a visit, even in a lit district.
- The trail of visited wilderness cells is always shown.

## 5. Server panels

### 5.1 Request model

A new action `map.view` with payload `{ "scope": "area" | "world" }` publishes the matching panel through the existing action and panel registries. Panels are not pushed on every move. While the drawer is open, the client re-requests the active scope after each committed move.

### 5.2 `area_map`

- Grid layer: from the settlement's sparse graph, every visited node plus every node adjacent to a visited node; roads whose two ends are known and at least one end is visited; metre coordinates; `visibility` of `current`, `visited`, or `seen`; the `gateway` field from the minimap design; `move` actions on exits adjacent to the current node.
- Instance and interior layers: the same fog-of-war rule over the room graph. Rooms carry no coordinates, so the client keeps the radial layout.
- Wilderness: the 15 × 15 cell neighbourhood around the player with visited flags, `move` actions on the eight neighbours, and the current district name.
- Quest markers: a node ID for destinations on this map; a bearing and distance for destinations elsewhere.

### 5.3 `world_map`

- Common-knowledge layer: simplified coastline, national border polylines, nation names and label positions. Static and cached.
- Lit districts: ID, name, outline, landmark position, terrain wash shapes, rivers, ridge, roads, and non-hidden places. Cached per district.
- Unlit districts: outline only. Names and contents never leave the server.
- Trail: visited wilderness cells, row run-length encoded. Above a cap (initially 20,000 cells) the server downsamples to 5 km cells.
- Visited hidden places and the current position.
- Quest markers: exact coordinates when the destination's district is lit. Otherwise the server rounds the coordinates to 50 km and marks the marker `approximate`; exact coordinates never reach the browser.
- Size: the prototype's coastline, borders, and 109 outlines total about 73 KB. The implementation measures the real payload and sets a bound. This panel is exempt from the existing 64 KB `local_map` envelope. Confirm the transport carries a payload of this size; if it cannot, the panel is sent in parts.

### 5.4 Quest destination resolution

The server converts each accepted commission's destination to world coordinates:

- ANCHOR locators: the anchor's cell.
- GRID locators: the settlement's anchor cell.
- Wilderness species hunts: the point of the target region nearest the player.
- Monster sites: the site's cell.

## 6. Client

### 6.1 Layout (option A)

The map fills the drawer. A floating control pill holds `－ <stop> ＋ ⌖ 全圖 ?`, the legend is a popover from `?`, a quest dropdown sits top left, and a scale bar sits bottom left. A detail drawer about 360 px wide slides in from the right only when something is selected; the pill and edge pointers move to its left edge. The fixed three-column option B was rejected because it narrows the map to about 820 px.

### 6.2 Components

- `MapDrawer.vue`: replaces `MapOverlay.vue` inside the existing OverlayHost shell. It holds the header with the `區域` / `世界` ARIA tabs (`1` / `2`), the place caption, and the close control, and it hosts the map, pill, quest dropdown, and detail drawer.
- `AreaMapView.vue`: settlement, dungeon or interior, and wilderness neighbourhood views. Settlements use metre coordinates at one uniform scale with pan and zoom; there is no compressed mode. The dot field and scale caption follow the minimap's scale-true rule.
- `WorldMapView.vue`: layers from bottom to top: sea, land, lit terrain, unlit hatching, district borders, national borders, coastline, trail, approximate-quest circles, places and landmarks, quest markers, current position, labels, then chrome.
- `MapEdgePointers.vue`: an HTML layer of off-screen quest pointers that avoids the open detail drawer, stacks by distance, and collapses beyond three into `＋n`.
- `lib/map_viewport.js`: pure projection, pan, zoom, zoom stops, and edge clamping. It absorbs `lib/map_view.js`.

### 6.3 Zoom stops and level of detail

| Map | Stops |
| --- | --- |
| World | 大陸 (fits the whole continent for the viewport's aspect ratio), 國 (800 km), 地區 (200 km), 近郊 (40 km) |
| Settlement | 全城, 街區, 近處 |
| Wilderness | 周邊, 近處 |

The wheel zooms continuously; `＋` / `－` jump between stops.

Level of detail on the world map:

- Nation names: 大陸 and 國.
- Lit district names: views up to 1,000 km wide.
- `未探明` labels: views up to 450 km wide.
- Place names: views up to 1,000 km wide.
- The trail is a line except at 近郊, where it is drawn as cells.

Labels are never below 16 px. A lower-priority label that does not fit is hidden, not shrunk.

### 6.4 Defaults and interaction

- Opening the map selects `區域` in a settlement, dungeon, or interior, and `世界` in the wilderness. Each tab keeps its own view for the session.
- The area tab opens centred on the current node at a zoom that fits its adjacent nodes.
- The world tab opens at 國 centred on the player. When the tracked commission is within 800 km, it fits the player and the commission together.
- Pointer: drag pans, the wheel zooms, a click selects a place, district, or commission and opens the detail drawer. Adjacent exits offer `前往`, which submits the existing `explore.move`.
- Keyboard: arrows pan, `＋` / `－` zoom, `C` recentres, `0` shows the whole map. Escape closes the legend, then the detail drawer, then the map.
- The detail drawer lists every nation a district belongs to; the deep forest shows both.
- A district lit while the drawer is open plays a 600 ms ink spread from its landmark; reduced motion switches instantly.

### 6.5 Accessibility

- Lit and unlit districts differ by hatching, line style, and label as well as colour.
- An approximate commission marker is a dashed circle labelled `大致方位`.
- Edge pointers and the quest list are keyboard reachable.
- The detail drawer and quest list mirror map state as text.
- A live region announces `已探明：<district>`.

### 6.6 Removal

The old overlay lattice path (`cellSize`, the rank-compressed lattice, and the overlay pitch branch) has no remaining consumer after this change and the minimap change, and is deleted.

## 7. Verification

- Partition tool: every land cell belongs to exactly one district; no Voronoi district crosses a national border, the ridge, or a river; the deep forest is a single region district; each landmark lies in its own district and is reachable; the recomputation test matches the stored data.
- Geography: the border river is impassable except at fords; Altoria's capital can reach Valhalla's capital; every anchor and harbour site stays on land and reachable; regression checks for region-keyed monster placement and commissions after the classifier change.
- Server panels: unlit district names and contents never appear in `world_map`; approximate markers carry only 50 km precision; dungeon fog of war; the wilderness 15 × 15 neighbourhood; trail downsampling; the first-arrival `已探明` narrative.
- Client units: `map_viewport.js` projection, anchored zoom, stops, edge clamping that avoids the drawer, and level-of-detail thresholds.
- Storybook: stories for the real components covering every prototype scenario, whose `play` functions assert edge pointers, nameless unlit districts, and `前往` on exits.
- Browser: agent-browser captures; after implementation, a walk in the real client from opening the map in Altoria, through a gate, to reaching a landmark that lights a district, then following a commission pointer.

## 8. Prototype

`docs/design/world-map/` holds the approved layout prototype (option A, with option B for comparison) on mock data. Its districts are a walking-distance Voronoi over the real coastline, ridge, and rivers. It predates §3: it has no border river, keeps the Y = 2200 forest edge, and shows a softened stand-in for the old Y = 1700 classifier border. Treat it as the layout, layering, and interaction reference, not as geography.

## 9. Proposed changes

This design was turned into thirteen proposal-only OpenSpec changes on `master`,
each sized at 8 hours or less for a mid-tier implementing worker. The six scopes
above remain the groups; a group is split further wherever one change would
exceed the budget (rows 2, 4, 5, and 6). Apply them strictly in the listed
order.

| Order | Change | Hours | Depends on | Scope |
| --- | --- | ---: | --- | --- |
| 1 | `author-border-river-and-forest-edge` | 8 | — | Border river and fords, meandering forest edge, classifier and `nation_key` updates, derived national borders |
| 2 | `establish-map-districts` | 5 | 1 | Frozen district and landmark registry, canonical landmarks, knowledge-derived lighting rule |
| 3 | `compute-map-district-partition` | 8 | 2 | Deterministic 5 km walking-distance partition, exact cell ownership, frozen RLE outlines, recomputation test |
| 4 | `author-district-landmarks` | 8 | 3 | About 110–130 authored landmark and name pairs, regenerated partition data |
| 5 | `resolve-map-quest-destinations` | 5 | 1 | Shared canonical destination resolution for accepted commissions |
| 6 | `define-map-panel-protocol` | 8 | minimap 1 | Exact `area_map` and `world_map` wire contracts, on-demand snapshot semantics, bounded atomic part codec |
| 7 | `publish-area-map-panel` | 8 | 3, 5, 6, minimap 1 | `map.view`, `area_map` for grid, instance, interior, and wilderness, gateways, quest markers |
| 8 | `transport-world-map-panel` | 6 | 4, 6, 7 | Real payload measurement, finite world bounds, confirmed socket and browser delivery of the large panel |
| 9 | `publish-world-map-panel` | 8 | 2, 5, 8 | Filtered `world_map`, caches, trail encoding, approximate markers, first-arrival narrative |
| 10 | `establish-map-viewport` | 5 | — | Pure `map_viewport.js`: projection, pan, anchored zoom, stops, drawer-aware clamping |
| 11 | `render-area-map-view` | 7 | 7, 10 | Real settlement, dungeon, interior, and wilderness area views with stories |
| 12 | `render-world-map-view` | 8 | 9, 10 | Real world layers, level of detail, precision-aware markers, accessible reveal motion |
| 13 | `redesign-map-drawer` | 8 | 7, 9, 11, 12, minimap 5 | Option-A drawer shell, requests, pointers, keyboard, story work, removal of the overlay lattice |

Groups: geography is 1; districts are 2–4; server panels are 5–9; client work is
10–13. `map.view` and the panel protocol (6) are prerequisites for both panel
changes. `redesign-map-drawer` also waits for the minimap chain to finish,
because the overlay lattice it deletes has no consumer only after both changes
land. Total: 92 hours.

Every change requires Storybook `play` assertions, agent-browser inspection of
the affected stories, and focused single-file, single-class, or single-method
tests with the shard, traceability, and contract gates.

## 10. Alternatives rejected

- Revealing whole settlement maps on entry: removes exploration from dungeons and mazes.
- Full world fog with no outline: a 1 km trail is invisible against a 2,700 km continent.
- Fixed 200 km squares or hand-drawn district polygons: squares cut across ridges and coasts; polygons cost the most authoring and validation.
- An elevation model: it would also change movement cost and rendering, so it needs its own design. A future slope cost can weight the partition.
- Shipping the full geography to the client: hands the player the military map the setting withholds.
- Several landmarks per district: makes the deep forest easy to light, against its purpose.
