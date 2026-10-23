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
The area drawer SHALL retain one concentric, decorative current-location ring with readable labels and visible incident connector segments. The world view SHALL likewise show one current-position marker. Decoration SHALL have no separate identity, accessible label, pointer action or fabricated position, and island marker behavior SHALL remain unchanged.

#### Scenario: Current marker meets a path
- **WHEN** the area map shows connectors in several directions around current
- **THEN** its ring stays concentric, clear of labels and does not obscure the connectors or create a second selectable place
