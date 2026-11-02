## MODIFIED Requirements

### Requirement: World scope reveals only common geography and permitted district knowledge
map.view world SHALL publish world_map read-only and on demand. Common geography SHALL contain coastline, derived borders outside deep forest, nation names and label positions. Lit districts SHALL contain ID, name, outline, landmark position, terrain wash, rivers, ridge, roads and non-hidden places. Unlit districts SHALL contain only outline and opaque identity.

#### Scenario: Fresh explorer receives no secret geography
- **WHEN** a player with no visited landmark requests the world map
- **THEN** the serialized payload contains common geography and unlit outlines but no unlit district names, landmarks, terrain, rivers, ridge, roads or place records

#### Scenario: Hidden places require an actual visit
- **WHEN** a district becomes lit while a hidden elven village or dungeon remains unvisited
- **THEN** the hidden place is absent even though ordinary places and capitals in the lit district appear; a previously visited place may appear independently of district lighting

#### Scenario: Place kinds derive from location kinds
- **WHEN** synthetic locations of every location kind and a synthetic harbour site are classified as world places
- **THEN** capitals carry wire kind `capital`, every other public location kind carries `settlement`, elven villages and dungeons carry `hidden` and are visit-only, and harbour sites carry `harbour`

#### Scenario: Caching cannot reuse another player knowledge
- **WHEN** two characters with different visited sets request the same static districts
- **THEN** static geometry caches may be reused, but each final payload includes only that requesting character permitted knowledge
