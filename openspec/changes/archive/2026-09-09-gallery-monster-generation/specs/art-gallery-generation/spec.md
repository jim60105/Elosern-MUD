## MODIFIED Requirements

### Requirement: One validated service seam requests every gallery image
`world/art/service.py::request_gallery_image(entity_or_subject, *, fields=(), custom_prompt="", binding=None, face_rect=None)`
SHALL be the only gameplay-reachable entry point that queues a gallery generation, and it SHALL serve
EVERY gallery-bearing subject kind through one path. It SHALL accept either an entity carrying a
portrait subject or an already-derived art subject, and SHALL derive the subject through the existing
typed subject producers.

Every precondition it enforces SHALL be read from the subject kind's capability declaration rather
than from a comparison against a particular kind:

- it SHALL re-check the canonical age pair exactly as the classic portrait ensure does for a kind that
  declares the age precondition, and SHALL NOT read age attributes for a kind that does not;
- it SHALL validate a supplied field selection against the catalog for a kind that declares
  field-selection support, and SHALL reject a non-empty selection with a typed error for a kind that
  does not;
- it SHALL accept free-form prompt text for a kind that declares free-text support, and SHALL reject
  non-empty text with a typed error for a kind that does not;
- it SHALL validate a supplied binding for a kind that declares binding support, and SHALL reject a
  non-`None` binding with a typed error for a kind that does not.

An argument naming a capability the kind does not declare SHALL be REJECTED, never silently dropped,
so a card's recorded provenance can never claim data the request could not have used. The seam SHALL
validate the face rectangle through the `world/art/gallery.py` validators BEFORE any queue write, SHALL
mint a fresh uuid `image_id`, and SHALL enqueue exactly one job. A subject whose kind declares no
gallery SHALL be refused. A rejection SHALL raise a typed error at the service boundary and SHALL leave
no record, no file, and no card behind. The seam SHALL be failure-isolated on every gameplay path
exactly like the existing ensure seams: every rejection raises BEFORE any record, file, or card is
written, so a gameplay call site wrapped in the existing post-commit failure-isolation pattern never
rolls back creation, import, spawn, or movement, and an art failure only logs a bounded diagnostic.

#### Scenario: A valid request queues exactly one job
- **WHEN** a gallery image is requested for an eligible character subject with a valid binding and rect
- **THEN** exactly one gallery job record exists for a freshly minted image id, carrying the supplied binding and rect, and no card exists yet

#### Scenario: A monster subject queues one job through the same seam
- **WHEN** a gallery image is requested for a registered monster subject with no field selection, no free text, and no binding
- **THEN** exactly one gallery job record exists for that subject, no age attribute is read, and the description is the registry-driven monster description

#### Scenario: An invalid binding or rect never reaches the queue
- **WHEN** a gallery image is requested with a malformed binding or an out-of-bounds face rectangle
- **THEN** a typed error is raised, no record is created, and no prompt is rendered

#### Scenario: An undeclared capability is rejected, never ignored
- **WHEN** a gallery image is requested for a monster subject with a non-empty field selection, a non-empty custom prompt, or a binding
- **THEN** a typed error is raised naming the undeclared capability, no record is created, and no prompt is rendered

#### Scenario: An ineligible subject is rejected deterministically
- **WHEN** a gallery image is requested for a character whose `age` or `apparent_age` is missing or non-integer, or for an entity carrying no portrait subject
- **THEN** a typed error is raised, no record is created, and no prompt content is produced

#### Scenario: A kind declaring no gallery is refused at the seam
- **WHEN** a gallery image is requested for a scene subject
- **THEN** a typed error is raised and no job record is created
