# gm-save-management Specification

## Purpose
Provide recoverable local world-state save slots containing the database and generated art, with protected operator management and rollback-safe restoration before server startup.

## Requirements

### Requirement: Complete world save contents

A save SHALL contain the SQLite world database and generated art, excluding nested save archives, authored source, model files, logs and transcripts. Its manifest SHALL include id, label, kind, creation time, world clock tick and in-game date, player character name/location summary, latest applied migration per app, file count and size. IDs SHALL follow `YYYYMMDDTHHMMSS-<6 hex>` and every route and save function accepting an ID SHALL validate it before filesystem access. Only complete database/art pairs SHALL be listed.

#### Scenario: Save metadata and contents
- **WHEN** a snapshot is created from a temporary world database and art store containing a nested save archive
- **THEN** its manifest has every required metadata field, its database and live artwork are included, and the nested archive and excluded resources are absent

#### Scenario: Invalid and absent identities
- **WHEN** a route or save operation receives a malformed ID or a valid ID naming no save
- **THEN** it refuses the operation with `invalid_save_id` or `save_not_found` respectively and malformed input causes no filesystem traversal

### Requirement: Consistent snapshots without damaged art history

Only one snapshot SHALL run at a time; concurrent snapshot attempts SHALL fail with `save_in_progress`. A snapshot SHALL pause art draining, obtain a consistent SQLite online backup, mirror art with hardlink-and-copy-fallback, and resume art draining in `finally` on success or failure. Art publication SHALL use temporary-file atomic replacement so subsequent generation, seeding, cutout or cleanup cannot modify saved bytes. Failed creation SHALL remove partial directories and SHALL NOT leave a listed half-save.

#### Scenario: Live SQLite writes
- **WHEN** database writes occur while a snapshot uses the online backup API
- **THEN** the saved database is a consistent readable SQLite database rather than a partial file copy

#### Scenario: Art writes and link fallback
- **WHEN** art is mirrored while link creation fails for one file and later art writers replace or delete live files
- **THEN** copy fallback preserves that file, no art file is written mid-snapshot, and all saved image bytes remain unchanged

#### Scenario: Snapshot contention
- **WHEN** a second snapshot is attempted while the first is running
- **THEN** the second receives `save_in_progress` and does not create a second save

#### Scenario: Failure cleanup and drain resumption
- **WHEN** snapshot failure is injected during backup, art mirroring, manifest writing or either final rename
- **THEN** partial and newly published incomplete halves are removed, no half-save is listed, and ArtDrainScript is resumed

### Requirement: Retention and manual deletion

Each automatic kind SHALL retain at most `GM_AUTOSAVE_KEEP` saves after successful creation, defaulting to 10 with an environment override, deleting the oldest of that kind. A selected automatic restore target SHALL survive pre-restore snapshot retention until pending application finishes; pruning of its kind SHALL be deferred during that interval and completed at subsequent server startup. Manual saves SHALL never be automatically deleted. Explicit operator deletion SHALL require confirmation and SHALL be limited to manual saves, refusing automatic saves with `save_delete_forbidden`.

#### Scenario: Independent automatic retention
- **WHEN** new automatic saves exceed the configured limit with both automatic kinds and manual saves present
- **THEN** only the oldest saves of the over-limit automatic kind are removed from both stores and manual saves remain

#### Scenario: Default retention
- **WHEN** no environment override is set and eleven saves of one automatic kind are created
- **THEN** the newest ten remain

#### Scenario: Deletion policy
- **WHEN** the operator confirms deletion of a manual save or attempts deletion of an automatic save
- **THEN** the manual save's database and art halves are deleted, while the automatic save remains and returns `save_delete_forbidden`

### Requirement: Guarded restore request

Restore requests SHALL reject saves containing migrations unknown to current code with `save_incompatible`. An accepted request SHALL first snapshot the current state as `auto_restore`, then persist the selected save ID in `RESTORE_PENDING`, respond to the portal, and shut down through Evennia's shutdown path. It SHALL NOT replace live database files or mutate cached game fields. Failure of the pre-restore snapshot SHALL leave no pending restore and SHALL NOT shut down the server.

#### Scenario: Unknown migration refused
- **WHEN** a selected save contains a migration unknown to the running code
- **THEN** restore is refused with `save_incompatible` without pending marker, pre-restore snapshot or shutdown

#### Scenario: Ordered accepted request
- **WHEN** a compatible save is selected for restore
- **THEN** the current state is successfully saved as `auto_restore` before the marker is written, the response precedes shutdown, and live files are not replaced in-process

#### Scenario: Pre-restore backup fails
- **WHEN** the automatic snapshot fails
- **THEN** no restore marker is written and the server remains running with current state intact

#### Scenario: Oldest automatic restore target survives pre-save
- **WHEN** the oldest `auto_restore` save is selected while that kind is at the retention limit
- **THEN** the pre-restore snapshot does not delete the target, pending application can restore it, and deferred oldest-first retention runs only after application finishes at subsequent server startup

### Requirement: Pre-start restore with rollback and result

