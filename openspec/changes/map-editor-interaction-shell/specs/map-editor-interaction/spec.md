# Spec Delta

## Purpose

Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces with a specialist visual-design handoff. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Workspace navigation and diagnostics identify source context
The workspace SHALL expose domain/map/source ownership, disambiguated search, textual selection/inspection and locatable diagnostic classes with persistent permission, persistence and preview status.

#### Scenario: Duplicate name and hidden target
- **WHEN** search finds equal names in different maps and a diagnostic targets a hidden layer
- **THEN** parent/source distinguishes results and navigation reveals or offers the target with useful return context

#### Scenario: Unknown external readiness
- **WHEN** the external index is unavailable while a map is geometrically visible
- **THEN** persistent status explains unsupported external claims and disabled deletion without disabling ordinary inspection/editing

### Requirement: Selection context is a copy-only external bridge
Explicit context copying SHALL produce credential-free plain text identifying selected objects, source paths, units, currentness and the cooperative ownership agreement without executing or submitting work.

#### Scenario: Stale multi-selection
- **WHEN** objects from multiple sources are selected in a stale preview during external ownership
- **THEN** copied text identifies every source/domain/qualified ID and stale/turn status without a token or AI action

### Requirement: Essential workspace operations have keyboard and reflow access
Essential controls SHALL support keyboard/non-drag operation, visible focus, meaningful non-color state and accessible compact/zoomed desktop use with shortcuts scoped away from text editing.

#### Scenario: Keyboard and focus
- **WHEN** a user navigates diagnostics, edits a numeric control and closes a dialog using only the keyboard
- **THEN** relevant fields/triggers regain focus and input Delete/undo do not mutate selected map objects

#### Scenario: Compact zoom
- **WHEN** the workspace is used at 960x720 or 200 percent browser zoom with long names and dense diagnostics
- **THEN** essential operations and ownership/save/stale status remain reachable through reflow or disclosure

