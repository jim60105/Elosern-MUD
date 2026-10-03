## MODIFIED Requirements

### Requirement: An image card carries the exact reproduction, placement, and provenance contract
Every stored card SHALL be a mapping with exactly these keys: `image_id` (a uuid string, unique
inside its record), `stored_identity` (the store-relative path
`gallery/<kind-directory>/<subject-key>/<image-id><extension>`, where the kind directory is exactly
`character` or `monster` — scenes have no gallery), `prompt` (either `None` or a mapping of exactly
`positive` and `negative` verbatim prompt text), `seed` (a non-negative integer or `None`),
`checkpoint` (a non-empty string or `None`), `requested_fields` (a list of field ids, possibly
empty), `face_rect`, `image_size`, `stage`, `binding`, `source` (one of `generated`, `seed`), and
`created_at` (a float epoch timestamp). `image_size` is the pixel size of the card's stored image:
a mapping of exactly `width` and `height`, each a positive integer. A write MAY omit `stage`, `face_rect`,
`image_size`, and `created_at`, which the API fills with the fitted default rectangle for the
established image size (see the face-rectangle requirement), the trusted image size supplied by
the append caller, and the current epoch time respectively; every other contract key is required
on the write. Omitted `stage` defaults to `{scale: 1.0, x: 0.0, y: 0.0}`; strict card validation requires the complete twelve-key contract. A caller-supplied `face_rect` SHALL be validated against the same record's
`image_size`, whichever order the two arrive in. Environment-driven generation parameters — steps,
CFG scale, dimension-setting values, sampler, scheduler — SHALL NOT be stored on a card;
`image_size` records the fact of the appended image's own decoded pixels, not a settings value. A
write whose card violates this contract SHALL raise a typed validation error at the API boundary
and SHALL NOT be persisted.

#### Scenario: A generated card stores the reproduction set and nothing environment-driven
- **WHEN** a card is appended carrying the verbatim prompt pair, the server-reported seed, and the configured checkpoint
- **THEN** the stored card carries exactly the contract keys, and it carries no steps, cfg scale, width-setting, height-setting, sampler, or scheduler value

#### Scenario: A seed-provenance card carries no prompt pair
- **WHEN** a card is appended with `source` `seed`
- **THEN** the stored card carries `prompt` `None` and `seed` `None`, and the write succeeds

#### Scenario: A card with an unknown or missing key is rejected
- **WHEN** a card write carries an extra key, omits a contract key other than the API-defaulted
  `stage`, `face_rect`, `image_size`, and `created_at`, or carries a wrongly typed value
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: A duplicate image id is rejected
- **WHEN** a card is appended whose `image_id` already exists on that record
- **THEN** a typed validation error is raised and the card list is unchanged

#### Scenario: A caller-supplied image size that is not a positive integer pair is rejected
- **WHEN** a card append supplies `image_size` whose values are zero, negative, non-integers, or
  whose key set is not exactly `width` and `height`
- **THEN** a typed validation error is raised and no card is persisted

### Requirement: Existing cards accept in-place face-rect and binding updates through the sole writer

`world/art/gallery.py` SHALL expose `update_card_face_rect(subject, image_id,
face_rect)` and `update_card_binding(subject, image_id, binding)` as the face-rect and binding
mutations of an existing card's fields; the stage update seam is governed by the stage-transform requirement. Each SHALL run under the existing
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

### Requirement: Malformed stored cards are skipped, never fatal
Every read of a record's cards SHALL first supply identity stage for a missing or malformed stored `stage`, without writing storage. Other malformed fields SHALL retain the existing skip discipline. Every read of a record's cards SHALL be tolerant: a stored entry that is not a mapping, or that
still fails the card contract after stage-only normalization, SHALL be skipped and reported once through the `world.observability`
facade as a `gallery_card_invalid` event carrying the subject and, when readable, the offending
`image_id`. A malformed entry SHALL NEVER raise out of a read, SHALL NEVER be returned to a caller,
and SHALL NOT prevent the record's valid cards from being returned.

#### Scenario: A malformed card is skipped and logged once
- **WHEN** a record holds one valid card and one entry that is not a mapping
- **THEN** the read returns exactly the valid card and one `gallery_card_invalid` event is logged

#### Scenario: A record of only malformed cards reads as empty
- **WHEN** every stored entry of a record still fails the card contract after stage-only normalization, such as non-mapping entries or entries with invalid image_size
- **THEN** the read returns an empty list and no exception propagates

## ADDED Requirements

### Requirement: Per-card stage transforms are bounded atomic presentation metadata
A gallery card SHALL own one `stage` mapping with exactly `scale`, `x`, `y`. Values SHALL be finite real numbers, never bool; scale SHALL be within [0.2, 2.0], x and y within [-0.5, 0.5], inclusively. Validation SHALL return a fresh plain mapping and preserve accepted values. The sole writer SHALL replace the entire triple atomically under the gallery lock after validation, preserve every other card field, card order, default and source file, and emit `gallery_stage_set` with subject, image id and all three values. An unknown card SHALL raise a typed record error without a write. Stage SHALL be presentation-only, with no subject-level inheritance or rules/appraisal influence. Missing or malformed stored stage SHALL read as identity without migration or persistent repair; unrelated corruption SHALL remain invalid.

#### Scenario: Inclusive endpoints are accepted verbatim
- **WHEN** stage is `{scale: 0.2, x: -0.5, y: 0.5}` or `{scale: 2.0, x: 0.5, y: -0.5}`
- **THEN** validation returns the same values in a distinct plain mapping

#### Scenario: Hostile types and shapes reject before persistence
- **WHEN** a stage write supplies bool, NaN, infinity, non-numbers, an extra/missing key or a value beyond any bound
- **THEN** a typed record error occurs and the stored record and files remain unchanged

#### Scenario: One save replaces all coordinates
- **WHEN** an existing card saves `{scale: 0.6, x: 0.1, y: -0.2}`
- **THEN** the complete triple is stored, no intermediate partial triple is visible, every other field/default/order/file remains unchanged and the stage event carries the subject, image id and triple

#### Scenario: Unknown card refuses atomically
- **WHEN** a valid stage triple names an image id absent from the subject's cards
- **THEN** a typed record error occurs and no card, record or file is changed

#### Scenario: API defaults differ from strict card validation
- **WHEN** a write-defaulted card omits stage and the same incomplete card is strictly validated
- **THEN** the write-defaulted form gains identity stage and the strict form is rejected for its missing twelfth key

#### Scenario: Old or hand-edited stage remains readable and editable
- **WHEN** otherwise valid stored cards lack stage or carry malformed stage
- **THEN** tolerant reads return those cards with identity stage without modifying storage, and an explicit valid stage save can locate and update the card

#### Scenario: Stage changes have no rules effect
- **WHEN** only a card's stage triple changes
- **THEN** combat, resolution, appraisal and integer-copper money state remain unchanged
