# map-editor-geography Specification

## Purpose
Implement complete manual continental geometry, location, district, footprint and binding authoring. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Continental authored inputs have direct and explicit editing controls
The editor SHALL retain labelled single-document controls for continental inputs, locations, districts and absolute-cell footprints, edit authored stem and arm control points through move/insert/remove with coherent shared-crotch history, and support empty ridge-pass lists.

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
- **THEN** observed command traffic and file digests establish one owner per operation and a fresh core load reports translated node world positions, mask and approach cells from the persisted location

#### Scenario: Empty-pass editing and branch retention
- **WHEN** a synthetic paired-branch continent with zero passes receives add/set/remove pass commands below the crotch, including removal of its last pass
- **THEN** each accepted operation writes only the continent, returning to an empty pass list remains editable with a current preview, and both branches remain preserved and displayed without pass exemptions on their walls

#### Scenario: Hand-authored branches survive unrelated edits
- **WHEN** stem and arm interior control points are moved, inserted, removed, undone, redone and reloaded in a synthetic ridge document
- **THEN** each accepted operation writes only the continent, route values/comments survive, history restores exact prior bytes and preview/capture follow the edited crests

#### Scenario: Shared crotch editing
- **WHEN** any of the three shared crotch control points is moved, or its deletion is requested
- **THEN** movement updates all three points in one continent command and undo entry, while shared-point deletion is refused without a write or gap

#### Scenario: Crest controls replace formula inputs
- **WHEN** a crest route is selected in the editor or an old periodic field command is submitted
- **THEN** route handles and cell-labelled numeric/insert/remove controls are available, political lines remain noneditable derived output, and retired field requests reject without writes

#### Scenario: Branch commands are outside the supported surface
- **WHEN** a request submits a set-ridge-branch or remove-ridge-branch command
- **THEN** it is refused as unknown without writes; existing move/insert/remove control-point commands edit authored routes instead

### Requirement: District landmark positions are placed on the continent canvas
The editor SHALL project each district landmark's authored cell as a pair and its referent-derived continental centre, draw a district-selecting mark at that centre on a dedicated landmark layer that is hidden by default, and save a drag of a wilderness-cell landmark as exactly one owner-only landmark command; a landmark that references another object SHALL follow its referent and not be draggable.

#### Scenario: Landmark projection resolves through its referent
- **WHEN** the workspace projection is read for districts whose landmarks are a wilderness cell, a location, a settlement node with a resolvable frame, and an interior room
- **THEN** each row's landmark cell is an `[x, y]` pair or null, and its centre is the wilderness cell's centre, the location cell's centre, the node's world position, and null respectively

#### Scenario: Landmark layer is hidden by default
- **WHEN** the continent canvas opens and the author then shows or hides the landmark layer
- **THEN** no landmark mark is drawn until the landmark layer is shown, toggling it shows or hides only landmark marks, and a district selected through its mark stays selected while its district list entry remains visible

#### Scenario: Wilderness landmark drag writes one district command
- **WHEN** a wilderness-cell landmark mark is dragged on the continent and released on a different non-negative cell
- **THEN** exactly one `set_district_field` landmark command with the full four-key wilderness reference and one undo entry are accepted, only the districts document changes, and the partition becomes stale without being rewritten

#### Scenario: Persisted landmark position survives reload
- **WHEN** the edited workspace is reloaded after the drag
- **THEN** the landmark's authored cell equals the dropped cell, its mark is drawn at that cell's centre, and the inspector's numeric landmark fields show that cell

#### Scenario: Referenced landmark follows its referent
- **WHEN** a district landmark references a location or a settlement node
- **THEN** its mark is drawn at the referent's centre and is not draggable, and selecting its district writes no document and marks that landmark selected

#### Scenario: Selecting a landmark mark selects its district
- **WHEN** a landmark mark is clicked on the continent canvas
- **THEN** its district becomes the selection and the district inspector opens, with no command sent

#### Scenario: Unfinished and refused placements
- **WHEN** a landmark command places the cell on water or an unreachable cell, or carries a negative cell
- **THEN** the water or unreachable placement is saved with its semantic diagnostic visible, while the negative cell is refused with no write and the mark returns to its saved position
