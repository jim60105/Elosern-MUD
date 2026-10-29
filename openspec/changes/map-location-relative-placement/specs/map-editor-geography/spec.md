## MODIFIED Requirements

### Requirement: Continental authored inputs have direct and explicit editing controls
The editor SHALL edit continental geometry/classifiers, locations, districts/landmarks and settlement footprints through labelled single-document commands, with location moves translating derived settlement geometry in one undoable operation and footprint controls retaining absolute-cell inputs without editable binding coordinates.

#### Scenario: Move river point
- **WHEN** a river control point is dragged or entered numerically
- **THEN** release/confirmation saves one command, terrain preview derives from core inputs and dependent partition status becomes stale

#### Scenario: Unbuilt location
- **WHEN** a valid geographic location is created without a local map
- **THEN** it is editable and searchable with explicit absent-local-map state and no fabricated rooms

#### Scenario: Footprint and district controls
- **WHEN** a footprint cell or stable district landmark is edited using keyboard controls
- **THEN** only its owning document changes and references/semantic diagnostics remain visible

#### Scenario: EDIT-DRAG one location command and undo entry
- **WHEN** a user drags a location with a settlement on the continent and releases on a valid cell
- **THEN** exactly one location-cell command and one undo entry are accepted, only locations.yaml changes, the reloaded core translates its derived frame/mask/gates, and the partition becomes stale without being rewritten

#### Scenario: EDIT-HISTORY drag undo and redo
- **WHEN** the completed location drag is undone once and redone once
- **THEN** the location and all derived settlement geometry return to their prior and moved positions respectively, with each history action writing only locations.yaml

#### Scenario: EDIT-FOOTPRINT absolute cell boundary
- **WHEN** an absolute cell west or south of the current mask is filled and the edited world reloads
- **THEN** only the settlement document changes, the saved offset accounts for growth, existing hash cells stay at their previous absolute positions and the selected absolute cell becomes filled

#### Scenario: EDIT-BINDING removed command surface
- **WHEN** the continent inspector is used for a location with a settlement or an old set_binding command is submitted
- **THEN** no binding input or payload builder is exposed, the obsolete command is refused as unknown with no write, and existing location/footprint controls remain available

#### Scenario: EDIT-BROWSER real workflow and restart
- **WHEN** the real browser drags a synthetic settlement-backed location, then performs undo/redo and restarts the editor service
- **THEN** observed command traffic and file digests establish one owner per operation and a fresh core load reports the translated node world positions, mask and approach cells from the persisted location
