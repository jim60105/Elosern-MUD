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
`world/art/service.py::request_gallery_image(entity_or_subject, *, fields=(), custom_prompt="", binding=None, face_rect=None)`
SHALL be the only gameplay-reachable entry point that queues a gallery generation, and it SHALL serve
EVERY gallery-bearing subject kind through one path. It SHALL accept either an entity carrying a
portrait subject or an already-derived art subject, and SHALL derive the subject through the existing
typed subject producers.

#### Scenario: A valid request queues exactly one job
- **WHEN** a gallery image is requested for an eligible character subject with a valid binding and rect
- **THEN** exactly one gallery job record exists for a freshly minted image id, carrying the supplied binding and rect, and no card exists yet

#### Scenario: A monster subject queues one job through the same seam
- **WHEN** a gallery image is requested for a registered monster subject with no field selection, no free text, and no binding
- **THEN** exactly one gallery job record exists for that subject, no age attribute is read, and the description is the registry-driven monster description

#### Scenario: An invalid binding or rect never reaches the queue
- **WHEN** a gallery image is requested with a malformed binding or an out-of-bounds face rectangle
- **THEN** a typed error is raised, no record is created, and no prompt is rendered

#### Scenario: A non-square rect never reaches the queue
- **WHEN** a gallery image is requested with a rect that passes the bounds rules but is not pixel-square for the configured portrait render size — including one field-for-field equal to the shared default constant
- **THEN** a typed error is raised, no record is created, and no prompt is rendered

#### Scenario: A null rect queues and takes the fitted default
- **WHEN** a gallery image is requested with `face_rect=None` and its job settles
- **THEN** the queued job carries no rect and the appended card's rect is the fitted default square for the settled image's recorded pixel size

#### Scenario: An undeclared capability is rejected, never ignored
- **WHEN** a gallery image is requested for a monster subject with a non-empty field selection, a non-empty custom prompt, or a binding
- **THEN** a typed error is raised naming the undeclared capability, no record is created, and no prompt is rendered

#### Scenario: An ineligible subject is rejected deterministically
- **WHEN** a gallery image is requested for a character whose `age` or `apparent_age` is missing or non-integer, or for an entity carrying no portrait subject
- **THEN** a typed error is raised, no record is created, and no prompt content is produced

#### Scenario: A kind declaring no gallery is refused at the seam
- **WHEN** a gallery image is requested for a scene subject
- **THEN** a typed error is raised and no job record is created

#### Scenario: Preconditions are read from the capability declaration
- **WHEN** the seam enforces any precondition
- **THEN** it SHALL be read from the subject kind's capability declaration rather than from a comparison against a particular kind
- **AND** it SHALL re-check the canonical age pair exactly as the classic portrait ensure does for a kind that declares the age precondition, and SHALL NOT read age attributes for a kind that does not
- **AND** it SHALL validate a supplied field selection against the catalog for a kind that declares field-selection support, and SHALL reject a non-empty selection with a typed error for a kind that does not
- **AND** it SHALL accept free-form prompt text for a kind that declares free-text support, and SHALL reject non-empty text with a typed error for a kind that does not
- **AND** it SHALL validate a supplied binding for a kind that declares binding support, and SHALL reject a non-`None` binding with a typed error for a kind that does not

#### Scenario: An undeclared-capability argument is rejected, never silently dropped
- **WHEN** a request argument names a capability the kind does not declare
- **THEN** it SHALL be REJECTED, never silently dropped, so a card's recorded provenance can never claim data the request could not have used

#### Scenario: The face rectangle is validated before any queue write
- **WHEN** a face rectangle is supplied
- **THEN** the seam SHALL validate it through the `world/art/gallery.py` validators BEFORE any queue write, against the subject kind's planned render pixel size (the configured portrait dimensions), so a rectangle that is not pixel-square for the image about to be rendered raises before the queue record exists — with no value exemption for any rect, including the shared default constant
- **AND** a `None` rect stays legal and takes the fitted default at append

#### Scenario: A successful request mints one id and one job; rejections leave nothing behind
- **WHEN** the seam accepts a request
- **THEN** it SHALL mint a fresh uuid `image_id` and SHALL enqueue exactly one job
- **AND** a subject whose kind declares no gallery SHALL be refused
- **AND** a rejection SHALL raise a typed error at the service boundary and SHALL leave no record, no file, and no card behind

