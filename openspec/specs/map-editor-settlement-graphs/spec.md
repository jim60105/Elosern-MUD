# map-editor-settlement-graphs Specification

## Purpose
Implement complete settlement creation, node/prototype editing, directed roads and physical route inspection. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Settlement tools preserve stable graph identity and explicit direction
Settlement tools SHALL create and edit maps, nodes/prototypes and directed roads through typed single-document commands while retaining existing IDs and authored directions when positions change.

#### Scenario: Moved referenced node
- **WHEN** a selected node with gate/interior/district/art dependents moves using drag or numeric input
- **THEN** one saved operation retains ID/direction and all dependent selectors still resolve the moved object

#### Scenario: Two-way street
- **WHEN** the user chooses bidirectional creation with endpoint/direction/bend controls
- **THEN** two inspectable directed entries are saved together in the settlement document with core-derived lengths

#### Scenario: Multi-selection and new map
- **WHEN** a list-selected group moves or an empty local map is created for a location
- **THEN** group mutation stays in one document and the empty graph remains diagnosed unfinished rather than playable
