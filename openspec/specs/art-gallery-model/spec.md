# art-gallery-model Specification

## Purpose

Define the gallery record model that later gallery changes build on: one
lazily created `GalleryRecord` per portrait subject (`world/art/gallery.py`,
the sole writer), the exact twelve-key image-card contract with its reproduction,
placement, and provenance fields, the shared `DEFAULT_FACE_RECT`, the
slot-masked equipment binding with the no-create snapshot reader, the monster
one-card cap, the `world/art/paths.py` store-root confinement helper behind
every gallery file deletion, and tolerant reads that skip malformed stored
cards instead of failing.

## Requirements

### Requirement: One gallery record per art subject carries an ordered card list and a default
`world/art/gallery.py` SHALL persist at most one `GalleryRecord` (an Evennia `DefaultScript`) per
art subject, keyed `gallery:<full-subject-key>`, carrying the subject kind and un-prefixed subject
key (mirroring `ArtAssetRecord`), an append-ordered `cards` list, a nullable `default_image_id`,
the subject's personal official-art preference state (see the preference requirement), and the
subject's last generation error code and timestamp. Records SHALL be created lazily, never by a
startup scan.

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

#### Scenario: The first official preference creates a card-less record
- **WHEN** a personal official selection is written for a subject that has never been written
- **THEN** the record is created with `cards: []`, `default_image_id: None`, and the selection set — and a runtime default-card rule is otherwise unchanged

#### Scenario: Clearing an unset preference creates nothing
- **WHEN** a clear-selection or clear-override request arrives for a subject with no record
- **THEN** the write is a no-op and no record exists afterward

#### Scenario: The record holds no live object reference
- **WHEN** a gallery record is persisted and re-read
- **THEN** it carries only serialized state and no live object reference

#### Scenario: Record creation follows the documented lazy triggers
- **WHEN** record creation is exercised
- **THEN** a record is created on the first card append, the first recorded generation error, the first explicit default set, or the first explicit official-preference write (a personal official selection or geometry override) — never by a startup scan, so a subject with no record is a legal state that yields an empty card list and unset preferences

#### Scenario: An explicit default set names an existing card
- **WHEN** an explicit default set is submitted
- **THEN** it SHALL name an existing card of that record and SHALL be rejected otherwise, and card-default semantics SHALL be unchanged and SHALL stay distinct from the personal official selection, which is not a default-card operation

#### Scenario: The first append sets the default and later appends do not
- **WHEN** cards are appended to a record
- **THEN** the first card appended to an empty record SHALL become that record's default, and a later append SHALL NOT change the default

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
- **AND** `stored_identity` is the store-relative path `gallery/<kind-directory>/<subject-key>/<image-id><extension>`, where the kind directory is exactly `character` or `monster` — scenes have no gallery
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

### Requirement: Face rectangles are normalized, bounded, and default to the shared upper-half constant
A card's `face_rect` SHALL be a mapping of exactly `x`, `y`, `w`, `h` whose values are real
numbers in `[0, 1]` satisfying `x + w <= 1`, `y + h <= 1`, `w > 0`, and `h > 0`. In addition, a
rect validated against a known image pixel size SHALL be *pixel-square*: `w × width` and
`h × height` agree within one pixel. A card written without an explicit rect SHALL be filled
with `default_face_rect` of its established `image_size`.

#### Scenario: A card written without a rect gets the fitted square default
- **WHEN** a card is appended with no `face_rect` supplied and a trusted `image_size` of 768×1024
- **THEN** the stored card's `face_rect` is `{x: 0.25, y: 0.06, w: 0.5, h: 0.375}` — 384×384 px — and the same call on a square image stores `DEFAULT_FACE_RECT` itself

#### Scenario: A card written without a rect gets the shared constant
- **WHEN** a card is appended with no `face_rect` supplied and a trusted square `image_size` (e.g. 1000×1000)
- **THEN** the stored card's `face_rect` equals `DEFAULT_FACE_RECT` — on a square image the fitted default IS the shared constant

