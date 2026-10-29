# map-editor-settlement-graphs Specification

## Purpose
Implement complete settlement creation, node/prototype editing, directed roads and physical route inspection. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Settlement tools preserve stable graph identity and explicit direction
Settlement tools SHALL create and edit graphs through typed single-document commands, deriving the local anchor from the unique anchor_room and retaining IDs and authored directions as node positions change.

#### Scenario: Moved referenced node
- **WHEN** a selected node with gate/interior/district/art dependents moves using drag or numeric input
- **THEN** one saved operation retains ID/direction and all dependent selectors still resolve the moved object

#### Scenario: Two-way street
- **WHEN** the user chooses bidirectional creation with endpoint/direction/bend controls
- **THEN** two inspectable directed entries are saved together in the settlement document with core-derived lengths

#### Scenario: Multi-selection and new map
- **WHEN** a list-selected group moves or an empty local map is created for a location
- **THEN** group mutation stays in one document and the empty graph remains diagnosed unfinished rather than playable

#### Scenario: GRAPH-CREATE location-only frame selection
- **WHEN** create_settlement is given settlement identity, location_id and existing map options, without either former anchor-coordinate argument
- **THEN** it creates only that settlement document with no binding; the empty graph has unavailable world geometry until its first created node becomes anchor_room with anchor_key equal to location_ref

#### Scenario: GRAPH-ANCHOR node drag meaning
- **WHEN** the anchor_room alone moves locally by `(30,50)` metres
- **THEN** one settlement command/undo entry changes its position, the location and footprint stay fixed, the anchor remains at the location cell centre and every untouched node's world position shifts by `(-30,-50)` metres

#### Scenario: GRAPH-FIRST-GATE default entry
- **WHEN** a wilderness gate is created in a settlement with no wilderness entry
- **THEN** that command writes a single-hash mask with offset `(0,0)` and the selected destination/direction in the same settlement document, placing its point entrance at the current location cell on reload
