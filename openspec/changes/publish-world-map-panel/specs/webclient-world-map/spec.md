# Spec Delta

## Purpose

Publish a server-filtered continental exploration map without disclosing unrevealed district contents or exact unknown commission destinations.

## ADDED Requirements

### Requirement: World scope reveals only common geography and permitted district knowledge
map.view world SHALL publish world_map read-only and on demand. Common geography SHALL contain coastline, derived borders outside deep forest, nation names and label positions. Lit districts SHALL contain ID, name, outline, landmark position, terrain wash, rivers, ridge, roads and non-hidden places. Unlit districts SHALL contain only outline and opaque identity.

#### Scenario: Fresh explorer receives no secret geography
- **WHEN** a player with no visited landmark requests the world map
- **THEN** the serialized payload contains common geography and unlit outlines but no unlit district names, landmarks, terrain, rivers, ridge, roads or place records

#### Scenario: Hidden places require an actual visit
- **WHEN** a district becomes lit while a hidden elven village or dungeon remains unvisited
- **THEN** the hidden place is absent even though ordinary places and capitals in the lit district appear; a previously visited place may appear independently of district lighting

#### Scenario: Caching cannot reuse another player knowledge
- **WHEN** two characters with different visited sets request the same static districts
- **THEN** static geometry caches may be reused, but each final payload includes only that requesting character permitted knowledge

### Requirement: World trails retain visited ground with bounded precision reduction
The trail SHALL include visited wilderness cells encoded as row runs at one-kilometre resolution up to 20000 unique cells. Above 20000 cells it SHALL downsample to 5 km cells and row-run encode the result. The current position and visited hidden places SHALL remain represented.

#### Scenario: Trail crosses the initial threshold
- **WHEN** visited wilderness count changes from 20000 to 20001
- **THEN** the former uses 1 km cells and the latter uses deduplicated 5 km cells with an explicit resolution, retaining visited coverage without sending all raw visits

### Requirement: Unknown world commission destinations are rounded before serialization
Accepted commissions SHALL use exact world coordinates only when their destination district is lit. Otherwise coordinates SHALL be rounded to a 50 km grid and the marker SHALL be flagged approximate. Exact coordinates SHALL not be present in any alternate field, canonical node identity, distance, bearing or cached payload sent for an approximate world marker.

#### Scenario: Unlit quest marker cannot recover exact location
- **WHEN** a commission destination is inside an unlit district
- **THEN** only its rounded world point and approximate flag are serialized, with no precise destination node or exact-derived distance/bearing; the client receives enough data for the dashed approximate marker

#### Scenario: Lighting permits the precise marker
- **WHEN** the destination district landmark is visited and world scope is requested again
- **THEN** the marker becomes precise using the canonical destination resolver

