## MODIFIED Requirements

### Requirement: WILDERNESS_ENTRY_REGISTRY authored data is validated before persistence
The game SHALL use the shared DB-free core map diagnostics before publishing or mirroring wilderness entries, rejecting malformed masks, invalid targets and unprovisionable terrain or gate geometry without duplicating the rejection rules.

#### Scenario: The shipped registry validates
- **WHEN** the current authored world is loaded through the game candidate path before lore mirroring
- **THEN** valid wilderness entries compose without a map rejection and the mirror uses that validated world

#### Scenario: Malformed authored entries are each rejected
- **WHEN** a synthetic source candidate contains one malformed entry at a time, including an empty mask, out-of-bounds hash cell, disconnected footprint, non-canonical or duplicated return_direction, gate face not crossing the footprint, point shape with zero or two gates, unknown destination node, or unknown location_ref
- **THEN** the shared core schema or map diagnostics name the entry and rejected rule before any publication or mirroring

#### Scenario: Malformed masks and colliding geometry are each rejected
- **WHEN** one candidate at a time contains ragged rows, an illegal character, an all-dot mask, a midpoint on a dot, overlapping footprints, a footprint containing another gate approach, duplicate gate destination rooms, or a point entry with a provider-invalid authored neighbor
- **THEN** the core rejects invalid structure or diagnoses semantic map errors and the game rejects the candidate through those same rules

#### Scenario: sync_all refuses to mirror a malformed registry
- **WHEN** startup synchronization is given an authored candidate with a malformed wilderness entry
- **THEN** core validation rejects before any wilderness-entry lore record is created or updated, without a game-local validator rechecking the same rules

#### Scenario: Per-entry rejection conditions
- **WHEN** the shared validator checks wilderness entries
- **THEN** it rejects invalid mask grammar or unknown targets and diagnoses hash cells outside the frame or on impassable terrain, disconnected footprints, invalid exterior rays or approaches, point entries without exactly one gate, or point anchors and authored-direction neighbors that are not provider-valid

#### Scenario: Mask shape and anchor cell well-formedness
- **WHEN** an entry's mask and derived midpoint are validated
- **THEN** a non-empty rectangle containing only hash and dot cells and at least one hash is required, and a non-point mask whose midpoint is outside its hash cells has a blocking semantic diagnostic

#### Scenario: Global cross-entry constraints
- **WHEN** the core checks all entries together
- **THEN** footprints do not overlap or contain another entry's approach or point anchor, gate approach-cell/direction pairs are unique, and each destination room hosts at most one wilderness gate

#### Scenario: Point-shape anchors need all neighbors provider-valid
- **WHEN** a point entry is validated
- **THEN** its hash anchor and authored return_direction neighbor must be provider-valid walkable terrain while the other directions follow ordinary terrain validity
