## MODIFIED Requirements

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
