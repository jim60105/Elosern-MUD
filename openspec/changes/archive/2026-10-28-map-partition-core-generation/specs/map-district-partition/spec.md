# Spec Delta

## MODIFIED Requirements

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

