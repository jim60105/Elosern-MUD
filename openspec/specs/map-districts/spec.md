# map-districts Specification

## Purpose
Provide immutable exploration districts with one reachable landmark each and lighting derived only from existing visited-node knowledge.

## Requirements

### Requirement: Every map district has one canonical reachable landmark
Each district SHALL resolve one qualified landmark to a reachable walkable position, with unique identities, declared minimum Voronoi spacing and region membership only for region districts.

#### Scenario: Invalid landmarks fail authoring validation
- **WHEN** sea, blocked terrain, absent settlement nodes, duplicate landmarks or insufficient spacing are declared
- **THEN** runtime validation rejects and names each invalid declaration; authoring retains saveable reachability diagnostics

#### Scenario: Stable landmark movement
- **WHEN** a settlement landmark moves with its stable node identity
- **THEN** the runtime canonical landmark follows its new binding while district lighting still reads existing visited-node knowledge

#### Scenario: Deep forest has one discovery landmark
- **WHEN** a region district spans nominal national claims
- **THEN** its one qualified landmark resolves independently of national borders and discovery still requires that landmark's canonical visited identity

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

### Requirement: District lighting is derived from completed rites
A district SHALL be lit if and only if the player character's rite record holds at least one completed rite for it and the district registry declares it. Reading lighting SHALL introduce no persistent state. An unreadable rite record SHALL raise from the strict read and SHALL degrade to no lit district with a warning in the read used by presentation and travel.

#### Scenario: A visit lights nothing
- **WHEN** the player visits a landmark's canonical node and completes no rite
- **THEN** the district remains unlit

#### Scenario: A completed rite lights only its district
- **WHEN** the rite record holds one completion for one district and one for a key the registry does not declare
- **THEN** exactly the declared district is lit, and no attribute was created by reading

#### Scenario: Unreadable record
- **WHEN** the rite record violates its envelope
- **THEN** the strict read raises the named record error, and the degrading read returns no lit district and logs one warning