#### Scenario: An out-of-bounds rectangle is rejected
- **WHEN** a rect is supplied whose `x + w` exceeds 1, whose `y + h` exceeds 1, whose `w` or `h` is zero or negative, or whose values fall outside `[0, 1]`
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: A non-square rect is rejected against a square image
- **WHEN** a rect is validated against image size 1000×1000 with `w = 0.4` and `h = 0.3`
- **THEN** a typed validation error is raised

#### Scenario: A non-square normalized rect that is pixel-square is accepted on a portrait canvas
- **WHEN** a rect is validated against image size 768×1024 with `w = 0.4` and `h = 0.3`
- **THEN** validation succeeds and the rect is stored verbatim, because it marks an equal-pixel
  width and height on that image

#### Scenario: The legacy default constant is rejected as a stored rect on a non-square card
- **WHEN** `DEFAULT_FACE_RECT` itself is submitted for validation against image size 768×1024
- **THEN** a typed validation error is raised — the constant is never exempt from the square rule

#### Scenario: A rect outside the one-pixel square tolerance is rejected
- **WHEN** a rect is validated against a known image size and `|w × width − h × height|` exceeds one pixel
- **THEN** a typed validation error is raised and the rect is not adjusted

#### Scenario: Validation without a known image size stays bounds-only
- **WHEN** the classic-asset presentation path validates `DEFAULT_FACE_RECT` with no image size
- **THEN** validation succeeds — an anchor with no image to square keeps today's contract

#### Scenario: The stored rect is verbatim and no second image exists
- **WHEN** a card is appended with a valid explicit rect
- **THEN** the stored rect equals the supplied values exactly and exactly one image file is referenced by that card

#### Scenario: The pixel-square rule works on non-square canvases
- **WHEN** a rect is checked for pixel-squareness
- **THEN** because gallery portrait images are not square canvases, the pixel-square rule deliberately admits rects whose normalized `w` and `h` differ (on 768×1024, `w = 0.4` pairs with `h = 0.3`), and it can only be checked against the image's pixel size, never as `w == h`

