# map-districts Specification

## Purpose
Provide immutable exploration districts with one reachable landmark each and lighting derived only from existing visited-node knowledge.

## Requirements

### Requirement: Every map district has one canonical reachable landmark
Each frozen district SHALL expose a stable key, district_name_zh, landmark_name_zh, landmark_node, kind of voronoi or region, and region_key only for region districts. Landmark identities SHALL be canonical wild:elosern:<x>:<y> or existing grid:<map>:<x>:<y> nodes, with reachable walkable positions and declared minimum Voronoi spacing.

#### Scenario: Invalid landmarks fail authoring validation
- **WHEN** a registry references sea, blocked terrain, an absent grid node, duplicate identity, or Voronoi landmarks below the declared minimum spacing
- **THEN** validation rejects the registry and identifies the invalid declarations

#### Scenario: Deep forest has one discovery landmark
- **WHEN** the northern deep forest district is read
- **THEN** it is one region district covering both nominal nations, with one landmark near its north-coast centre around (1250,2420), roughly 500 km from the forest edge

### Requirement: District lighting is derived from visited landmark identity
A district SHALL be lit if and only if its exact landmark node is in the player map-knowledge visited record. Reading lighting SHALL introduce no persistent state and SHALL leave the existing knowledge writer unchanged.

#### Scenario: Nearby travel does not reveal a district
- **WHEN** the player visits cells near a landmark but never its canonical node
- **THEN** the district remains unlit

#### Scenario: Recorded landmark reveals only its district
- **WHEN** the exact landmark node appears in visited knowledge
- **THEN** that district becomes lit on read without a second discovery attribute, while other districts remain unlit

### Requirement: The authored continent has a complete discoverable landmark roster
The district registry SHALL contain the districts and landmarks authored in
`world/lore/map_districts.py`, named in Traditional Chinese with a target district width of roughly
200 km. Every district SHALL retain exactly one reachable canonical landmark; the northern deep
forest stays one region district with its single deep landmark. Frozen ownership and outlines SHALL
be regenerated from this roster, whose size SHALL stay authored data, not a specification-owned
count.

#### Scenario: Final roster remains geographically valid
- **WHEN** the full authored registry is validated and partitioned
- **THEN** every landmark is reachable on walkable land, existing grid nodes resolve, declared Voronoi minimum spacing holds, every land cell has one owner and no Voronoi district straddles a barrier or national border

#### Scenario: Authored names are stable lore content
- **WHEN** the player lights different districts
- **THEN** district and landmark names are distinct authored lore appropriate to their geography, with no numbered placeholders, generated-at-runtime names or repeated cyclic prototype name list
