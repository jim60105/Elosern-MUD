# Spec Delta

## ADDED Requirements

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
