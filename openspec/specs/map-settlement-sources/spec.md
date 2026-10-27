# map-settlement-sources Specification

## Purpose
Convert every settlement graph, prototype, binding, footprint and entry relationship to discovered YAML with complete game caller migration. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Settlement documents own complete local map declarations
Each discovered settlement document SHALL be the sole authority for its graph, location binding, footprint, entries, map options and map-owned scene associations.

#### Scenario: Discover another local map
- **WHEN** a supported settlement file is added for an existing geographic location
- **THEN** loading discovers it without Python registration and reverse navigation derives from its location reference alone

#### Scenario: Move a bound node
- **WHEN** a node with entry and art references moves
- **THEN** identity and direction remain unchanged and adapters derive the new binding from that document
