# map-editor-interaction Specification

## Purpose
Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces implementing the approved frontend design. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Workspace navigation and diagnostics identify source context
The workspace SHALL expose domain/map/source ownership, disambiguated search, textual selection/inspection and locatable diagnostic classes, with persistent save, file-sync, external-index and partition status and one priority banner for the highest-priority active failure.

#### Scenario: Duplicate name and hidden target
- **WHEN** search finds equal names in different maps and a diagnostic targets a hidden layer
- **THEN** parent/source distinguishes results and navigation reveals or offers the target with useful return context

#### Scenario: Unknown external readiness
- **WHEN** the external index is unavailable while a map is geometrically visible
- **THEN** persistent status explains unsupported external claims and refused deletion without blocking ordinary inspection/editing

### Requirement: Selection context is a copy-only external bridge
Explicit context copying SHALL produce credential-free plain text identifying selected objects, source paths, coordinate frames/units and currentness without executing or submitting work.

#### Scenario: Stale multi-selection
- **WHEN** objects from multiple sources are selected in a stale preview
- **THEN** copied text identifies every source/domain/qualified ID and the stale status without a token, ownership claim or AI action

### Requirement: Essential workspace operations have keyboard and reflow access
Essential controls SHALL support keyboard/non-drag operation, visible focus, meaningful non-color state and accessible zoomed desktop use with shortcuts scoped away from text editing.

#### Scenario: Keyboard and focus
- **WHEN** a user navigates diagnostics, edits a numeric control and closes a dialog using only the keyboard
- **THEN** relevant fields/triggers regain focus and input Delete/undo do not mutate selected map objects

#### Scenario: Supported viewports and zoom
- **WHEN** the workspace is used at 1451x790 and 2560x1440 and at 200 percent browser zoom with long names and dense diagnostics
- **THEN** essential operations and save/sync/stale status remain reachable, with the side columns disclosed as drawers when they cannot fit

### Requirement: Monster spawn objects are selectable, searchable and read-only
Each zone and site SHALL be a catalog object with a `monster_zone:<key>` or `monster_site:<key>` reference on the monster spawn layer, found by its species and variant names and keys, with no drag, edit or delete path.

#### Scenario: Species search reaches every place
- **WHEN** a species name, species key, variant name or variant key is searched against a synthetic section where several zones and sites can spawn it
- **THEN** each of those zones and sites is its own result, and no other monster object is

#### Scenario: Choosing a result reveals the layer
- **WHEN** a monster search result is chosen while the layer is hidden or another map is open
- **THEN** the continent opens with the layer shown, the object selected and the inspector focused

#### Scenario: No drag path
- **WHEN** a monster mark or polygon is dragged and arrow keys are pressed on the selection
- **THEN** no command is sent and every workspace file keeps its bytes

#### Scenario: No delete path
- **WHEN** deletion is requested for a selected monster object, by button or by Delete key
- **THEN** the delete explanation appears, no command is sent and every workspace file keeps its bytes

#### Scenario: Copied context
- **WHEN** context is copied for a selected monster object
- **THEN** the text names its reference, source file and coordinate frame

### Requirement: Monster spawn inspector shows what a place spawns
Selecting a zone or site SHALL show its label, reference, region, source file and read-only spawn facts, including one row per composition with its chance for a zone and one row per member with species, variant and count range.

#### Scenario: Region name follows the map document
- **WHEN** a synthetic region's display name changes in the workspace without a re-export, or a row names a region the world does not have
- **THEN** the inspector shows the current display name, or the region key when no region matches

#### Scenario: Zone chance
- **WHEN** a synthetic zone has pool weights that sum to more than one row's weight
- **THEN** each composition row shows `weight / total weight`, displayed only and never written

#### Scenario: Site recovery
- **WHEN** a one-shot synthetic site and a recoverable one are selected in turn
- **THEN** the first states that it is one-shot and the second shows its recovery time in a readable unit

#### Scenario: Readable game time
- **WHEN** game seconds are shown for values under a minute, whole hours and mixed days and hours
- **THEN** each renders in the largest fitting units with zero parts left out

#### Scenario: Text floor
- **WHEN** a monster object is inspected at 1451x790 and 2560x1440
- **THEN** every inspector row renders at 16 CSS pixels or larger

### Requirement: Monster spawn layer reports the artifact state
The layer SHALL follow the reference context status: a current section draws normally, a stale section still draws with a regeneration notice in the inspector, and a missing or undecodable artifact leaves the layer empty with the reason on its navigation row.

#### Scenario: Stale section
- **WHEN** the status is not current and the section has rows
- **THEN** the layer draws them and the inspector shows the stale notice with the regeneration command

#### Scenario: Unavailable section
- **WHEN** the status is not current and the section is empty
- **THEN** the layer draws nothing, the navigation row shows the status reason, and map editing stays available

#### Scenario: Selection across regeneration
- **WHEN** a selected monster object is absent from a newer snapshot
- **THEN** the selection is cleared and reported as removed by the existing selection rule
