## MODIFIED Requirements

### Requirement: An image card carries the exact reproduction, placement, and provenance contract
Every stored card SHALL be a mapping with exactly these keys: `image_id`, `stored_identity`,
`prompt`, `seed`, `checkpoint`, `requested_fields`, `face_rect`, `image_size`, `stage`,
`binding`, `source`, and `created_at`. Strict card validation requires the complete twelve-key
contract. A write whose card violates this contract SHALL raise a typed validation error at the
API boundary and SHALL NOT be persisted.

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

#### Scenario: Each contract key carries its documented type
- **WHEN** a stored card's keys are validated
- **THEN** `image_id` is a uuid string, unique inside its record
- **AND** `stored_identity` is the store-relative path `gallery/<kind-directory>/<subject-key>/<image-id><extension>`, where the kind directory is exactly `character`, `monster` or `scene`
- **AND** `prompt` is either `None` or a mapping of exactly `positive` and `negative` verbatim prompt text
- **AND** `seed` is a non-negative integer or `None`, and `checkpoint` a non-empty string or `None`
- **AND** `requested_fields` is a list of field ids, possibly empty
- **AND** `image_size` is the pixel size of the card's stored image: a mapping of exactly `width` and `height`, each a positive integer
- **AND** `source` is one of `generated`, `seed`, and `created_at` is a float epoch timestamp

#### Scenario: The API fills the four defaultable keys
- **WHEN** a write omits `stage`, `face_rect`, `image_size`, or `created_at`
- **THEN** the API fills them with the fitted default rectangle for the established image size (see the face-rectangle requirement), the trusted image size supplied by the append caller, and the current epoch time respectively, and every other contract key is required on the write
- **AND** omitted `stage` defaults to `{scale: 1.0, x: 0.0, y: 0.0}`

#### Scenario: A caller-supplied rect is validated against the record's size
- **WHEN** a card write supplies `face_rect` and `image_size` in whichever order the two arrive
- **THEN** the caller-supplied `face_rect` SHALL be validated against the same record's `image_size`

#### Scenario: No environment-driven generation parameter lands on a card
- **WHEN** a card is stored
- **THEN** environment-driven generation parameters — steps, CFG scale, dimension-setting values, sampler, scheduler — SHALL NOT be stored on a card, and `image_size` records the fact of the appended image's own decoded pixels, not a settings value

