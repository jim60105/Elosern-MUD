# Spec Delta

## ADDED Requirements

### Requirement: District landmark positions are placed on the continent canvas
The editor SHALL project each district landmark's authored cell as a pair and its referent-derived continental centre, draw a district-selecting mark at that centre, and save a drag of a wilderness-cell landmark as exactly one owner-only landmark command; a landmark that references another object SHALL follow its referent and not be draggable.

#### Scenario: Landmark projection resolves through its referent
- **WHEN** the workspace projection is read for districts whose landmarks are a wilderness cell, a location, a settlement node with a resolvable frame, and an interior room
- **THEN** each row's landmark cell is an `[x, y]` pair or null, and its centre is the wilderness cell's centre, the location cell's centre, the node's world position, and null respectively

#### Scenario: Wilderness landmark drag writes one district command
- **WHEN** a wilderness-cell landmark mark is dragged on the continent and released on a different non-negative cell
- **THEN** exactly one `set_district_field` landmark command with the full four-key wilderness reference and one undo entry are accepted, only the districts document changes, and the partition becomes stale without being rewritten

#### Scenario: Persisted landmark position survives reload
- **WHEN** the edited workspace is reloaded after the drag
- **THEN** the landmark's authored cell equals the dropped cell, its mark is drawn at that cell's centre, and the inspector's numeric landmark fields show that cell

#### Scenario: Referenced landmark follows its referent
- **WHEN** a district landmark references a location or a settlement node
- **THEN** its mark is drawn at the referent's centre, is not draggable, and selecting it selects the district without writing any document

#### Scenario: Unfinished and refused placements
- **WHEN** a landmark command places the cell on water or an unreachable cell, or carries a negative cell
- **THEN** the water or unreachable placement is saved with its semantic diagnostic visible, while the negative cell is refused with no write and the mark returns to its saved position
