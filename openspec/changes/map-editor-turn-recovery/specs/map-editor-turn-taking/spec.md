# Spec Delta

## Purpose

Implement external AI turn-taking, directory watching, stale preview adoption and explicit reconnect/restart recovery. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Handoff grants one cooperative writer after persistence
External ownership SHALL be granted only after drafts are resolved and admitted manual saves finish successfully, while every mutation path is denied during the external turn.

#### Scenario: Flush failure
- **WHEN** a save fails while handoff waits for its queue
- **THEN** external ownership is not granted and persistent recovery information remains visible

#### Scenario: Mutation bypass attempts
- **WHEN** undo, keyboard deletion, paste, layout edits or generated-output publication is requested externally
- **THEN** the service rejects every mutation while browse/search/select/inspect/context copy remain available

### Requirement: External return adopts loadable disk state without rewriting history
Return to manual ownership SHALL reread current disk after stop confirmation and require authoring-load success, clearing obsolete history without serializing pre-external memory.

#### Scenario: Semantic repair
- **WHEN** external files contain an unreachable landmark but valid authoring structure
- **THEN** explicit return loads disk and enables repair with diagnostics without claiming game readiness

#### Scenario: Malformed return
- **WHEN** the external writer leaves invalid YAML or schema
- **THEN** return stays read-only with current-file diagnostics and does not rewrite files

### Requirement: Watching and reconnect retain truthful preview state
File events and connection changes SHALL publish only authoring-loadable candidates, preserve the last preview as stale on failure and require fresh state plus explicit resume before writes.

#### Scenario: Real filesystem replacement
- **WHEN** a selected node moves, is deleted, or its file becomes malformed then corrected through directory events
- **THEN** identity preserves view/selection where present; deletion explains cleared selection and malformed content retains visibly stale prior preview

#### Scenario: Unexpected write and old tab
- **WHEN** disk changes during manual mode or the service restarts while a tab retains commands
- **THEN** writes pause or reject, reload explains discarded drafts/history, and no write permission or command replay is restored locally

