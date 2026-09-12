# Delta spec: gallery-card-update-api (art-gallery-model)

## ADDED Requirements

### Requirement: Existing cards accept in-place face-rect and binding updates through the sole writer

`world/art/gallery.py` SHALL expose `update_card_face_rect(subject, image_id,
face_rect)` and `update_card_binding(subject, image_id, binding)` as the ONLY
mutations of an existing card's fields. Each SHALL run under the existing
`gallery_lock`, locate the entry through the tolerant card read (a missing or
malformed match SHALL raise the same typed `GalleryRecordError` form
`remove_card` raises for a miss), validate the incoming value through
`validate_face_rect` / `validate_binding` before any write, and store it
verbatim — no file write, no crop, no second image, and no change to card
order, `default_image_id`, or any other card field.
`update_card_binding` SHALL additionally refuse a subject kind whose capability
declaration supports no bindings with the capability-naming typed error the
service seam raises, and SHALL accept an explicit `None` binding as an unbind.
Each successful update SHALL emit one `gallery_card_updated` facade event
carrying `subject`, `image_id`, `kind`, and the updated field in `context`.

#### Scenario: A stored face rect update equals the submitted rect exactly

- **WHEN** `update_card_face_rect` is called with a valid rect for an existing card
- **THEN** the card's stored rect matches field-for-field, every other card field and the record's default are unchanged, and no file on disk is touched

#### Scenario: A binding update on a binding-incapable kind is refused

- **WHEN** `update_card_binding` names a monster-kind subject with a non-null binding
- **THEN** the typed capability error is raised, the card is unchanged, and no event fires

#### Scenario: An unknown or malformed card id refuses

- **WHEN** either writer names an image_id no valid card carries
- **THEN** the typed error mirrors the `remove_card` miss form and the record is byte-for-byte unchanged

#### Scenario: The sole-writer rule still holds after the update seam ships

- **WHEN** the production modules are inspected for gallery-card writes
- **THEN** every card mutation still lives in `world/art/gallery.py`

### Requirement: One public read-only seam resolves a serialized subject key to subject and entity

`world/art/service.py` SHALL expose `resolve_gallery_subject_by_key(subject_key)
-> (ArtSubject, entity_or_None)`: registry-backed kinds re-validate through the
kind's typed producer; character-kind keys resolve through the module's
existing stable-key live-entity lookup and the existing typed subject
producer, never trusting the caller's key alone. An unknown kind prefix, an
unresolvable key, or a dead entity SHALL raise the existing typed
`ArtSubjectError`. The resolver SHALL NOT check preconditions (age,
capability), SHALL NOT read or write any gallery record, and SHALL publish no
presentation. The webclient gallery presenter rail and the gallery management
adapters SHALL be its only new callers.

#### Scenario: A companion key resolves to subject plus live entity

- **WHEN** the resolver is called with a live character's serialized subject key
- **THEN** it returns that character's typed subject and the live entity, and no record or entity attribute changes

#### Scenario: A dead subject key raises the typed error

- **WHEN** the resolver is called with a character key whose entity no longer exists
- **THEN** `ArtSubjectError` is raised naming the key