#### Scenario: No rect value is exempt from the square rule
- **WHEN** a rect is validated against a known size
- **THEN** validation rejects every non-square rect, including one field-for-field equal to the shared `DEFAULT_FACE_RECT` constant (the constant's `w == h` form marks a 384×512 box on the 768×1024 canvas and is therefore an illegal *stored card* rect there)

#### Scenario: default_face_rect derives the fitted square for a pixel size
- **WHEN** `world/art/gallery.py`'s exposed `default_face_rect(image_size)` is called with a pixel size
- **THEN** it returns the pinned upper-half anchor with its height fraction derived so the box is exactly square: `{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5 × width / height}` — and it equals `DEFAULT_FACE_RECT` exactly on a square image

#### Scenario: One shared constant serves card-less presentation
- **WHEN** presentation needs a rect without a card image size
- **THEN** `world/art/gallery.py` SHALL keep one `DEFAULT_FACE_RECT` constant equal to `{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}` for card-less presentation use (the classic-asset and unknown-size composition anchor and the fallback-map gap fill)

#### Scenario: One validator enforces bounds always and squareness when the size is known
- **WHEN** a rect passes through the single validator `validate_face_rect`
- **THEN** it enforces the bounds contract always and the square contract wherever the writer knows the image pixel size; validation with no known size bounds-checks only, because a composition anchor on an unknown image marks no box on any image

#### Scenario: The server stores rects verbatim and does no imaging work
- **WHEN** the server handles an accepted rectangle
- **THEN** it SHALL store it verbatim and SHALL NEVER crop, transform, adjust, resize, or derive a second image from a rect, and SHALL NOT perform face detection

### Requirement: A card binding is a non-empty slot mask plus a normalized snapshot over exactly the masked slots
A card's `binding` SHALL be either `None` (unbound) or a mapping of exactly `mask` and `snapshot`.
`mask` SHALL be a non-empty list of distinct slot ids drawn from `weapon_main`, `weapon_off`,
`armor`, `accessories`. `snapshot` SHALL carry exactly the masked slot ids as keys. A binding whose mask is
empty, carries an unknown or duplicate slot id, or whose snapshot keys do not equal the mask SHALL
be rejected with a typed validation error.

#### Scenario: An armor-plus-weapon binding stores its mask and snapshot
- **WHEN** a card is bound with the mask `armor` and `weapon_main` while the entity wears a specific armor and main weapon
- **THEN** the stored mask is `["weapon_main", "armor"]` in declared order and the snapshot carries exactly those two slots with their item keys

#### Scenario: The mask is stored in declared order
- **WHEN** a mask is stored
- **THEN** its slot ids are stored in the declared order `weapon_main`, `weapon_off`, `armor`, `accessories`, so the same selection always serializes identically

#### Scenario: An all-empty snapshot is a legal binding
- **WHEN** a card is bound with a mask over slots that are all currently empty
- **THEN** the binding is stored with `None` values (and an empty list for `accessories`) and the write succeeds

#### Scenario: Accessory keys are stored sorted
- **WHEN** a binding masks `accessories` while the entity wears several accessories in arbitrary storage order
- **THEN** the stored snapshot list is lexicographically sorted

#### Scenario: A malformed mask or mismatched snapshot is rejected
- **WHEN** a binding is written with an empty mask, an unknown slot id, a duplicated slot id, or a snapshot whose key set differs from the mask
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: Snapshot slot values follow the documented shapes
- **WHEN** a snapshot's values are validated
- **THEN** `weapon_main`, `weapon_off`, and `armor` map to an item key string or `None`, and `accessories` maps to a lexicographically sorted list of item key strings, possibly empty

#### Scenario: An all-empty masked snapshot is legal
- **WHEN** a snapshot has every masked slot empty ("wearing nothing on those slots")
- **THEN** it SHALL be a legal binding

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
A `GalleryRecord` SHALL hold at most the number of cards its subject kind's capability declaration
names as that kind's maximum. The monster portrait kind SHALL declare a maximum of one; the character
portrait kind SHALL declare NO maximum and SHALL therefore stay uncapped exactly as it is today.
Both the cap rule below and the binding rule SHALL be enforced by reading the declaration, never
by comparing the subject kind inline.

#### Scenario: A second monster card replaces the first
- **WHEN** a card is appended to a monster subject that already has one card
- **THEN** the record holds exactly one card, it is the new one, it is the default, and the previous card's stored file is deleted

#### Scenario: Appending to a capped record installs the sole card
- **WHEN** a card is appended to a record whose kind declares a maximum
- **THEN** the append SHALL install the new card as its sole card and SHALL leave the new card as the record's default

#### Scenario: A bound monster card is rejected
- **WHEN** a card carrying a binding is appended to a monster subject
- **THEN** a typed validation error is raised and the record is unchanged

#### Scenario: A character record stays uncapped
- **WHEN** many cards are appended to a character subject
- **THEN** every card is retained in append order, none is replaced, no stored file is deleted, and the first card is still the default

#### Scenario: The cap follows the declaration
- **WHEN** the enforced cap is exercised against a kind whose declared maximum is changed
- **THEN** the append honours the declared maximum with no edit to the enforcing module

#### Scenario: Character appends always accumulate
- **WHEN** cards are appended to the character portrait kind
- **THEN** appending always accumulates and never replaces, however many cards it already holds

#### Scenario: A replaced card's file is deleted under the confinement rules
- **WHEN** appending a card to a record whose kind declares a maximum replaces an existing card
- **THEN** the replaced card's stored file is deleted under the confinement rules; because the only admitted maximum is one, a capped record is never partially full and appending to an empty capped record installs the card exactly as the monster append does today

#### Scenario: A binding on a binding-incapable kind is rejected
- **WHEN** a card carries a non-`None` binding for a kind whose declaration does not support bindings, which the monster portrait kind does not
- **THEN** the card SHALL be rejected, so the monster cap and the monster unbound rule are consequences of that kind's declared capabilities rather than monster-specific enforcement code

### Requirement: world/art/gallery.py is the sole writer of gallery records and deletion never dangles
`world/art/gallery.py` SHALL be the only module that creates, mutates, or deletes a `GalleryRecord`
or any card inside one; every other module — service, queue, worker, presenter, commands, and every
module under `world/ai/` — SHALL go through its API. Deleting a card SHALL remove it from the list
and SHALL delete its stored file under the store-root confinement rules below.

#### Scenario: Deleting a card deletes exactly its confined file
- **WHEN** a card whose stored identity resolves under the store root is deleted
- **THEN** the card is removed from the list and exactly that file is unlinked

#### Scenario: Deletion resolves through the single confinement helper
- **WHEN** a card deletion resolves the card's stored identity for file removal
- **THEN** it goes through the single store-root confinement helper `world/art/paths.py::resolved_under_store_root` so no path outside `ART_STORE_ROOT` is ever unlinked

#### Scenario: An out-of-root identity is never unlinked
- **WHEN** a card whose stored identity resolves outside the store root or through a symlink is deleted
- **THEN** the card is removed from the list, no file outside the root is touched, and a bounded diagnostic is logged

#### Scenario: Deleting the default clears the default
- **WHEN** the card named by `default_image_id` is deleted while other cards remain
- **THEN** `default_image_id` becomes `None` and the remaining cards are untouched

#### Scenario: No other module writes a gallery record
- **WHEN** the production modules of the repository are inspected for gallery-record writes
- **THEN** only `world/art/gallery.py` creates, mutates, or deletes a `GalleryRecord` or its cards

#### Scenario: An unresolvable file leaves the removal committed
- **WHEN** a deleted card's stored file is already missing or fails to resolve under the store root
- **THEN** the card removal is committed rather than raising

#### Scenario: Deleting the named default resets the default
- **WHEN** the card named by `default_image_id` is deleted
- **THEN** `default_image_id` SHALL reset to `None`, so a record never names a card it does not hold

### Requirement: Malformed stored cards are skipped, never fatal
Every read of a record's cards SHALL be tolerant: a stored entry that is not a mapping, or that
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

#### Scenario: Reads normalize stored stage without writing
- **WHEN** a read encounters a missing or malformed stored `stage`
- **THEN** the read first supplies identity stage for it, without writing storage, and other malformed fields SHALL retain the existing skip discipline

### Requirement: The recorded generation error is last-attempt state, not a permanent mark
The generation error a `GalleryRecord` carries SHALL describe the subject's LAST generation attempt.
Recording an error SHALL replace any previously recorded code and timestamp, and `world/art/gallery.py`
SHALL expose a clearing operation that resets both to `None`. Both operations SHALL run under the same
`gallery_lock` as every other record mutation and SHALL emit their existing bounded facade events.

#### Scenario: A second failure replaces the first code
- **WHEN** a subject records error code `A` and later records error code `B`
- **THEN** the record carries `B` with `B`'s timestamp and no trace of `A`

#### Scenario: Clearing a subject with no record creates nothing
- **WHEN** the recorded error is cleared for a subject that has never been written
- **THEN** no record is created, no error is raised, and the subject still reads as an empty gallery

#### Scenario: Clearing leaves every card untouched
- **WHEN** the recorded error is cleared for a subject holding cards and a default
- **THEN** the error code and timestamp are `None` and the card list and `default_image_id` are unchanged

#### Scenario: Clearing is a side-effect-free no-op for a never-failed subject
- **WHEN** the recorded error is cleared for a subject that has no record
- **THEN** it SHALL be a side-effect-free no-op — it SHALL NOT create a record, because a subject that never failed has nothing to clear

### Requirement: One read-only accessor reports every subject whose gallery carries an error
`world/art/gallery.py` SHALL expose one read-only accessor returning the subjects whose record carries
a recorded generation error, each with its bounded code and timestamp. The single-writer rule keeps the
record class inside that module, so operator surfaces SHALL read cross-record gallery state ONLY
through the gallery module's read-only accessors and SHALL NOT query the record class themselves.

#### Scenario: Only erroring subjects are reported
- **WHEN** the accessor runs against a store holding one subject with a recorded error and two without
- **THEN** exactly the erroring subject is returned, with its code and timestamp

#### Scenario: The accessor never writes
- **WHEN** the accessor runs against a store with no gallery records at all
- **THEN** it returns nothing, creates no record, and raises no error

#### Scenario: An unparseable record is skipped, not fatal
- **WHEN** the accessor runs against a store where one gallery record's persisted subject no longer parses
- **THEN** that row is skipped, every other erroring subject is still returned, and no exception escapes

#### Scenario: The erroring-subject accessor is the sole cross-record ERROR read
- **WHEN** the gallery module's cross-record reads are inventoried
- **THEN** the erroring-subject accessor is the sole cross-record ERROR read, and the gallery module MAY expose additional read-only accessors of the same discipline (for example per-record state summaries for the staff status surface)
- **AND** every such accessor SHALL create no record, SHALL write nothing, and SHALL be tolerant: a record whose persisted kind or subject key no longer parses SHALL be skipped rather than raising, so one corrupt row can never blind the whole surface

### Requirement: Existing cards accept in-place face-rect and binding updates through the sole writer

`world/art/gallery.py` SHALL expose `update_card_face_rect(subject, image_id,
face_rect)` and `update_card_binding(subject, image_id, binding)` as the face-rect and binding
mutations of an existing card's fields; the stage update seam is governed by the stage-transform requirement. Each SHALL run under the existing
`gallery_lock`, locate the entry through the tolerant card read, and validate the incoming value
through `validate_face_rect` / `validate_binding` before any write.

#### Scenario: A stored face rect update equals the submitted rect exactly

- **WHEN** `update_card_face_rect` is called with a valid rect for an existing card
- **THEN** the card's stored rect matches field-for-field, every other card field and the record's default are unchanged, and no file on disk is touched

#### Scenario: A validated update stores verbatim and touches nothing else
- **WHEN** either writer commits a validated value
- **THEN** it stores the value verbatim — no file write, no crop, no second image, and no change to card order, `default_image_id`, or any other card field

#### Scenario: A binding update on a binding-incapable kind is refused

- **WHEN** `update_card_binding` names a monster-kind subject with a non-null binding
- **THEN** the typed capability error is raised, the card is unchanged, and no event fires

#### Scenario: An unknown or malformed card id refuses

- **WHEN** either writer names an image_id no valid card carries
- **THEN** the typed error mirrors the `remove_card` miss form and the record is byte-for-byte unchanged

#### Scenario: The sole-writer rule still holds after the update seam ships

- **WHEN** the production modules are inspected for gallery-card writes
- **THEN** every card mutation still lives in `world/art/gallery.py`

#### Scenario: A missing or malformed match raises the remove_card miss form
- **WHEN** either writer locates its entry through the tolerant card read and the match is missing or malformed
- **THEN** it SHALL raise the same typed `GalleryRecordError` form `remove_card` raises for a miss

#### Scenario: update_card_binding enforces capability and unbind
- **WHEN** `update_card_binding` is called
- **THEN** it SHALL additionally refuse a subject kind whose capability declaration supports no bindings with the capability-naming typed error the service seam raises, and SHALL accept an explicit `None` binding as an unbind

#### Scenario: Each successful update emits one facade event
- **WHEN** either writer completes a successful update
- **THEN** it SHALL emit one `gallery_card_updated` facade event carrying `subject`, `image_id`, `kind`, and the updated field in `context`

### Requirement: One public read-only seam resolves a serialized subject key to subject and entity

`world/art/service.py` SHALL expose `resolve_gallery_subject_by_key(subject_key)
-> (ArtSubject, entity_or_None)`: registry-backed kinds re-validate through the
kind's typed producer; character-kind keys resolve through the module's
existing stable-key live-entity lookup and the existing typed subject
producer, never trusting the caller's key alone.

#### Scenario: A companion key resolves to subject plus live entity

- **WHEN** the resolver is called with a live character's serialized subject key
- **THEN** it returns that character's typed subject and the live entity, and no record or entity attribute changes

#### Scenario: A dead subject key raises the typed error

- **WHEN** the resolver is called with a character key whose entity no longer exists
- **THEN** `ArtSubjectError` is raised naming the key

#### Scenario: Resolution failures raise the typed error
- **WHEN** the resolver is handed an unknown kind prefix, an unresolvable key, or a dead entity
- **THEN** it SHALL raise the existing typed `ArtSubjectError`

#### Scenario: The resolver stays out of rules, records, and presentation
- **WHEN** the resolver runs
- **THEN** it SHALL NOT check preconditions (age, capability), SHALL NOT read or write any gallery record, and SHALL publish no presentation

#### Scenario: Its only new callers are the gallery surfaces
- **WHEN** the resolver's callers are inspected
- **THEN** the webclient gallery presenter rail and the gallery management adapters SHALL be its only new callers

### Requirement: A card's image pixel size is recorded from verified bytes at append
Every card append SHALL record the appended image's actual pixel dimensions in `image_size`, and
that value SHALL be derived only from trusted server-side provenance — the dimensions actually
decoded from the image bytes — never from a player- or client-supplied field and never from the
requested render dimensions a generation call carried. An append that
cannot establish a trusted pixel size for its image SHALL raise a typed validation error and
persist nothing.

#### Scenario: A generated card records the decoded image's size
- **WHEN** the worker settles one gallery generation and its card is appended
- **THEN** the stored card's `image_size` equals the pixel dimensions decoded from the stored image file

#### Scenario: Requested and decoded sizes disagree
- **WHEN** a settled image decodes to different dimensions than the generation request specified
- **THEN** `image_size` records the decoded dimensions, and the queued rect is re-checked against them, with the job settling failed through the bounded worker path if the stored rect would violate the square contract

#### Scenario: A seed card records the copied file's decoded size
- **WHEN** seed sync appends a card for a copied seed image
- **THEN** the stored card's `image_size` equals the decoded pixel dimensions of that file

#### Scenario: An append without any trusted size refuses
- **WHEN** a card append can establish neither a decoded provenance size nor a caller-supplied trusted `image_size`
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: Player traffic can never carry an image size
- **WHEN** a webclient gallery action payload is validated
- **THEN** no payload schema admits an image size, and an attempted extra key is rejected as malformed

#### Scenario: Each provenance track decodes its own bytes
- **WHEN** a card append establishes its pixel size
- **THEN** a `generated` card's append receives the size decoded from the worker's rendered bytes (the request parameters are request metadata, not proof), and a `seed` card's append derives the size by decoding the copied bytes

#### Scenario: The recorded size makes the card self-describing
- **WHEN** face-rect squareness is checked at every write boundary
- **THEN** it SHALL be checked against this recorded size, so the stored card is self-describing: rect plus `image_size` fully determine the square it marks without opening the image

### Requirement: A face-rect update is checked against the card's recorded image size
`update_card_face_rect` SHALL validate the incoming rect against the stored card's `image_size`
under the pixel-square rule with no value exemptions, so a client cannot square-lock around a size
other than the card's own and cannot store the legacy constant on a non-square card.

#### Scenario: An update whose squareness disagrees with the stored size is refused
- **WHEN** `update_card_face_rect` is called with a rect that is pixel-square for some other image size but not for the card's recorded one
- **THEN** a typed validation error is raised and the card is unchanged

#### Scenario: Replaying the legacy constant onto a non-square card is refused
- **WHEN** `update_card_face_rect` submits a rect field-for-field equal to `DEFAULT_FACE_RECT` for a card whose recorded `image_size` is not square-compatible with it
- **THEN** a typed validation error is raised and the card is unchanged

#### Scenario: A pixel-square update against the recorded size commits verbatim
- **WHEN** `update_card_face_rect` is called with a rect that is pixel-square for the card's recorded `image_size`
- **THEN** the stored rect matches field for field and every other card field is unchanged

#### Scenario: A card with a malformed recorded size is un-updatable
- **WHEN** a stored card's `image_size` is missing or malformed
- **THEN** it fails the tolerant card contract and is skipped on reads, which makes its face rect un-updatable through the tolerant-match rule (the existing miss error) rather than silently checked against a guessed size

### Requirement: Per-card stage transforms are bounded atomic presentation metadata
A gallery card SHALL own one `stage` mapping with exactly `scale`, `x`, `y`. Values SHALL be finite real numbers, never bool; scale SHALL be within [0.2, 2.0], x and y within [-0.5, 0.5], inclusively. Validation SHALL return a fresh plain mapping and preserve accepted values.

#### Scenario: The sole writer replaces the triple atomically
- **WHEN** a validated stage triple is saved
- **THEN** the sole writer SHALL replace the entire triple atomically under the gallery lock after validation, preserve every other card field, card order, default and source file, and emit `gallery_stage_set` with subject, image id and all three values
- **AND** an unknown card SHALL raise a typed record error without a write

#### Scenario: Stage is presentation-only and malformed stage reads as identity
- **WHEN** stage is read or applied
- **THEN** stage SHALL be presentation-only, with no subject-level inheritance or rules/appraisal influence
- **AND** missing or malformed stored stage SHALL read as identity without migration or persistent repair; unrelated corruption SHALL remain invalid

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

### Requirement: Gallery records carry entity-local official-art preferences as first-class fields
`world/art/gallery.py` SHALL extend each subject's `GalleryRecord` with personal official-art
preference state — the explicitly selected official image identity (nullable) and a bounded map of
per-identity geometry overrides (face rectangle and stage triple) — written ONLY through
`world/art/gallery.py`'s public API under the existing `gallery_lock` discipline, exactly like card
mutations.

#### Scenario: Preference writes obey the sole writer
- **WHEN** the production modules are inspected for writes to official-art preference fields
- **THEN** only `world/art/gallery.py` mutates them, every write ran under `gallery_lock`, and no other module writes the record

#### Scenario: Preferences stay out of the card rules
- **WHEN** preference state is stored alongside cards
- **THEN** it SHALL NOT be stored as a card in `cards` and SHALL NOT participate in card rules (the card contract, the monster card cap, binding eligibility, and default-card semantics are unchanged)

#### Scenario: Preference writes touch no files
- **WHEN** a preference write runs
- **THEN** it SHALL NOT create, modify, or delete any file under the official root or the art store

#### Scenario: Preference reads are tolerant with the skip discipline
- **WHEN** preference state is read
- **THEN** reads SHALL be tolerant with the existing skip discipline: a malformed stored preference SHALL be treated as absent with one bounded diagnostic, never fatal

#### Scenario: Preferences are not cards
- **WHEN** a subject holds a personal official selection and one geometry override while its `cards` list is empty
- **THEN** the tolerant card read still returns zero cards, the monster one-card cap is unaffected, and the panel's card rows remain empty

#### Scenario: A malformed preference degrades to absent
- **WHEN** a stored preference fails validation on read
- **THEN** it reads as absent, one `gallery_card_invalid`-style bounded diagnostic names the subject, and the record's valid fields still read
