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
Frozen partition data SHALL reproduce from identical explicit map inputs and algorithm version, carry their dependency signature and support lightweight runtime decoding/freshness checks without generation dependencies.

#### Scenario: Regeneration has stable output
- **WHEN** the partitioner runs twice on identical synthetic inputs and deterministic tie ordering
- **THEN** ownership runs and outlines match byte for byte

#### Scenario: Stale generated data is detected
- **WHEN** a relevant source value or membership changes without regeneration
- **THEN** signature validation rejects game freshness without raster generation or NumPy/SciPy imports

#### Scenario: Independent generation
- **WHEN** a core snapshot is partitioned in the generation environment with game imports blocked
- **THEN** input assembly and partition complete using the extracted existing rules and the game adapter reads the same artifact format
