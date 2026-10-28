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
