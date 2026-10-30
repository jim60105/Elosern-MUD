# wilderness-elevation-runtime Specification

## Purpose
Publish bounded fingerprinted elevation tiles and runtime lookup. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Elevation artifacts are bounded and source identified
Generation SHALL atomically publish deterministic elevation tiles within4MiB, with fingerprints covering geographic, configuration and algorithm inputs.

#### Scenario: Budget and freshness
- **WHEN** synthetic output exceeds budget or an input changes without regeneration
- **THEN** prior bytes survive oversize failure and freshness rejects the named changed source

#### Scenario: Partial edge tiles
- **WHEN** a frame ends inside its final tile
- **THEN** real cells round trip and unused padding is zero

### Requirement: Runtime elevation rejects stale or corrupt artifacts
Map adoption SHALL reject missing, stale or integrity-invalid elevation artifacts and expose bounded cached tile lookup without offline numeric dependencies.

#### Scenario: Admission and lookup
- **WHEN** an artifact digest/source changes or repeated synthetic lookups exceed cache capacity
- **THEN** bad candidates never replace the published bundle, lookups match packed bytes, cache<=128 and invalid expansion/bounds reject
