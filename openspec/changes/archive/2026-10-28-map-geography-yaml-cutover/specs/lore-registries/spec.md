# Spec Delta

## MODIFIED Requirements

### Requirement: Anchor registry covers capitals, elven villages, and known dungeons
The game SHALL compose immutable location views from map-owned identity/kind/name/prose and separate non-map lore keyed by the same identity, without a fixed roster count.

#### Scenario: Location kind and lore
- **WHEN** synthetic capital, village and dungeon locations join nation/population/floor metadata
- **THEN** map-facing fields come from YAML, non-map values remain their authored lore values and unknown joins are diagnosed

#### Scenario: No invented local content
- **WHEN** a new geographic location has no settlement or interior document
- **THEN** it remains readable without generating rooms, dungeon floors, instances or population

#### Scenario: Registry has exactly nine anchors of the right kinds
- **WHEN** a synthetic source contains locations of each supported kind
- **THEN** the composed registry includes those identities with their declared kinds and no duplicates; the inherited scenario title does not impose a fixed production roster size

#### Scenario: Dungeon floor counts match world_info.md
- **WHEN** a dungeon's map-facing location fields change while its separate floor lore remains unchanged
- **THEN** the composed view retains the existing authored floor value without deriving it from geometry or copying a floor approval table into map tests

#### Scenario: Elven villages are not assigned to a nation
- **WHEN** a location joins non-map lore with a nullable political affiliation
- **THEN** an absent nation stays absent regardless of the location's geometric nominal claim

