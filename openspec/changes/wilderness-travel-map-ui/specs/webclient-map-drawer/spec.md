## MODIFIED Requirements

### Requirement: Every map surface draws a shared map concept from its one glyph source
Every map surface SHALL render each shared concept and named state from its single glyph definition with uniform whole-glyph scaling; travel party, neighbour, hostile and route states SHALL extend shared definitions without changing existing drawer/minimap states or copying their geometry.

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

#### Scenario: Travel adds named shared states
- **WHEN** travel draws its party seal, landmark ornament or neighbour/hostile/route states
- **THEN** each concept/state has one shared definition, repeated consumers differ only by uniform scale and the existing non-travel states retain their original shapes
