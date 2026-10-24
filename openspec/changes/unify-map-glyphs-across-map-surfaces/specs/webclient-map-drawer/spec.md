## ADDED Requirements

### Requirement: Every map surface draws a shared map concept from its one glyph source
All map surfaces (the island, the area and world maps, and both legend tabs) SHALL share one icon set. Each shared concept SHALL have exactly one glyph definition owning its geometry and paint, and every surface, including any new one, SHALL render the concept from it, changing only uniform scale, state, selection and position. No private redraw or approximation SHALL exist outside the named exceptions in the scenarios below, and each exception SHALL reproduce its map's exact values.

#### Scenario: The shared concepts are enumerated
- **WHEN** the shared icon set is listed
- **THEN** the area/minimap node family is: current location, visited place, seen-but-unvisited place, adjacent travel halo and gateway arch
- **AND** the world point family is: player position, district landmark, place by kind (settlement, capital, harbour, hidden) and exact commission pin with its tracked halo
- **AND** the world ink family is: land, lit wash, unlit hatching, lit and unlit district strokes, nation border with casing, walked trail with casing, and the approximate-commission ring

#### Scenario: The named exceptions are enumerated
- **WHEN** the not-yet-unified marks are listed
- **THEN** they are:
  - the area map's wilderness-cell here-seal (r13/9/5) and 7-unit gate, which are inset in a wilderness cell rectangle;
  - the area road casing and core strokes;
  - the area commission diamond;
  - the unlit hatch `<pattern>` element, which the world map and the world legend each declare around the shared hatch-line ink rule.

#### Scenario: Named exceptions reproduce the map's exact values
- **WHEN** the area legend draws its road and commission samples, or the world legend declares its hatch pattern
- **THEN** each sample's path, stroke, fill and pattern geometry equal the map's own values for that mark

#### Scenario: The minimap and the area map draw the same node
- **WHEN** the minimap island and the drawer's area tab (outside a wilderness cell) both draw the current node, a visited node, an unvisited node, a node with a move action, and a non-current gateway node
- **THEN** each pair has identical shapes, so circle radii and arch path data match after the island's uniform marker scale is removed, and the island applies no paint override to them
- **AND** the island draws no shape the area map does not: no gold landmark ring, no separate actionable disc and no outline arch with feet

#### Scenario: The world map's point glyphs come from one definition
- **WHEN** the world map draws the player, a district landmark, each place kind and an exact commission, tracked and untracked
- **THEN** each glyph's shapes and paint come from the shared world point definition, and the shared world ink definition supplies the land, wash, hatching, district, nation, trail and approximate-ring strokes

#### Scenario: A changed glyph changes every surface at once
- **WHEN** the single glyph definition of a shared concept changes, for example the gate arch path
- **THEN** every map and legend that shows that concept outside the named exceptions renders the change with no second edit

### Requirement: Map legend samples are drawn by the map they explain
Each map-drawer legend tab SHALL draw its node, world point and world ink samples with the same shared glyph definitions and ink rules as the map it explains. Its area road and commission samples SHALL use the area map's exact values. Samples SHALL be SVG at the map's 1:1 glyph size multiplied by the UI scale, beside their existing text labels. CSS boxes, borders, gradients or clip-paths that imitate a glyph SHALL NOT be used.

#### Scenario: The area legend lists the area map's marks
- **WHEN** the player opens the legend on the area tab
- **THEN** it shows the following, each from the shared node glyph unless noted:
  - 目前位置 (current);
  - 到過的地點 (visited);
  - 看過，尚未到訪 (seen, with the dashed seen paint);
  - 相鄰，可前往 (a visited node with the travel halo);
  - 城門與出入口 (a visited gateway arch);
  - 走過的路 and 看見但未走過的路 (the area road casing and core, walked and frontier);
  - 委託目的地 (the area commission diamond).

#### Scenario: The area legend gate is the map's gate
- **WHEN** the legend is open on the area tab while the area map shows a non-cell gateway node, for example in the Altoria settlement fixture
- **THEN** the legend's gate sample has the same arch path data as the map's gate glyph, and no CSS-drawn legend icon remains

#### Scenario: The world legend uses the world map's glyphs and ink
- **WHEN** the player opens the legend on the world tab
- **THEN** it shows the following:
  - 目前位置, 分區地標, 城鎮與地點 (the settlement place) and 委託目的地 (the commission pin), drawn by the shared world point glyph;
  - 已探明的分區 (lit wash and lit stroke), 未探明的分區 (land, hatching and dotted unlit stroke), 國界, 走過的足跡 and 委託大致方位 (the approximate ring), drawn with the world ink rules.
- **AND** the landmark spire and commission pin paths are identical to the map's
- **AND** a lit-district sample's computed stroke equals the map's lit district stroke

#### Scenario: The approximate ring fits its sample box
- **WHEN** the world legend draws 委託大致方位
- **THEN** its ring has radius 14, below the map's 16 px minimum, so it fits the 32-unit sample, and its stroke and fill are the map's

#### Scenario: Legend samples scale with the interface
- **WHEN** the UI scale changes
- **THEN** every sample box is 32 units at scale 1, multiplied by the UI scale; each glyph keeps its map proportions, and each label stays at the drawer's legend type step

## MODIFIED Requirements

### Requirement: The drawer current marker makes one truthful position claim
The area drawer SHALL keep one concentric, decorative current-location glyph, which is the shared node glyph's here-seal, with readable labels and visible incident connector segments. The world view SHALL likewise show one current-position marker, drawn by the shared world player glyph. Decoration SHALL have no separate identity, accessible label, pointer action or fabricated position. The minimap island SHALL draw its current node with the same here-seal glyph as the area drawer and SHALL NOT keep a separate current marker design.

#### Scenario: Current marker meets a path
- **WHEN** the area map shows connectors in several directions around current
- **THEN** its ring stays concentric, clear of labels and does not obscure the connectors or create a second selectable place

#### Scenario: The island's current marker is the drawer's
- **WHEN** the island and the area drawer draw the same current node
- **THEN** both draw one glow, one ring and one seal dot at the shared here-seal's radii (the island scales them by its uniform marker scale), and neither draws a second current shape
