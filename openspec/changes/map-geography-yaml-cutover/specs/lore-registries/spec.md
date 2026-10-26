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

