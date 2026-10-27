# Spec Delta

## MODIFIED Requirements

### Requirement: The authored continent has a complete discoverable landmark roster
The district document SHALL supply every district and landmark exactly once, with qualified identity resolution and runtime geographic validation independent of Python roster imports.

#### Scenario: Roster discovery
- **WHEN** a synthetic district is added with a unique stable ID and reachable landmark
- **THEN** loading discovers it and lighting/partition consumers resolve it without code registration or a specification-owned count

#### Scenario: Invalid district candidate
- **WHEN** a district has a duplicate ID, invalid kind/region shape, unreachable landmark or insufficient declared spacing
- **THEN** structural errors block authoring; loadable geographic failures remain diagnosed and reject runtime adoption

#### Scenario: Authored naming ownership
- **WHEN** a district or landmark display name is edited without changing its ID
- **THEN** consumers display that authored value and relationships remain identity-based; prose quality is human-reviewed

#### Scenario: Final roster remains geographically valid
- **WHEN** the discovered districts are validated and partitioned from a synthetic world
- **THEN** landmarks resolve on reachable walkable positions with declared spacing, each land cell has one owner and Voronoi propagation respects barriers/national borders

#### Scenario: Authored names are stable lore content
- **WHEN** a district name changes without its stable identity changing
- **THEN** discovery and references retain that identity and consumers read the authored name; lore appropriateness is human-reviewed rather than pinned by copied wording

