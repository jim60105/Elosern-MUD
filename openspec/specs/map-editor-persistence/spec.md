# map-editor-persistence Specification

## Purpose
Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Completed commands save exactly one validated document
Every admitted manual command SHALL validate and apply exactly one owning document's create, replace or remove effect, acknowledging persistence only after publication and rejecting obsolete session, presence or fingerprint state.

#### Scenario: One drag and failure
- **WHEN** a completed layout drag is saved, then a later save fails before replacement
- **THEN** the first operation remains saved, the failed target stays intact and no multi-file atomic claim is made

#### Scenario: Obsolete or uncertain save
- **WHEN** an old session generation or document fingerprint is submitted or durability becomes uncertain after replacement
- **THEN** stale writes reject and uncertainty pauses mutations pending reread without automatic resubmission

#### Scenario: Creation and removal preserve expected presence
- **WHEN** a create expects absence but a file has appeared, or remove expects a fingerprint that changed
- **THEN** the stale operation preserves current disk content and history; removal otherwise validates the complete remaining world and reference guards before deleting only its owner

#### Scenario: Removal failure and uncertainty
- **WHEN** a removal fails before unlink or its durability is uncertain after unlink
- **THEN** the first failure preserves the document and history while uncertainty pauses for reread without a blind retry or saved-state claim

### Requirement: Drafts and history obey completed operation boundaries
Field drafts SHALL remain unsaved until completion, and undo/redo SHALL be validated autosaved operations confined to the current uninterrupted manual segment.

#### Scenario: Incomplete draft
- **WHEN** a numeric field is incomplete or Escape cancels an active tool
- **THEN** no file write occurs and Save does not force the draft

#### Scenario: Segment boundary
- **WHEN** a drag is undone/redone and then an external change is adopted
- **THEN** each drag/undo/redo is one saved operation and old history is cleared rather than replayed

#### Scenario: Undo creation returns to absence
- **WHEN** a settlement or first layout document is created, undone and redone within one manual segment
- **THEN** undo removes that document and its derived association, redo recreates it only while absent, and no other source or layout document is changed

#### Scenario: Undo removal restores its guarded baseline
- **WHEN** a reference-free document is removed and its inverse is requested
- **THEN** the inverse recreates retained values/comments only if the target remains absent and current validation permits it; a rejected inverse changes neither disk nor history
