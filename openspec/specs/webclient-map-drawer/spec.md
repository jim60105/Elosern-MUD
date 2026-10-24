# webclient-map-drawer Specification

## Purpose
Provide the production area/world map drawer with on-demand refresh, keyboard navigation and selection-aware commission pointers in the existing overlay shell.

## Requirements

### Requirement: The map drawer opens the appropriate scope and preserves session views
MapDrawer SHALL replace MapOverlay inside the existing OverlayHost shell. It SHALL expose ARIA 區域/世界 tabs with 1/2 shortcuts, a place caption and close control. Opening SHALL choose area in settlement/dungeon/interior and world in wilderness. Each tab SHALL retain its view for the session. New area views SHALL centre on current and fit adjacent nodes; new world views SHALL start at country centred on the player and fit a tracked commission within 800 km.

#### Scenario: Opening and returning to a tab
- **WHEN** the player opens in a settlement, switches tabs, pans and switches back
- **THEN** area opens first, each tab retains its own pan/zoom, and world initial fit includes an eligible tracked commission

#### Scenario: Epoch change retires prior map data
- **WHEN** the client reconnects or changes puppet
- **THEN** old map payloads, view memory and pending responses cannot appear for the new epoch

### Requirement: Map requests follow explicit scope and committed moves only while open
Opening or switching active scope SHALL request map.view for that scope; committed moves SHALL refresh it once while open. Closed maps SHALL request nothing. Adoption SHALL obey dispatcher ordering and epoch/revision rules. Each opening's world discovery baseline SHALL use its first fresh world response, never a retained cached body or a response from an earlier opening. Freshness SHALL remain independent of per-tab viewport memory.

#### Scenario: Open movement refreshes only the active map
- **WHEN** a movement commits with world selected
- **THEN** the client re-requests world once after the committed publication rather than optimistically on input or once per room/panel render

#### Scenario: Failed movement and closed drawer do not refresh
- **WHEN** a move is rejected or the drawer is closed
- **THEN** there is no new map.view caused by that move

#### Scenario: A cached reopening waits for its own fresh world baseline
- **WHEN** the client caches an unlit world body, closes the drawer, reaches a landmark while closed and reopens in wilderness before receiving its new world response
- **THEN** the cached body and unrelated same-epoch snapshots do not establish a discovery baseline, the opening's fresh lit response renders without discovery ink or announcement, and saved viewport/selection memory remains independent

#### Scenario: World first opens after the area tab
- **WHEN** an opening starts on area and later selects world with a retained world cache
- **THEN** only area was requested initially, the world tab's own fresh response establishes the opening baseline without replay, and the cache cannot qualify a world discovery

#### Scenario: Closed or retired requests cannot qualify a new opening
- **WHEN** a response completes after close, during a later opening waiting for its own response, or after transport generation or epoch retirement
- **THEN** it cannot qualify the later opening's baseline or reveal; existing cache/admission rules remain in force, unrelated map caches are not cleared to implement freshness, and retired view memory and pending requests remain unusable

#### Scenario: Freshness requires the requested map publication and settled action
- **WHEN** an opening request receives its action result before the matching committed map publication, its publication before the result, a partial multipart transfer, a failure or an unavailable map body
- **THEN** only the successfully settled request with a completely adopted available world body establishes the baseline; arbitrary revision changes, cached-body clones and partial transfers cannot qualify it, and no polling or retry queue is introduced

#### Scenario: A committed move is observed while opening readiness is pending
- **WHEN** a movement commits before opening readiness and its active-scope refresh follows the opening response in either supported action-result/body order
- **THEN** the opening response establishes a silent baseline; an unlit baseline followed by the movement refresh's eligible newly lit district reveals once without remounting, while a discovery already included in the first fresh baseline remains silent; normal dispatcher admission and single-refresh behavior remain unchanged

### Requirement: Floating map chrome avoids selected details
The map SHALL fill the drawer with a floating minus/stop/plus/recentre/full-map/legend pill, top-left quest dropdown and bottom-left scale bar. Selection SHALL open an approximately 360 px right detail drawer; pill and HTML edge pointers SHALL move left of it. Offscreen quest pointers SHALL be keyboard reachable, stack by distance and collapse beyond three into ＋n. Quest list and detail SHALL mirror permitted map facts as text.

#### Scenario: Offscreen pointers exceed three
- **WHEN** four or more accepted commissions point offscreen with a detail drawer open
- **THEN** the visible pointers are distance-ordered, show at most three plus ＋n, avoid the drawer and retain keyboard access through the quest list

