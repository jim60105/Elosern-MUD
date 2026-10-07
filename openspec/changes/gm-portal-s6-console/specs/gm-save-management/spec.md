## MODIFIED Requirements

### Requirement: Complete world save contents

A save SHALL contain the SQLite world database and generated art, excluding nested save archives, authored source, model files, logs and transcripts. Its manifest SHALL include id, label, kind, creation time, world clock tick and in-game date, player character name/location summary, latest applied migration per app, file count and size. Its world clock tick and in-game date SHALL be read from the copied database the save contains, not from a later live read, so the recorded in-game time always describes the world the save holds. IDs SHALL follow `YYYYMMDDTHHMMSS-<6 hex>` and every route and save function accepting an ID SHALL validate it before filesystem access. Only complete database/art pairs SHALL be listed.

#### Scenario: Save metadata and contents
- **WHEN** a snapshot is created from a temporary world database and art store containing a nested save archive
- **THEN** its manifest has every required metadata field, its database and live artwork are included, and the nested archive and excluded resources are absent

#### Scenario: Invalid and absent identities
- **WHEN** a route or save operation receives a malformed ID or a valid ID naming no save
- **THEN** it refuses the operation with `invalid_save_id` or `save_not_found` respectively and malformed input causes no filesystem traversal

#### Scenario: Snapshot-backed world clock
- **WHEN** the live world clock advances after a snapshot's database backup has completed and before its metadata is collected
- **THEN** the manifest's world clock tick and in-game date are the values contained in the save's copied database, and the console baseline derived from that save is that same tick

### Requirement: Protected save API and streaming download

S5 SHALL add GET/POST `/gm/api/saves/`, POST `/gm/api/saves/<id>/restore`, POST `/gm/api/saves/<id>/delete`, and GET `/gm/api/saves/<id>/download` using the existing `gm-portal-access-api` protection, envelope, CSRF and request-event contracts. List SHALL provide saves and latest restore result; creation SHALL create a manual save with a label. A completed manual save SHALL reset the process-local gm-developer-console baseline to the tick its own copied database represents, never a later live read; failed creation, including a refusal, SHALL not change the baseline. Manual-save creation SHALL keep its fail-fast contention behavior: an attempt that cannot take the snapshot serialization it needs SHALL return the existing `save_in_progress` refusal and SHALL NOT be queued behind another save or a console operation. Download success SHALL stream an uncompressed tar of the database, art and manifest instead of a JSON success body; failures before streaming SHALL use the JSON error envelope. Clients SHALL branch on the S5 error codes `save_not_found`, `invalid_save_id`, `save_incompatible`, `save_in_progress`, and `save_delete_forbidden`, not message text. Upload/import SHALL NOT be exposed.

#### Scenario: Access and CSRF matrix
- **WHEN** anonymous, ordinary, Developer and superuser accounts exercise all save routes, and privileged POSTs use missing, invalid or valid CSRF tokens
- **THEN** existing authentication/permission and CSRF outcomes apply to every route including downloads, and only privileged valid-token POSTs reach save operations

#### Scenario: JSON payloads and domain errors
- **WHEN** a privileged account lists, creates, requests restore or deletes a save, or encounters each defined S5 refusal
- **THEN** the existing JSON envelope carries real operation data or the stable error code, and list includes the latest restore result when present

#### Scenario: Download archive
- **WHEN** a privileged account downloads a completed save
- **THEN** a streamed uncompressed tar contains its database, manifest and art, without nested saves or whole-archive buffering

#### Scenario: Manual save baseline notification
- **WHEN** a manual save completes successfully and a console write follows at its saved tick, or the manual save fails
- **THEN** success suppresses an unnecessary auto_intervention save at that tick, failure leaves the previous baseline unchanged, and save API payload/status behavior remains otherwise unchanged

#### Scenario: Manual save provenance and contention
- **WHEN** the live clock advances after a manual save's database backup and before its metadata collection, or a second manual save is attempted while a snapshot-affecting operation is running
- **THEN** the completed save's reported in-game date and the console baseline are the tick contained in its copied database, the later player tick still requires a save, and the second attempt receives `save_in_progress` without creating a queued save

### Requirement: Operator saves page

The isolated GM SPA SHALL enable the S5 saves page and show label, kind badge, creation time, in-game date, player summaries and size, plus the latest restore result when present. It SHALL offer labelled creation, restore, download and confirmed deletion for manual saves only. The danger-style restore confirmation SHALL explain that current state is saved first, the server shuts down and the operator must start it again. It SHALL use the landed GM component/fetch boundary and remain usable offline without touching game-client contracts. S6 contextual console surfaces SHALL be available under gm-developer-console rather than being required to remain disabled.

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
- **THEN** the page remains usable with local saves, the GM-only route is enabled, S6 contextual entry points remain independently available and the game bundle/OOB remain unchanged