#### Scenario: The seam is failure-isolated on every gameplay path
- **WHEN** the seam rejects on a gameplay path
- **THEN** it behaves exactly like the existing ensure seams: every rejection raises BEFORE any record, file, or card is written, so a gameplay call site wrapped in the existing post-commit failure-isolation pattern never rolls back creation, import, spawn, or movement, and an art failure only logs a bounded diagnostic

### Requirement: Generation while the image server is unreachable is a reported failure, never a gate
`request_gallery_image` SHALL NOT consult the connectivity probe and SHALL NOT import
`world.art.connectivity`; it enqueues unconditionally. When the configured sd-webui server is
unreachable, the claimed job SHALL settle `failed` with its existing bounded named error code, SHALL
append no card, and SHALL record that code and its timestamp on the subject's `GalleryRecord` so an
operator surface can report it.

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

#### Scenario: The operator surface exposes the recorded error
- **WHEN** a subject's `GalleryRecord` carries a recorded error code
- **THEN** it SHALL be readable through the gallery module's read-only erroring-subject accessor and SHALL be reported by the staff art surfaces

#### Scenario: A successful settle clears the recorded error in the same settle
- **WHEN** a gallery settle successfully appends a card
- **THEN** it SHALL clear the subject's recorded error as part of the same settle, so the recorded code always describes the subject's LAST generation attempt and never a stale one
- **AND** the clear SHALL happen after the card append commits and under the established `queue_lock -> gallery_lock` order
- **AND** a failure to clear SHALL NOT rewrite the settle's outcome, because the appended card is the authoritative publish

#### Scenario: Card resolution never depends on a successful generation
- **WHEN** a fully offline deployment resolves existing cards
- **THEN** nothing in the resolution of an existing card SHALL depend on any generation having succeeded, so the deployment stays playable

### Requirement: Interrupted gallery generations are reclaimed at startup
The engine SHALL run one idempotent startup prune that deletes every file under the store root's
`gallery/` tree that no card of any `GalleryRecord` references, and deletes every gallery job
record that can never be claimed or published again (a record whose subject no longer resolves,
or whose status is neither `pending` nor `in_progress`). A prune SHALL NEVER delete a file a card
references, and a prune failure SHALL be a bounded diagnostic that never aborts startup.

#### Scenario: An orphan gallery file is reclaimed
- **WHEN** the server starts with a file under `gallery/` that no card references
- **THEN** that file is deleted and every referenced file is left in place

#### Scenario: The prune is idempotent and non-destructive
- **WHEN** the prune runs twice in a row on a store whose every gallery file is referenced
- **THEN** nothing is deleted on either pass and no error is raised

#### Scenario: A prune failure never aborts startup
- **WHEN** the gallery tree cannot be read or a deletion raises
- **THEN** a bounded diagnostic is logged and startup continues

#### Scenario: A lease-expired in-progress job is retained
- **WHEN** the prune meets a lease-expired `in_progress` gallery job
- **THEN** the job is RETAINED — reclaiming it to `pending` is the shared queue's lease-reclaim job, not the prune's, so a gallery job whose worker died is retried rather than silently dropped

#### Scenario: Every deletion resolves through the store-root confinement helper
- **WHEN** the prune deletes a file or a job record
- **THEN** the deletion SHALL resolve through the single store-root confinement helper, so no path outside `ART_STORE_ROOT` is ever unlinked

### Requirement: Gallery generation emits its boundary events
The engine SHALL emit one `gallery_generate` info event through the `world.observability` facade
when a gallery job is enqueued, and one `gallery_settle` info event when a gallery job reaches a
terminal settle, carrying the business ids `subject`, `image_id`, and `kind` in `context`, plus
the settled `status` and bounded `reason` code on settle.

#### Scenario: A successful gallery generation leaves a generate/settle pair
- **WHEN** one gallery image is requested and its job settles `done`
- **THEN** one `gallery_generate` and one `gallery_settle` event are logged with the subject, image id, kind, and the settled status

#### Scenario: A failed gallery generation reports its bounded reason
- **WHEN** a gallery job settles `failed`
- **THEN** the `gallery_settle` event carries the failed status and the bounded error code as its reason

#### Scenario: Logging goes exclusively through the observability facade
- **WHEN** gallery boundary events are logged
- **THEN** logging SHALL go exclusively through the facade so `tools.observability_lint` passes with no waiver

#### Scenario: Queue-level events accompany the per-image business stream
- **WHEN** a gallery job flows through the existing claim machinery unchanged
- **THEN** it additionally produces the queue-level `sd_job_claim`/`sd_job_settled` events keyed by the job record, and the `gallery_*` pair is the per-image business stream operators SHALL count
