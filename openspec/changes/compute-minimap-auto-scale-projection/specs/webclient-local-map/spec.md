# Spec Delta

## ADDED Requirements

### Requirement: Island projection selects a metric scale for one-hop exits
The coordinate-bearing island SHALL centre the current node at (120,120) in a 240-unit square and select its scale from same-layer one-hop exits, including locked exits. Normal placement SHALL preserve exact bearings and use the smallest fitting level in the approved ladder with R_MAX 88 and R_MIN 36.

#### Scenario: Distance inputs respect their coordinate frames
- **WHEN** a grid or wilderness model is projected
- **THEN** grid deltas are metres and wilderness cell deltas are converted to metres at the existing one-kilometre cell scale without altering the payload; exit tiers come from non-empty-labelled edges incident to current, independent of action; other same-layer in-view nodes are context and cross-layer nodes never affect scale.

#### Scenario: The full ladder and worked uniform examples
- **WHEN** positive exit distances are projected
- **THEN** the level is selected from 10,15,20,30,50,75,100,150,200,300,500,750,1000,1500,2000,3000,5000 metres per 100 units using d_max * 100 / M <= 88; Altoria plaza exits about 850–1090 m choose 1500 with radii about 57–72, and wilderness cardinal/diagonal neighbours choose 2000 with radii 50 and about 71.

#### Scenario: Hysteresis keeps at most one coarser fitting level
- **WHEN** the prior level still fits all exits and is at most one ladder step coarser than the ideal
- **THEN** it is retained; an insufficient level or one more than one step coarser is replaced by the ideal, and a changed current-node map key discards the previous level before selection.

### Requirement: Island projection compresses extreme exit distances monotonically
When the nearest uniform exit radius is below 36 or no ladder level fits the farthest exit, the island SHALL use compressed distance mapping from radius 36 to 88. Distance order and bearings SHALL remain intact except for the bounded overlap-spreading rule.

#### Scenario: Logarithmic compression and equal distances
- **WHEN** positive exit distances span d_min to d_max in compressed mode
- **THEN** r(d) = 36 + 52 * ln(d/d_min) / ln(d_max/d_min); context closer than d_min uses 36*d/d_min; equal positive exit distances use radius 66; bearings are unchanged before overlap handling.

#### Scenario: Compression boundaries
- **WHEN** an 80 m exit and a 1200 m exit are projected, or d_max exceeds 4400 m
- **THEN** compressed mode is used; a nearest radius exactly 36 remains uniform if all exits fit, and a farthest radius exactly 88 at level 5000 still fits.

### Requirement: Island projection handles sparse and coincident nodes deterministically
No-exit, zero-distance and overlapping-exit inputs SHALL produce finite deterministic positions. Context SHALL use the same mapping, with off-canvas context omitted and remembered remote nodes retaining their existing edge-direction presentation.

#### Scenario: No exits and no distance
- **WHEN** a model has no exits
- **THEN** drawable context supplies the level-selection distances; with no positive drawable distance the default level is 100, and the current-only result remains centred.

#### Scenario: Zero-distance exits
- **WHEN** exits have no defined bearing because their distance from current is zero
- **THEN** their bearings are assigned in payload order starting north and evenly spaced; their placement is finite and keeps the current marker clear, without evaluating a logarithm of zero.

#### Scenario: Overlapping exits
- **WHEN** exit marker footprints at similar radii would overlap
- **THEN** they are spread symmetrically about their mean bearing by no more than ±20 degrees; non-overlapping exits keep exact bearings and ordinary context does not receive invented routes.

### Requirement: Island projection separates gateway stubs from node scale
A cross-layer target SHALL be absent from island node placement and all distance calculations, while retaining its exit bearing, far-side label and validated move action as an exit-stub descriptor.

#### Scenario: Gate slot cannot change scale
- **WHEN** a current gateway carries a cross-layer target at a renderer-local slot and that slot offset changes
- **THEN** same-layer scale and projected node positions remain unchanged; the target yields an exit-ring stub with its bearing, `通往 <leads_to>` label and original nullable action; gateway metadata comes from the current gateway or target as available, never from invented geography.

### Requirement: Island background describes the selected distance mapping
Uniform projection SHALL return dots with 20-unit spacing anchored to integer world multiples of M/5 metres and a scale-spacing caption. Compressed projection SHALL return labelled concentric distance rings positioned by the same distance mapping, with shape and text distinguishing compression.

#### Scenario: Dot anchors follow ground
- **WHEN** the current location moves while level M is unchanged
- **THEN** each dot remains anchored to integer multiples of M/5 metres and its screen offset changes with the world-coordinate origin; the caption states that spacing, such as `格距 300 m` at M=1500.

#### Scenario: Compressed rings use real distances
- **WHEN** a compressed projection is generated
- **THEN** a bounded readable set of positive distances, such as 100 m, 300 m and 1 km when in range, receives radii from the same mapping and distance labels; no uniform dot field is returned.