### Requirement: Map keyboard and pointer interaction remains modal and accessible
Drag SHALL pan, wheel SHALL zoom continuously, click SHALL select a place/district/commission, and adjacent 前往 SHALL submit existing explore.move. Arrows SHALL pan; plus/minus SHALL jump stops; C SHALL recentre; 0 SHALL fit all. Escape SHALL close legend, then selected details, then the map, with final focus restored to the opener. Background game commands SHALL not consume map keys.

#### Scenario: Escape unwinds one layer
- **WHEN** legend and selected details are open
- **THEN** the first Escape closes legend, the second details and the third map, without passing a movement or menu key to the game

#### Scenario: Selected adjacent exit is activated
- **WHEN** a real panel supplies a current adjacent move descriptor
- **THEN** the drawer forwards its exact existing explore.move intent and never infers a route or moves to a remote marker

### Requirement: The old full-map lattice has no remaining consumer
After drawer and minimap cutovers the old MapOverlay, overlay pitch branch, cellSize/rank-compressed projection and obsolete map_view path SHALL be removed with all callers, tests and stories migrated. No compatibility alias or fallback overlay SHALL remain.

#### Scenario: Clean production cutover
- **WHEN** the normal map opener and minimap run after the new drawer is integrated
- **THEN** they render their new real components without importing or executing the removed overlay lattice path

### Requirement: Area view memory resets on coordinate-frame changes
Area pan/zoom and selection SHALL be retained only while the authoritative map_id and frame key/unit match. A map or coordinate-frame transition SHALL clear incompatible selection/view state and fit the new current node and adjacency; world view remains independent and all memory clears on epoch retirement.

#### Scenario: Gate and interior transitions change frames
- **WHEN** an active area tab moves city to wilderness to interior, or from one settlement to another
- **THEN** each changed map/frame initializes the correct metre, kilometre or radial view centred on current adjacency instead of reusing the previous coordinates

### Requirement: The drawer current marker makes one truthful position claim
The area drawer SHALL keep one concentric, decorative current-location glyph, the shared node glyph's here-seal, with readable labels and visible incident connector segments. The world view SHALL likewise show one current-position marker, the shared world player glyph. Decoration SHALL have no separate identity, accessible label, pointer action or fabricated position. The minimap island SHALL draw its current node with the same here-seal at its uniform scale, not a separate design.

#### Scenario: Current marker meets a path
- **WHEN** the area map shows connectors in several directions around current
- **THEN** its ring stays concentric, clear of labels and does not obscure the connectors or create a second selectable place

#### Scenario: The island's current marker is the drawer's
- **WHEN** the island and the area drawer draw the same current node
- **THEN** both draw one glow, one ring and one seal dot with the shared here-seal's base radii. The island's glyph group carries its uniform island scale, and neither surface draws a second current shape.

### Requirement: Every map surface draws a shared map concept from its one glyph source
All map surfaces (island, area map including wilderness cells, world map, both legend tabs) SHALL share one icon set. Each shared concept SHALL have exactly one definition owning its shapes, paint, stroke and dash styling, and states. Every surface, including a new one, SHALL render it from that definition, with no private redraw, copy or approximation. A surface MAY set its own uniform scale applied to the whole glyph, and SHALL NOT differ otherwise.

#### Scenario: The shared concepts are enumerated
- **WHEN** the shared icon set is listed
- **THEN** it consists of the following families:
  - area/minimap node family: current location, visited place, seen-but-unvisited place, adjacent travel halo and gateway arch;
  - area ink family: road casing and core (walked, frontier and travel variants) and the commission diamond;
  - world point family: player position, district landmark, place by kind (settlement, capital, harbour, hidden) and exact commission pin with its tracked halo;
  - world ink family: land, lit wash, the unlit hatch pattern and its hatch line, lit and unlit district strokes, nation border with casing, walked trail with casing, and the approximate-commission ring.
- **AND** the island's rim edge-direction markers (the diamond, its landmark ring and the gateway stub arrow) are not map-place concepts. They point toward places beyond the canvas edge, no other surface draws them, and they belong to the island alone.

#### Scenario: Surfaces differ only by uniform scale
- **WHEN** any two surfaces draw the same concept in the same state
- **THEN** after dividing out each surface's own uniform scale, their shapes, path data, radii, fills, strokes, stroke widths, dash patterns and state variants are identical
- **AND** a surface's scale is applied to the glyph as a whole (for example a transform on its group), never to radii alone, so stroke widths and dash patterns shrink or grow in proportion

