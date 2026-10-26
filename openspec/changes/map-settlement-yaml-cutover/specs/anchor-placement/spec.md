# Spec Delta

## MODIFIED Requirements

### Requirement: AnchorPlacement is a frozen dataclass separate from Anchor
Game placement views SHALL derive immutable location-to-settlement bindings from settlement documents without adding placement fields to non-map lore.

#### Scenario: Spatial ownership
- **WHEN** a settlement names a location and anchor node
- **THEN** the composed placement follows the current qualified node binding while political/population/floor lore is unchanged

#### Scenario: Anchor dataclass is untouched
- **WHEN** settlement placement is composed with non-map location lore
- **THEN** placement adds no coordinate fields or duplicate political/population/floor facts to the non-map lore record

#### Scenario: AnchorPlacement carries no lore fact
- **WHEN** the immutable placement projection is read
- **THEN** it contains only resolved location/map/node binding facts, with lore supplied by its separate identity join

### Requirement: Every placement's anchor_key resolves against ANCHOR_REGISTRY
Every derived placement SHALL resolve an existing geographic location and a node in its declared settlement.

#### Scenario: Missing location or node
- **WHEN** a settlement binding names an absent location or anchor node
- **THEN** validation names the broken source field and rejects runtime publication

#### Scenario: capital_altoria's placement resolves
- **WHEN** the capital's discovered settlement binding is resolved
- **THEN** its qualified location and anchor node exist in the current snapshot, without a fixed coordinate assertion

#### Scenario: No placement references a nonexistent anchor
- **WHEN** any derived placement names an absent location
- **THEN** validation rejects before publishing placements or mirroring lore

### Requirement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial
Placement views SHALL contain exactly authored local-map associations derived from settlement-owned location references without requiring a local map for every location.

#### Scenario: Unbuilt and newly built location
- **WHEN** one location has no local map and another gains a discovered settlement document
- **THEN** only the built association appears and no reverse location document edit or Python registration is needed

#### Scenario: The registry follows the built settlement maps
- **WHEN** settlement source membership changes
- **THEN** placement membership derives from those supported documents, and unbuilt locations need no placeholder placement

#### Scenario: capital_altoria's placement matches the sample city's spawned AnchorRoom
- **WHEN** the loaded capital anchor is synchronized
- **THEN** its placement resolves the same stable AnchorRoom at that node's current binding

#### Scenario: Every placement matches its settlement's spawned AnchorRoom
- **WHEN** multiple settlement anchors synchronize
- **THEN** each placement resolves its own stable room/map binding without collisions or cross-map substitution

