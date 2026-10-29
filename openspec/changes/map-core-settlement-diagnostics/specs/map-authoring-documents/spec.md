## MODIFIED Requirements

### Requirement: Authoring diagnostics and runtime acceptance have distinct gates
Authoring load SHALL use shared map diagnostics to reject invalid structure and permit semantically unfinished maps, while runtime acceptance rejects those map errors and requires authoritative external-reference and artifact-freshness validation.

#### Scenario: Saveable unfinished world
- **WHEN** a valid empty graph or inaccessible landmark is loaded
- **THEN** authoring succeeds with a semantic diagnostic and runtime construction is rejected

#### Scenario: Invalid structure
- **WHEN** a road has a missing endpoint or duplicate outgoing direction
- **THEN** structured editing/writing is blocked rather than treating it as game-readiness WIP

#### Scenario: DIAG-ANCHOR missing or ambiguous anchor
- **WHEN** a settlement has no anchor node, multiple anchor_room nodes, an anchor_key unequal to location_ref, or a location_ref already owned by another settlement
- **THEN** the core reports the named source defect and game adoption rejects it; a missing anchor is saveable semantic WIP, while multiple anchors, mismatched keys and duplicate location ownership are structure errors

#### Scenario: DIAG-MASK invalid physical mask
- **WHEN** a mask is disconnected, its midpoint misses its hash cells, a hash cell lies outside the frame or on impassable ground, or its occupied cells intersect another footprint or point entry
- **THEN** the core reports a semantic map diagnostic naming the involved entries and game adoption rejects the same world, including point-cell terrain failures despite point entries owning no wilderness obstacle

#### Scenario: DIAG-GATE invalid approach and point entry
- **WHEN** a gate ray cannot yield an in-frame exterior cell, an approach is blocked or inside another footprint, a point entry has multiple gates, or its authored direction leads to a provider-invalid neighbor
- **THEN** the core reports a semantic map diagnostic and game adoption rejects the same world; unrelated point-entry directions remain ordinary wilderness movement and a zero-gate entry remains a schema structure error

#### Scenario: DIAG-COLLISION unprovisionable gates
- **WHEN** gates share an approach-cell/direction pair or destination room, or another gate approach equals a point entry
- **THEN** the core diagnoses the collision before runtime publication; duplicate destinations are structure errors and spatial approach collisions are semantic map errors

#### Scenario: DIAG-INTERIOR duplicated identity or doorway
- **WHEN** interior room IDs repeat across documents or two interiors declare the same doorway_key on one settlement node
- **THEN** the core reports a structure diagnostic naming both owners and game adoption rejects without changing the previously published world or persistent rooms

#### Scenario: DIAG-AGREEMENT independently invalid candidate matrix
- **WHEN** each shared rule above is violated separately in an otherwise valid synthetic world and loaded through the core and game candidate path
- **THEN** each core code/category/source identifies that rule, the game rejects through the shared diagnostic, and the static checker reports the same decision without a second rule implementation
