# art-gallery-generation Specification

## Purpose

Define per-image gallery generation jobs: one validated service seam that
validates and enqueues exactly one request keyed by a freshly minted image id,
generation failures reported (never gated) while the image server is down, an
idempotent startup prune that reclaims orphan gallery files and spent gallery
job records, and the `gallery_generate`/`gallery_settle` boundary events that
make every request and terminal settle observable.
## Requirements
### Requirement: One validated service seam requests every gallery image
`world/art/service.py::request_gallery_image(entity, *, binding=None, face_rect=None)` SHALL be the
only gameplay-reachable entry point that queues a gallery generation. It SHALL derive the subject
through the existing typed subject producers, SHALL re-check the canonical age pair for a character
subject exactly as the classic portrait ensure does, SHALL validate the supplied binding and face
rectangle through the `world/art/gallery.py` validators BEFORE any queue write, SHALL mint a fresh
uuid `image_id`, and SHALL enqueue exactly one job. A rejection SHALL raise a typed error at the
service boundary and SHALL leave no record, no file, and no card behind. The seam SHALL be
failure-isolated on every gameplay path exactly like the existing ensure seams: every rejection
raises BEFORE any record, file, or card is written, so a gameplay call site wrapped in the existing
post-commit failure-isolation pattern (wired by `gallery-autogen-retrofit`) never rolls back
creation, import, spawn, or movement, and an art failure only logs a bounded diagnostic.

#### Scenario: A valid request queues exactly one job
- **WHEN** a gallery image is requested for an eligible character subject with a valid binding and rect
- **THEN** exactly one gallery job record exists for a freshly minted image id, carrying the supplied binding and rect, and no card exists yet

#### Scenario: An invalid binding or rect never reaches the queue
- **WHEN** a gallery image is requested with a malformed binding or an out-of-bounds face rectangle
- **THEN** a typed error is raised, no record is created, and no prompt is rendered

#### Scenario: An ineligible subject is rejected deterministically
- **WHEN** a gallery image is requested for a character whose `age` or `apparent_age` is missing or non-integer, or for an entity carrying no portrait subject
- **THEN** a typed error is raised, no record is created, and no prompt content is produced

### Requirement: Generation while the image server is unreachable is a reported failure, never a gate
`request_gallery_image` SHALL NOT consult the connectivity probe and SHALL NOT import
`world.art.connectivity`; it enqueues unconditionally. When the configured sd-webui server is
unreachable, the claimed job SHALL settle `failed` with its existing bounded named error code, SHALL
append no card, and SHALL record that code and its timestamp on the subject's `GalleryRecord` so an
operator surface can report it. That surface SHALL exist: the recorded code SHALL be readable through
the gallery module's read-only erroring-subject accessor and SHALL be reported by the staff art
surfaces. A gallery settle that successfully appends a card SHALL clear the subject's recorded error
as part of the same settle, so the recorded code always describes the subject's LAST generation
attempt and never a stale one. The clear SHALL happen after the card append commits and under the
established `queue_lock -> gallery_lock` order; a failure to clear SHALL NOT rewrite the settle's
outcome, because the appended card is the authoritative publish. Nothing in the resolution of an
existing card SHALL depend on any generation having succeeded, so a fully offline deployment stays
playable.

#### Scenario: An offline request reports a bounded failure and no card
- **WHEN** a gallery image is requested while the image server refuses connections
- **THEN** the job settles `failed` with the named connection error code, the gallery holds no new card, and the error code is readable on the gallery record

#### Scenario: A later success clears the recorded error
- **WHEN** a subject whose record carries a bounded error code has a gallery job settle `done` with a card appended
- **THEN** the card is present and the record's error code and timestamp are `None`

#### Scenario: A failed settle after a success records the new code
- **WHEN** a subject with a cleared error has a later gallery job settle `failed`
- **THEN** the record carries the new bounded code and its timestamp, and every existing card is untouched

#### Scenario: Existing cards keep resolving with every external service down
- **WHEN** the image server and every LLM service are unreachable and a subject already holds cards
- **THEN** the stored cards are unchanged and remain readable

#### Scenario: The connectivity import boundary still holds
- **WHEN** the package-wide import-boundary test parses every production module under `world/art/`
- **THEN** no module other than `connectivity.py` imports `world.art.connectivity`

### Requirement: Interrupted gallery generations are reclaimed at startup
The engine SHALL run one idempotent startup prune that deletes every file under the store root's
`gallery/` tree that no card of any `GalleryRecord` references, and deletes every gallery job record
that can never be claimed or published again (a record whose subject no longer resolves, or whose
status is neither `pending` nor `in_progress`); a lease-expired `in_progress` job is RETAINED —
reclaiming it to `pending` is the shared queue's lease-reclaim job, not the prune's, so a gallery
job whose worker died is retried rather than silently dropped. Every deletion SHALL resolve through
the single store-root confinement helper, so no path outside `ART_STORE_ROOT` is ever unlinked. A
prune failure SHALL be a bounded diagnostic that never aborts startup, and a prune SHALL NEVER
delete a file a card references.

#### Scenario: An orphan gallery file is reclaimed
- **WHEN** the server starts with a file under `gallery/` that no card references
- **THEN** that file is deleted and every referenced file is left in place

#### Scenario: The prune is idempotent and non-destructive
- **WHEN** the prune runs twice in a row on a store whose every gallery file is referenced
- **THEN** nothing is deleted on either pass and no error is raised

#### Scenario: A prune failure never aborts startup
- **WHEN** the gallery tree cannot be read or a deletion raises
- **THEN** a bounded diagnostic is logged and startup continues

### Requirement: Gallery generation emits its boundary events
The engine SHALL emit one `gallery_generate` info event through the `world.observability` facade
when a gallery job is enqueued, and one `gallery_settle` info event when a gallery job reaches a
terminal settle, carrying the business ids `subject`, `image_id`, and `kind` in `context`, plus the
settled `status` and bounded `reason` code on settle. Logging SHALL go exclusively through the
facade so `tools.observability_lint` passes with no waiver.
Gallery jobs flow through the existing claim machinery unchanged, so a gallery job additionally
produces the queue-level `sd_job_claim`/`sd_job_settled` events keyed by the job record; the
`gallery_*` pair is the per-image business stream operators SHALL count.

#### Scenario: A successful gallery generation leaves a generate/settle pair
- **WHEN** one gallery image is requested and its job settles `done`
- **THEN** one `gallery_generate` and one `gallery_settle` event are logged with the subject, image id, kind, and the settled status

#### Scenario: A failed gallery generation reports its bounded reason
- **WHEN** a gallery job settles `failed`
- **THEN** the `gallery_settle` event carries the failed status and the bounded error code as its reason

