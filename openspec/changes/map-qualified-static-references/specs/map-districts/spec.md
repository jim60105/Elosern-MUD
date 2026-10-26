# Spec Delta

## MODIFIED Requirements

### Requirement: Every map district has one canonical reachable landmark
Each district SHALL resolve one qualified landmark to a reachable walkable position, with unique identities, declared minimum Voronoi spacing and region membership only for region districts.

#### Scenario: Invalid landmarks fail authoring validation
- **WHEN** sea, blocked terrain, absent settlement nodes, duplicate landmarks or insufficient spacing are declared
- **THEN** runtime validation rejects and names each invalid declaration; authoring retains saveable reachability diagnostics

#### Scenario: Stable landmark movement
- **WHEN** a settlement landmark moves with its stable node identity
- **THEN** the runtime canonical landmark follows its new binding while district lighting still reads existing visited-node knowledge