#### Scenario: The minimap and the area map draw the same node
- **WHEN** the minimap island and the drawer's area tab both draw the current node, a visited node, an unvisited node, a node with a move action, and a non-current gateway node
- **THEN** each pair differs only by the two surfaces' uniform scales, the island applies no paint override, and the island draws no shape the area map does not: no gold landmark ring, no separate actionable disc and no outline arch with feet

#### Scenario: A wilderness cell draws the shared node glyph
- **WHEN** the area map draws a wilderness layer whose nodes are cell rectangles, with the current cell, a gateway cell and a commission cell
- **THEN** the current and gateway marks inside the cells are the shared here-seal and gate arch, and the commission mark is the shared commission diamond
- **AND** each is drawn at one cell-layout uniform scale, with no private seal radii, arch path or diamond path

#### Scenario: The legend's road and commission samples come from the area map's source
- **WHEN** the area legend draws 走過的路, 看見但未走過的路 and 委託目的地
- **THEN** the road samples carry the area map's own shared road classes and rules, the commission sample is the shared commission diamond, and the drawer holds no road or commission paint values of its own

#### Scenario: The unlit hatch pattern has one definition
- **WHEN** the world map and the world legend each need the unlit hatching
- **THEN** both instantiate the same hatch pattern definition (tile size, rotation and hatch-line rule), each under its own unique element id, and neither declares the pattern geometry itself

#### Scenario: The world map's point glyphs come from one definition
- **WHEN** the world map draws the player, a district landmark, each place kind and an exact commission, tracked and untracked
- **THEN** each glyph's shapes and paint come from the shared world point definition, scaled as a whole by the UI scale, and the shared world ink definition supplies the land, wash, hatching, district, nation, trail and approximate-ring strokes

#### Scenario: A changed glyph changes every surface at once
- **WHEN** the single definition of a shared concept changes, for example the gate arch path or the road core colour
- **THEN** every map and legend that shows that concept renders the change with no second edit

### Requirement: Map legend samples are drawn by the map they explain
Each map-drawer legend tab SHALL draw every sample with the same shared definitions as the map it explains, at the map's base glyph size multiplied by the UI scale, beside its existing text label. CSS boxes, borders, gradients, clip-paths or copied paint values that imitate a glyph SHALL NOT be used.

#### Scenario: The area legend lists the area map's marks
- **WHEN** the player opens the legend on the area tab
- **THEN** it shows the following, each from the shared area definitions:
  - 目前位置 (current);
  - 到過的地點 (visited);
  - 看過，尚未到訪 (seen, with the dashed seen paint);
  - 相鄰，可前往 (a visited node with the travel halo);
  - 城門與出入口 (a visited gateway arch);
  - 走過的路 and 看見但未走過的路 (the shared road casing and core, walked and frontier);
  - 委託目的地 (the shared commission diamond).

#### Scenario: The area legend gate is the map's gate
- **WHEN** the legend is open on the area tab while the area map shows a gateway node, as a point node in the Altoria settlement fixture or as a wilderness cell
- **THEN** the legend's gate sample has the same arch path data as the map's gate glyph, and no CSS-drawn legend icon remains

#### Scenario: The world legend uses the world map's glyphs and ink
- **WHEN** the player opens the legend on the world tab
- **THEN** it shows the following:
  - 目前位置, 分區地標, 城鎮與地點 (the settlement place) and 委託目的地 (the commission pin), drawn by the shared world point glyph;
  - 已探明的分區 (lit wash and lit stroke), 未探明的分區 (land, the shared hatch pattern and dotted unlit stroke), 國界, 走過的足跡 and 委託大致方位 (the approximate ring), drawn with the shared world ink.
- **AND** the landmark spire and commission pin paths are identical to the map's
- **AND** a lit-district sample's computed stroke equals the map's lit district stroke

#### Scenario: The approximate ring fits its sample box
- **WHEN** the world legend draws 委託大致方位
- **THEN** its ring has radius 14, so it fits the 32-unit sample. On the map this ring's radius comes from the commission's data, with a 16 px minimum, so it is not a fixed glyph size. Its stroke and fill are the map's.

#### Scenario: Legend samples scale with the interface
- **WHEN** the UI scale changes
- **THEN** every sample box is 32 units at scale 1, multiplied by the UI scale, and each glyph scales as a whole with its strokes and dashes. Each label stays at the drawer's legend type step.
