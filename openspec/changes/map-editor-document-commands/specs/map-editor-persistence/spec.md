# Spec Delta

## Purpose

Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Completed commands save exactly one validated document
Every admitted manual command SHALL validate and atomically replace exactly one owning document, acknowledging persistence only after replacement and rejecting obsolete session, turn or fingerprint state.

#### Scenario: One drag and failure
- **WHEN** a completed layout drag is saved, then a later save fails before replacement
- **THEN** the first operation remains saved, the failed target stays intact and no multi-file atomic claim is made

#### Scenario: Obsolete or uncertain save
- **WHEN** an old generation/fingerprint is submitted or durability becomes uncertain after replacement
- **THEN** stale writes reject and uncertainty pauses mutations pending reread without automatic resubmission

### Requirement: Drafts and history obey completed operation boundaries
Field drafts SHALL remain unsaved until completion, and undo/redo SHALL be validated autosaved operations confined to the current uninterrupted manual segment.

#### Scenario: Incomplete draft
- **WHEN** a numeric field is incomplete or Escape cancels an active tool
- **THEN** no file write occurs and Save does not force the draft

#### Scenario: Segment boundary
- **WHEN** a drag is undone/redone and then handoff or external adoption occurs
- **THEN** each drag/undo/redo is one saved operation and old history is cleared rather than replayed

