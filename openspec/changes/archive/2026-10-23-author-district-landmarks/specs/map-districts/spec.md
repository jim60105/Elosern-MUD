# Spec Delta

## ADDED Requirements

### Requirement: The authored continent has a complete discoverable landmark roster
The district registry SHALL contain approximately 110–130 individually authored districts and landmarks with Traditional Chinese names, targeting roughly 200 km district width. Every district SHALL retain exactly one reachable canonical landmark, with the northern deep forest remaining one region district and its single deep landmark. Frozen ownership and outlines SHALL be regenerated from this roster.

#### Scenario: Final roster remains geographically valid
- **WHEN** the full authored registry is validated and partitioned
- **THEN** every landmark is reachable on walkable land, existing grid nodes resolve, declared Voronoi minimum spacing holds, every land cell has one owner and no Voronoi district straddles a barrier or national border

#### Scenario: Authored names are stable lore content
- **WHEN** the player lights different districts
- **THEN** district and landmark names are distinct authored lore appropriate to their geography, with no numbered placeholders, generated-at-runtime names or repeated cyclic prototype name list
