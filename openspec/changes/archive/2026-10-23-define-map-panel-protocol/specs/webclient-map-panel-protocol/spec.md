# Spec Delta

## Purpose

Define the exact on-demand area/world panel wire models and bounded atomic delivery so presenters and views share one contract.

## ADDED Requirements

### Requirement: Map panels use exact layer and precision discriminators
Area and world map logical payloads SHALL use versioned exact-field schemas with distinct metric grid, coordinate-free room graph and wilderness forms. Each area SHALL identify its stable map and coordinate frame. Local destinations SHALL be node identities; remote area destinations SHALL be bearing/distance. World unlit districts SHALL expose only opaque identity/outline and approximate quest rows SHALL carry only 50km-rounded positions.

#### Scenario: Coordinate frames are not interchangeable
- **WHEN** a player crosses from settlement to wilderness or enters another interior
- **THEN** the new panel changes stable map/frame identity and its node geometry has the new declared units, without inheriting coordinates from the prior frame

#### Scenario: Malformed or secretly enriched records are rejected
- **WHEN** a node, unlit district or approximate marker has extra fields or wrong discriminator types
- **THEN** both validators reject it rather than preserving unknown metadata

### Requirement: Map delivery replaces only complete epoch-safe logical panels
On-demand maps SHALL remain separate from eager snapshots, survive same-epoch eager refreshes unchanged and clear on epoch retirement. Large map parts SHALL have finite byte/count limits and replace map state only after complete validated assembly.

#### Scenario: Eager movement refresh does not rebuild maps
- **WHEN** movement or a text command publishes ordinary presentation without map.view
- **THEN** map presenters do not execute and same-epoch complete maps are retained without a push

#### Scenario: Partial or stale delivery stays invisible
- **WHEN** a large map transfer loses a part, duplicates an index or crosses an epoch/newer transfer boundary
- **THEN** no incomplete/mixed logical panel is adopted and memory remains bounded
