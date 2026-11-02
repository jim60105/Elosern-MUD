## REMOVED Requirements

### Requirement: Anchor registry covers capitals, elven villages, and known dungeons
**Reason**: The title lists only three of the six location kinds now in the closed vocabulary (commit 1bf6e0ad added city, town and port), and its scenario "Registry has exactly nine anchors of the right kinds" names a roster size; OpenSpec cannot drop or retitle scenarios under MODIFIED.
**Migration**: Replaced by "Anchor registry composes every declared location kind" below; tests change their `covers_requirement` ID to `lore-registries::anchor-registry-composes-every-declared-location-kind`.

## ADDED Requirements

### Requirement: Anchor registry composes every declared location kind
The game SHALL compose immutable location views from map-owned identity/kind/name/prose and separate non-map lore keyed by the same identity, over one closed location-kind vocabulary shared with the map schema, without a fixed roster count.

#### Scenario: Location kind and lore
- **WHEN** synthetic capital, village and dungeon locations join nation/population/floor metadata
- **THEN** map-facing fields come from YAML, non-map values remain their authored lore values and unknown joins are diagnosed

#### Scenario: National settlement lore joins
- **WHEN** every shipped city, town or port location joins its non-map lore
- **THEN** each carries a registered nation, a positive population and no floor count, without comparing authored magnitudes between locations

#### Scenario: No invented local content
- **WHEN** a new geographic location has no settlement or interior document
- **THEN** it remains readable without generating rooms, dungeon floors, instances or population

#### Scenario: The location kind vocabulary is closed and shared
- **WHEN** the map schema's location kinds are compared with the game's anchor kinds and a synthetic source declares one location of each kind
- **THEN** both vocabularies are the same set and each synthetic identity composes exactly once with its declared kind; shipped content need not use every kind and no production roster size is imposed

#### Scenario: Dungeon floor counts match world_info.md
- **WHEN** a dungeon's map-facing location fields change while its separate floor lore remains unchanged
- **THEN** the composed view retains the existing authored floor value without deriving it from geometry or copying a floor approval table into map tests

#### Scenario: Elven villages are not assigned to a nation
- **WHEN** a location joins non-map lore with a nullable political affiliation
- **THEN** an absent nation stays absent regardless of the location's geometric nominal claim
