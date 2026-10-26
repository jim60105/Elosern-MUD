# Spec Delta

## MODIFIED Requirements

### Requirement: AnchorPlacement is a frozen dataclass separate from Anchor
Game placement views SHALL derive immutable location-to-settlement bindings from settlement documents without adding placement fields to non-map lore.

#### Scenario: Spatial ownership
- **WHEN** a settlement names a location and anchor node
- **THEN** the composed placement follows the current qualified node binding while political/population/floor lore is unchanged

### Requirement: Every placement's anchor_key resolves against ANCHOR_REGISTRY
Every derived placement SHALL resolve an existing geographic location and a node in its declared settlement.

#### Scenario: Missing location or node
- **WHEN** a settlement binding names an absent location or anchor node
- **THEN** validation names the broken source field and rejects runtime publication

### Requirement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial
Placement views SHALL contain exactly authored local-map associations derived from settlement-owned location references without requiring a local map for every location.

#### Scenario: Unbuilt and newly built location
- **WHEN** one location has no local map and another gains a discovered settlement document
- **THEN** only the built association appears and no reverse location document edit or Python registration is needed

