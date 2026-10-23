# map-district-partition Specification

## Purpose
Define reproducible offline district ownership and frozen outlines over the continent while keeping partition computation out of runtime play.

## Requirements

### Requirement: Offline partition assigns every land cell once without crossing barriers
The offline partition SHALL reserve all region-district terrain first and partition remaining land by walking distance on a 5 km 540 by 540 raster, with eight-connected moves and diagonal cost sqrt(2). Sea, summit ridge, rivers and national borders SHALL block Voronoi propagation; passes and fords permit terrain traversal but national borders stay closed. Each land cell SHALL map to exactly one district and each landmark SHALL lie in its own district.

#### Scenario: Coarse diagonal cannot jump a narrow obstacle
- **WHEN** two 5 km cells have traversable centres but their connection intersects a 1 km river, ridge or closed national boundary
- **THEN** propagation rejects the crossing, including diagonal corner cutting, while a legal same-nation ford/pass route remains available

#### Scenario: Forest remains a single region district
- **WHEN** the entire mainland is partitioned
- **THEN** all northern deep-forest cells belong to the one region district even across nominal nations, and every remaining land cell has one reachable Voronoi owner

#### Scenario: A settlement footprint owns the pocket it encloses
- **WHEN** a same-nation walkable pocket is enclosed on all eight sides by the claimed footprint of a grid landmark
- **THEN** the pocket belongs to that landmark's district with its footprint, while any other unseeded walkable component fails generation with its coordinates

### Requirement: Frozen partition and outlines reproduce deterministically offline
The partition and smoothed outlines SHALL be stored as version-controlled frozen data with row run-length encoding of ownership. Recomputing from the same authored geography and registry SHALL reproduce the stored data. Runtime district lookup SHALL read frozen data without running the partitioner.

#### Scenario: Regeneration has stable output
- **WHEN** the tool runs twice with identical inputs and deterministic tie ordering
- **THEN** ownership runs and smoothed outlines match each other and committed data byte for byte

#### Scenario: Stale generated data is detected
- **WHEN** a registry or geography change alters ownership without regeneration
- **THEN** the recomputation test fails with a mismatch rather than silently adopting runtime computation