Both launchers SHALL apply pending restoration before `evennia migrate`. The pre-start tool SHALL run using only the standard library, verify the manifest and every saved file, refuse incompatible migrations, move originals aside and install the selected database and live art without consuming save archives. On success it SHALL remove moved-aside originals and the marker; on failure it SHALL roll originals back, remove the marker and allow normal startup. Both outcomes SHALL write `RESTORE_RESULT.json`. Older compatible saves SHALL migrate forward during normal startup. Captured in-progress art work SHALL be requeued through the existing lease reclaim.

#### Scenario: Successful restore and forward migration
- **WHEN** either launcher starts with a compatible older save pending
- **THEN** restoration runs before migration, the selected database and art become live, all save archives remain available, the marker and moved-aside originals are removed, a success result is written, and normal migration runs afterward

#### Scenario: Invalid saved input
- **WHEN** a pending save has a missing file, corrupt manifest or incompatible migrations
- **THEN** restoration fails without losing original database/art, removes the marker, writes a failure result and proceeds to normal startup

#### Scenario: Mid-replacement rollback
- **WHEN** an injected failure occurs after replacing one live half
- **THEN** the original database and art are both restored, the marker is removed, the selected archive remains intact, a failure result is written and normal startup can continue

#### Scenario: No pending request
- **WHEN** a launcher starts without a pending marker
- **THEN** the restore tool leaves live database/art unchanged and startup proceeds normally

#### Scenario: Lease reclaim after restoration
- **WHEN** restored art jobs were captured as in-progress
- **THEN** existing lease reclaim requeues them rather than leaving them permanently stuck

### Requirement: Protected save API and streaming download

S5 SHALL add GET/POST `/gm/api/saves/`, POST `/gm/api/saves/<id>/restore`, POST `/gm/api/saves/<id>/delete`, and GET `/gm/api/saves/<id>/download` using the existing `gm-portal-access-api` protection, envelope, CSRF and request-event contracts. List SHALL provide saves and latest restore result; creation SHALL create a manual save with a label. Download success SHALL stream an uncompressed tar of the database, art and manifest instead of a JSON success body; failures before streaming SHALL use the JSON error envelope. Clients SHALL branch on the S5 error codes `save_not_found`, `invalid_save_id`, `save_incompatible`, `save_in_progress`, and `save_delete_forbidden`, not message text. Upload/import SHALL NOT be exposed.

#### Scenario: Access and CSRF matrix
- **WHEN** anonymous, ordinary, Developer and superuser accounts exercise all save routes, and privileged POSTs use missing, invalid or valid CSRF tokens
- **THEN** existing authentication/permission and CSRF outcomes apply to every route including downloads, and only privileged valid-token POSTs reach save operations

#### Scenario: JSON payloads and domain errors
- **WHEN** a privileged account lists, creates, requests restore or deletes a save, or encounters each defined S5 refusal
- **THEN** the existing JSON envelope carries real operation data or the stable error code, and list includes the latest restore result when present

#### Scenario: Download archive
- **WHEN** a privileged account downloads a completed save
- **THEN** a streamed uncompressed tar contains its database, manifest and art, without nested saves or whole-archive buffering

### Requirement: Operator saves page

The isolated GM SPA SHALL enable the S5 saves page and show label, kind badge, creation time, in-game date, player summaries and size, plus the latest restore result when present. It SHALL offer labelled creation, restore, download and confirmed deletion for manual saves only. The danger-style restore confirmation SHALL explain that current state is saved first, the server shuts down and the operator must start it again. It SHALL use the landed GM component/fetch boundary and remain usable offline without enabling S6 or touching game-client contracts.

#### Scenario: Save management actions
- **WHEN** the operator opens the saves page with manual and automatic saves present
- **THEN** all required metadata and latest restore result render, creation/restore/download are available, and deletion is offered only for manual saves

#### Scenario: Confirmation and cancellation
- **WHEN** the operator opens a restore or manual-delete confirmation and cancels
- **THEN** no POST is sent, and the restore dialog uses danger styling and states pre-save, shutdown and manual restart consequences

#### Scenario: Code-based failure presentation
- **WHEN** an S5 operation fails with a domain error including `save_delete_forbidden`
- **THEN** the page surfaces that code and message without fabricating success or treating domain refusal as account permission denial

#### Scenario: Isolated offline delivery
- **WHEN** LLM/SD services are offline and the saves page is loaded directly or via navigation
- **THEN** the page remains usable with local saves, the GM-only route is enabled, S6 stays disabled and the game bundle/OOB remain unchanged

### Requirement: Save operational observability

Server-side save operations SHALL emit `save_created`, `save_failed`, `save_deleted`, `save_restore_requested`, `save_restored` and `save_restore_failed` through `world.observability`, each with `save` and `kind` in context. GM writes SHALL additionally emit `gm_action` with operator account and target identifiers. The standard-library pre-start restore tool SHALL report through stdout and the result file rather than importing the facade; server startup SHALL translate its result to the corresponding restore event. New production modules SHALL NOT enter the observability freeze list.

#### Scenario: Operation events
- **WHEN** creation succeeds/fails, a save is deleted or a restore request succeeds
- **THEN** the corresponding save event has save/kind context and GM writes carry account/target context in `gm_action`

#### Scenario: Startup outcome translation
- **WHEN** startup reads a successful or failed restore result
- **THEN** it emits `save_restored` or `save_restore_failed` respectively with save/kind context and the page can display the recorded outcome
