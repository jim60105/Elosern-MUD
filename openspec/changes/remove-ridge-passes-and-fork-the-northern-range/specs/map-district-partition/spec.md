# Spec Delta

## MODIFIED Requirements

### Requirement: Offline partition assigns every land cell once without crossing barriers
The offline partition SHALL reserve region-district terrain first and assign remaining land by walking distance on the established 5 km raster, blocking sea, complete physical ridge walls, rivers and national borders while preserving diagonal corner guards, unique district ownership and landmark ownership.

#### Scenario: Coarse diagonal cannot jump a narrow obstacle
- **WHEN** two 5 km cells have traversable centres but their connection intersects a 1 km river, stem, ridge arm or closed national boundary
- **THEN** propagation rejects the crossing including diagonal corner cutting, while legal same-nation fords remain available and national borders stay closed

#### Scenario: Forest remains a single region district
- **WHEN** a synthetic mainland containing paired forest arms is partitioned
- **THEN** both arm spans are blocked in the walkability input, forest keeps its single region-district ownership across nominal nations, and every remaining land cell has one reachable Voronoi owner

#### Scenario: A settlement footprint owns the pocket it encloses
- **WHEN** a same-nation walkable pocket is enclosed on all eight sides by the claimed footprint of a grid landmark
- **THEN** the pocket belongs to that landmark's district with its footprint, while any other unseeded walkable component fails generation with its coordinates

#### Scenario: Stem passes cannot open political borders
- **WHEN** a synthetic document authors a stem pass or a ford on a national boundary
- **THEN** terrain traversal may be open there but partition propagation still cannot cross the national boundary; shipped ridge content authors no passes
