## ADDED Requirements

### Requirement: One gallery record per art subject carries an ordered card list and a default
`world/art/gallery.py` SHALL persist at most one `GalleryRecord` (an Evennia `DefaultScript`) per
art subject, keyed `gallery:<full-subject-key>`, carrying the subject kind and un-prefixed subject
key (mirroring `ArtAssetRecord`), an append-ordered `cards` list, a nullable `default_image_id`, and
the subject's last generation error code and timestamp. The record SHALL hold no live object
reference. Records SHALL be created lazily — on the first card append, the first recorded generation
error, or the first explicit default set — never by a startup scan, so a subject with no record is a
legal state that yields an empty card list. The first card appended to an empty record SHALL become that record's default; a later
append SHALL NOT change the default. An explicit default set SHALL name an existing card of that
record and SHALL be rejected otherwise.

#### Scenario: A subject with no record yields an empty gallery
- **WHEN** the card list is read for a subject that has never been written
- **THEN** the read returns an empty list, no record is created, and no error is raised

#### Scenario: The first appended card becomes the default
- **WHEN** a card is appended to a subject with no record
- **THEN** the record is created with that one card and `default_image_id` equal to that card's `image_id`

#### Scenario: A later append leaves the default alone
- **WHEN** a second card is appended to a record that already has a default
- **THEN** the card list has two entries in append order and `default_image_id` still names the first card

#### Scenario: Setting a default to an unknown card is rejected
- **WHEN** an explicit default set names an `image_id` that no card of the record carries
- **THEN** a typed validation error is raised and the record's `default_image_id` is unchanged

### Requirement: An image card carries the exact reproduction, placement, and provenance contract
Every stored card SHALL be a mapping with exactly these keys: `image_id` (a uuid string, unique
inside its record), `stored_identity` (the store-relative path
`gallery/<kind-directory>/<subject-key>/<image-id><extension>`, where the kind directory is exactly `character` or `monster` — scenes have no gallery), `prompt` (either `None` or a
mapping of exactly `positive` and `negative` verbatim prompt text), `seed` (a non-negative integer
or `None`), `checkpoint` (a non-empty string or `None`), `requested_fields` (a list of field ids,
possibly empty), `face_rect`, `binding`, `source` (one of `generated`, `seed`), and `created_at` (a
float epoch timestamp). A write MAY omit `face_rect` and `created_at`, which the API fills with
`DEFAULT_FACE_RECT` and the current epoch time respectively; every other contract key is required on
the write. Environment-driven generation parameters — steps, CFG scale, dimensions,
sampler, scheduler — SHALL NOT be stored on a card. A write whose card violates this contract SHALL
raise a typed validation error at the API boundary and SHALL NOT be persisted.

#### Scenario: A generated card stores the reproduction set and nothing environment-driven
- **WHEN** a card is appended carrying the verbatim prompt pair, the server-reported seed, and the configured checkpoint
- **THEN** the stored card carries exactly the contract keys, and it carries no steps, cfg scale, width, height, sampler, or scheduler value

#### Scenario: A seed-provenance card carries no prompt pair
- **WHEN** a card is appended with `source` `seed`
- **THEN** the stored card carries `prompt` `None` and `seed` `None`, and the write succeeds

#### Scenario: A card with an unknown or missing key is rejected
- **WHEN** a card write carries an extra key, omits a contract key other than the API-defaulted
  `face_rect` and `created_at`, or carries a wrongly typed value
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: A duplicate image id is rejected
- **WHEN** a card is appended whose `image_id` already exists on that record
- **THEN** a typed validation error is raised and the card list is unchanged

### Requirement: Face rectangles are normalized, bounded, and default to the shared upper-half constant
A card's `face_rect` SHALL be a mapping of exactly `x`, `y`, `w`, `h` whose values are real numbers
in `[0, 1]` satisfying `x + w <= 1`, `y + h <= 1`, `w > 0`, and `h > 0`. `world/art/gallery.py` SHALL
expose one `DEFAULT_FACE_RECT` constant equal to `{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}`, which
SHALL be applied to any card written without an explicit rect. The server SHALL store the rectangle
verbatim and SHALL NEVER crop, transform, or derive a second image from it, and SHALL NOT perform
face detection.

#### Scenario: A card written without a rect gets the shared constant
- **WHEN** a card is appended with no `face_rect` supplied
- **THEN** the stored card's `face_rect` equals `DEFAULT_FACE_RECT`

#### Scenario: An out-of-bounds rectangle is rejected
- **WHEN** a rect is supplied whose `x + w` exceeds 1, whose `y + h` exceeds 1, whose `w` or `h` is zero or negative, or whose values fall outside `[0, 1]`
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: The stored rect is verbatim and no second image exists
- **WHEN** a card is appended with a valid explicit rect
- **THEN** the stored rect equals the supplied values exactly and exactly one image file is referenced by that card

### Requirement: A card binding is a non-empty slot mask plus a normalized snapshot over exactly the masked slots
A card's `binding` SHALL be either `None` (unbound) or a mapping of exactly `mask` and `snapshot`.
`mask` SHALL be a non-empty list of distinct slot ids drawn from `weapon_main`, `weapon_off`,
`armor`, `accessories`, stored in that declared order so the same selection always serializes
identically. `snapshot` SHALL carry exactly the masked slot ids as keys: `weapon_main`,
`weapon_off`, and `armor` map to an item key string or `None`; `accessories` maps to a
lexicographically sorted list of item key strings, possibly empty. A snapshot in which every masked
slot is empty ("wearing nothing on those slots") SHALL be a legal binding. A binding whose mask is
empty, carries an unknown or duplicate slot id, or whose snapshot keys do not equal the mask SHALL
be rejected with a typed validation error.

