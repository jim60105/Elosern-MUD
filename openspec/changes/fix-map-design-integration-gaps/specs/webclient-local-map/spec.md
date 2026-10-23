# Spec Delta

## MODIFIED Requirements

### Requirement: Island projection handles sparse and coincident nodes deterministically
No-exit, zero-distance and overlapping-exit inputs SHALL produce finite deterministic positions. Overlap handling SHALL account for painted marker footprints, including gateway arches and feet. Context SHALL use the same mapping, with off-canvas context omitted and remembered remote nodes retaining their existing edge-direction presentation.

#### Scenario: No exits and no distance
- **WHEN** a model has no exits
- **THEN** drawable context supplies the level-selection distances; with no positive drawable distance the default level is 100, and the current-only result remains centred.

#### Scenario: Zero-distance exits
- **WHEN** exits have no defined bearing because their distance from current is zero
- **THEN** their bearings are assigned in payload order starting north and evenly spaced; their placement is finite and keeps the current marker clear, without evaluating a logarithm of zero.

#### Scenario: Overlapping exits
- **WHEN** exit marker footprints at similar radii would overlap
- **THEN** they are spread symmetrically about their mean bearing by no more than ±20 degrees; non-overlapping exits keep exact bearings and ordinary context does not receive invented routes.

#### Scenario: Gateway feet overlap despite separated marker centres
- **WHEN** current is at grid coordinate (0,0) and two gateway exits at (-120,800) and (120,800) project at level 1000
- **THEN** the painted gate footprints receive clearance within the existing spread cap, current remains at (120,120), exit radii and distance order are unchanged, and every node and action retains its original identity.

#### Scenario: Mixed exit footprints and unaffected bearings
- **WHEN** gateway and ordinary exits include an overlapping pair that can be separated within the cap and a separate non-overlapping exit
- **THEN** pair clearance accounts for both painted footprints, the separate exit retains its exact bearing, and spreading remains deterministic; crowded groups that cannot fully clear within the cap never exceed it or invent a position identity.

### Requirement: Island background describes the selected distance mapping
Uniform projection SHALL return dots with 20-unit spacing anchored to integer world multiples of M/5 metres and a scale-spacing caption. Compressed projection SHALL return labelled concentric distance rings positioned by the same distance mapping, including metre-scale positive inputs, with shape and text distinguishing compression. Ring geometry and candidate work SHALL remain finite and bounded.

#### Scenario: Dot anchors follow ground
- **WHEN** the current location moves while level M is unchanged
- **THEN** each dot remains anchored to integer multiples of M/5 metres and its screen offset changes with the world-coordinate origin; the caption states that spacing, such as `格距 300 m` at M=1500.

#### Scenario: Compressed rings use real distances
- **WHEN** a compressed projection is generated
- **THEN** a bounded readable set of positive distances, such as 100 m, 300 m and 1 km when in range, receives radii from the same mapping and distance labels; no uniform dot field is returned.

#### Scenario: One-metre exits retain a readable compressed background
- **WHEN** equal positive one-metre exits select compressed mode
- **THEN** at least one readable positive-distance ring is drawn inside the canvas with a truthful distance label and a radius from that projection's mapper; the one-metre ring is at radius 66 and the result respects the existing ring count and separation limits.

#### Scenario: Mixed and degenerate scales remain bounded
- **WHEN** exits span 80 m and 1200 m, or input includes zero distances beside positive distances
- **THEN** rings remain finite, distance-ordered and correctly mapped, with the existing readability limits; zero-only or missing positive ranges do not cause logarithms of zero, unbounded iteration or fabricated distance rings.

### Requirement: Island gateways expose labelled accessible exit-ring controls
The island SHALL draw gateway nodes with a gate glyph, room label and second line `通往 <leads_to>`. A cross-layer target SHALL appear only as an exit-ring arrow labelled `通往 <leads_to>`, retaining its nullable move action. An actionable stub SHALL be a focusable button named `往 <leads_to> 移動`; its arrow and label SHALL have separate compact hit regions for every label placement, leaving the intervening empty space clear of stub activation.

#### Scenario: Current city gate offers wilderness travel
- **WHEN** the current city gate carries its far-side region metadata and a cross-layer target move descriptor
- **THEN** the region-labelled stub is drawn at that target bearing on the exit ring; pointer, Enter and Space each submit exactly one move using the original exit_ref and current_node, without also opening the map or inventing a destination.

#### Scenario: Wilderness offers city return without city streets
- **WHEN** a wilderness payload carries an adjacent grid gateway with settlement leads_to metadata
- **THEN** the island shows the settlement-labelled exit-ring stub, no cross-layer grid node or city streets, and no scale effect from the renderer-local gateway offset; its move arrives at the original grid destination.

#### Scenario: A locked gateway remains navigation information
- **WHEN** a gateway exit has action null
- **THEN** its exit representation and far-side label remain visible, but activation submits no move; the gateway field never grants traversal that the server withheld.

#### Scenario: Gateway stories check the full exit set
- **WHEN** metric south-gate and wilderness-return stories run
- **THEN** the story checks every same-layer exit marker and cross-layer exit-ring representation inside the canvas with no two exit markers overlapping; its focus and activation assertions preserve exact payload actions.

#### Scenario: A nearby street remains the pointer target beside an unleadered stub label
- **WHEN** a north stub at (120,32) has a label without a leader and a same-layer street exit at (135,35), produced from grid delta (150,850) at level 1000, is clicked at its visible centre through actual browser hit testing
- **THEN** exactly one move uses the street's original exit_ref and destination with the authoritative current_node, no gateway move is sent and the map drawer stays closed.

#### Scenario: Separate stub regions preserve native activation
- **WHEN** the stub arrow or its separated label is pointer-activated, or the focused native stub button receives Enter or Space through the browser's normal keyboard sequence
- **THEN** each independent activation sends exactly one original gateway move, retains the full accessible name and never opens the drawer; leadered and unleadered labels obey the same hit-region rule.
