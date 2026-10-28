# Spec Delta

## Purpose

Implement continuous workspace file following: directory watching, own-write recognition, automatic adoption of loadable external changes, stale preview retention and reconnect/restart recovery, with no explicit AI handoff. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: External changes are followed without overwriting them
The service SHALL adopt every authoring-loadable external file change as the current snapshot without a handoff, and SHALL reject any editor write whose expected document fingerprint no longer matches disk.

#### Scenario: Loadable external change
- **WHEN** an external writer replaces a source document with loadable content while the editor holds no field draft
- **THEN** the new snapshot is published, undo history is cleared, view and selection are preserved by qualified identity, and no editor-side write occurs

#### Scenario: External change with an open draft
- **WHEN** a loadable external change arrives while the client holds an uncommitted field draft
- **THEN** the client keeps the draft until the user explicitly loads the new version, which discards the named draft and history, and a draft submitted against the old snapshot is rejected without changing disk

#### Scenario: Concurrent write race
- **WHEN** an external replacement lands between the editor reading a document and its save reaching the guard
- **THEN** the save is rejected with the external content intact and the editor reloads instead of merging or retrying

### Requirement: Watching and reconnect retain truthful preview state
File events and connection changes SHALL publish only authoring-loadable candidates, preserve the last preview as stale with writes rejected on failure and require a fresh session read before writes.

#### Scenario: Real filesystem replacement
- **WHEN** a selected node moves, is deleted, or its file becomes malformed then corrected through directory events
- **THEN** identity preserves view/selection where present; deletion explains cleared selection; malformed content retains a visibly stale prior preview with file/line diagnostics and rejected writes; the corrected content is adopted automatically

#### Scenario: Old tab and restart
- **WHEN** the service restarts while a tab retains commands or the connection drops
- **THEN** old-session writes are rejected, the tab shows the disconnected snapshot as stale and writes resume only after a fresh read, with no write permission or command replay restored locally

#### Scenario: Own saves do not become external changes
- **WHEN** two service saves receive delayed/coalesced real watcher events, followed by an external replacement at the same path
- **THEN** matching committed fingerprints preserve history, while the external fingerprint is adopted as an external change without blanket path/event suppression