#### Scenario: An armor-plus-weapon binding stores its mask and snapshot
- **WHEN** a card is bound with the mask `armor` and `weapon_main` while the entity wears a specific armor and main weapon
- **THEN** the stored mask is `["weapon_main", "armor"]` in declared order and the snapshot carries exactly those two slots with their item keys

#### Scenario: An all-empty snapshot is a legal binding
- **WHEN** a card is bound with a mask over slots that are all currently empty
- **THEN** the binding is stored with `None` values (and an empty list for `accessories`) and the write succeeds

#### Scenario: Accessory keys are stored sorted
- **WHEN** a binding masks `accessories` while the entity wears several accessories in arbitrary storage order
- **THEN** the stored snapshot list is lexicographically sorted

#### Scenario: A malformed mask or mismatched snapshot is rejected
- **WHEN** a binding is written with an empty mask, an unknown slot id, a duplicated slot id, or a snapshot whose key set differs from the mask
- **THEN** a typed validation error is raised and no card is persisted

### Requirement: Equipment snapshots are read from stored state without materializing a handler
`world/art/gallery.py` SHALL compute an entity's four-slot snapshot by reading the stored
`equipment` mapping directly — the same no-create discipline
`world/skills/equipment.py::dual_wielding_from_storage` uses — and SHALL NOT construct an
`EquipmentHandler`, write `entity.db.equipment`, or mutate any entity state. Missing, non-mapping,
or wrongly typed storage SHALL fail closed to the fully empty snapshot rather than raising.

#### Scenario: Reading a snapshot creates no equipment state
- **WHEN** the snapshot is computed for an entity whose `equipment` attribute has never been written
- **THEN** the fully empty snapshot is returned and the entity still has no `equipment` attribute

#### Scenario: Malformed equipment storage fails closed
- **WHEN** the stored `equipment` value is a string, a list, or a mapping whose slot values are of the wrong type
- **THEN** the snapshot is the fully empty snapshot and no exception propagates

### Requirement: Monster subjects hold at most one card
A `GalleryRecord` whose subject kind is the monster portrait kind SHALL hold at most one card:
appending a card to a monster record that already has one SHALL replace the existing card — deleting
its stored file under the confinement rules — and SHALL leave the new card as the record's default.
Monster cards SHALL be rejected when they carry a non-`None` binding.

#### Scenario: A second monster card replaces the first
- **WHEN** a card is appended to a monster subject that already has one card
- **THEN** the record holds exactly one card, it is the new one, it is the default, and the previous card's stored file is deleted

#### Scenario: A bound monster card is rejected
- **WHEN** a card carrying a binding is appended to a monster subject
- **THEN** a typed validation error is raised and the record is unchanged

### Requirement: world/art/gallery.py is the sole writer of gallery records and deletion never dangles
`world/art/gallery.py` SHALL be the only module that creates, mutates, or deletes a `GalleryRecord`
or any card inside one; every other module — service, queue, worker, presenter, commands, and every
module under `world/ai/` — SHALL go through its API. Deleting a card SHALL remove it from the list
and SHALL delete its stored file, resolving the identity through the single store-root confinement
helper `world/art/paths.py::resolved_under_store_root` so no path outside `ART_STORE_ROOT` is ever
unlinked; a file that is already missing or fails to resolve under the root SHALL leave the card
removal committed rather than raising. Deleting the card named by `default_image_id` SHALL reset
`default_image_id` to `None`, so a record never names a card it does not hold.

#### Scenario: Deleting a card deletes exactly its confined file
- **WHEN** a card whose stored identity resolves under the store root is deleted
- **THEN** the card is removed from the list and exactly that file is unlinked

#### Scenario: An out-of-root identity is never unlinked
- **WHEN** a card whose stored identity resolves outside the store root or through a symlink is deleted
- **THEN** the card is removed from the list, no file outside the root is touched, and a bounded diagnostic is logged

#### Scenario: Deleting the default clears the default
- **WHEN** the card named by `default_image_id` is deleted while other cards remain
- **THEN** `default_image_id` becomes `None` and the remaining cards are untouched

#### Scenario: No other module writes a gallery record
- **WHEN** the production modules of the repository are inspected for gallery-record writes
- **THEN** only `world/art/gallery.py` creates, mutates, or deletes a `GalleryRecord` or its cards

### Requirement: Malformed stored cards are skipped, never fatal
Every read of a record's cards SHALL be tolerant: a stored entry that is not a mapping, or that
fails the card contract, SHALL be skipped and reported once through the `world.observability`
facade as a `gallery_card_invalid` event carrying the subject and, when readable, the offending
`image_id`. A malformed entry SHALL NEVER raise out of a read, SHALL NEVER be returned to a caller,
and SHALL NOT prevent the record's valid cards from being returned.

#### Scenario: A malformed card is skipped and logged once
- **WHEN** a record holds one valid card and one entry that is not a mapping
- **THEN** the read returns exactly the valid card and one `gallery_card_invalid` event is logged

#### Scenario: A record of only malformed cards reads as empty
- **WHEN** every stored entry of a record fails the card contract
- **THEN** the read returns an empty list and no exception propagates
