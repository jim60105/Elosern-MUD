# art-gallery-model Specification

## Purpose

Define the gallery record model that later gallery changes build on: one
lazily created `GalleryRecord` per portrait subject (`world/art/gallery.py`,
the sole writer), the exact ten-key image-card contract with its reproduction,
placement, and provenance fields, the shared `DEFAULT_FACE_RECT`, the
slot-masked equipment binding with the no-create snapshot reader, the monster
one-card cap, the `world/art/paths.py` store-root confinement helper behind
every gallery file deletion, and tolerant reads that skip malformed stored
cards instead of failing.

## Requirements

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
`gallery/<kind-directory>/<subject-key>/<image-id><extension>`, where the kind directory is exactly
`character` or `monster` — scenes have no gallery), `prompt` (either `None` or a mapping of exactly
`positive` and `negative` verbatim prompt text), `seed` (a non-negative integer or `None`),
`checkpoint` (a non-empty string or `None`), `requested_fields` (a list of field ids, possibly
empty), `face_rect`, `image_size`, `binding`, `source` (one of `generated`, `seed`), and
`created_at` (a float epoch timestamp). `image_size` is the pixel size of the card's stored image:
a mapping of exactly `width` and `height`, each a positive integer. A write MAY omit `face_rect`,
`image_size`, and `created_at`, which the API fills with the fitted default rectangle for the
established image size (see the face-rectangle requirement), the trusted image size supplied by
the append caller, and the current epoch time respectively; every other contract key is required
on the write. A caller-supplied `face_rect` SHALL be validated against the same record's
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
  `face_rect`, `image_size`, and `created_at`, or carries a wrongly typed value
- **THEN** a typed validation error is raised and no card is persisted

#### Scenario: A duplicate image id is rejected
- **WHEN** a card is appended whose `image_id` already exists on that record
- **THEN** a typed validation error is raised and the card list is unchanged

#### Scenario: A caller-supplied image size that is not a positive integer pair is rejected
- **WHEN** a card append supplies `image_size` whose values are zero, negative, non-integers, or
  whose key set is not exactly `width` and `height`
- **THEN** a typed validation error is raised and no card is persisted

### Requirement: Face rectangles are normalized, bounded, and default to the shared upper-half constant
A card's `face_rect` SHALL be a mapping of exactly `x`, `y`, `w`, `h` whose values are real
numbers in `[0, 1]` satisfying `x + w <= 1`, `y + h <= 1`, `w > 0`, and `h > 0`. In addition, a
rect validated against a known image pixel size SHALL be *pixel-square*: `w × width` and
`h × height` agree within one pixel. Because gallery portrait images are not square canvases, the
pixel-square rule deliberately admits rects whose normalized `w` and `h` differ (on 768×1024,
`w = 0.4` pairs with `h = 0.3`), and it can only be checked against the image's pixel size, never
as `w == h`. **No rect value is exempt**: validation against a known size rejects every
non-square rect, including one field-for-field equal to the shared `DEFAULT_FACE_RECT` constant
(the constant's `w == h` form marks a 384×512 box on the 768×1024 canvas and is therefore an
illegal *stored card* rect there). `world/art/gallery.py` SHALL expose `default_face_rect(image_size)`
returning the fitted default rectangle for a pixel size — the pinned upper-half anchor with its
height fraction derived so the box is exactly square: `{"x": 0.25, "y": 0.06, "w": 0.5,
"h": 0.5 × width / height}` — and it equals `DEFAULT_FACE_RECT` exactly on a square image. A card
written without an explicit rect SHALL be filled with `default_face_rect` of its established
`image_size`. `world/art/gallery.py` SHALL keep one `DEFAULT_FACE_RECT` constant equal to
`{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}` for card-less presentation use (the classic-asset and
unknown-size composition anchor and the fallback-map gap fill). The single validator
`validate_face_rect` enforces the bounds contract always and the square contract wherever the
writer knows the image pixel size; validation with no known size bounds-checks only, because a
composition anchor on an unknown image marks no box on any image. The server SHALL store accepted
rectangles verbatim and SHALL NEVER crop, transform, adjust, resize, or derive a second image from
a rect, and SHALL NOT perform face detection.

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
A `GalleryRecord` SHALL hold at most the number of cards its subject kind's capability declaration
names as that kind's maximum. The monster portrait kind SHALL declare a maximum of one; the character
portrait kind SHALL declare NO maximum and SHALL therefore stay uncapped exactly as it is today —
appending to it always accumulates and never replaces, however many cards it already holds. Appending
a card to a record whose kind declares a maximum SHALL install the new card as its sole card — deleting
any replaced card's stored file under the confinement rules — and SHALL leave the new card as the
record's default; because the only admitted maximum is one, a capped record is never partially full and
appending to an empty capped record installs the card exactly as the monster append does today. A card
SHALL be rejected when it carries a non-`None` binding for a kind whose
declaration does not support bindings, which the monster portrait kind does not. Both rules SHALL be
enforced by reading the declaration, never by comparing the subject kind inline, so the monster cap and
the monster unbound rule are consequences of that kind's declared capabilities rather than
monster-specific enforcement code.

#### Scenario: A second monster card replaces the first
- **WHEN** a card is appended to a monster subject that already has one card
- **THEN** the record holds exactly one card, it is the new one, it is the default, and the previous card's stored file is deleted

#### Scenario: A bound monster card is rejected
- **WHEN** a card carrying a binding is appended to a monster subject
- **THEN** a typed validation error is raised and the record is unchanged

#### Scenario: A character record stays uncapped
- **WHEN** many cards are appended to a character subject
- **THEN** every card is retained in append order, none is replaced, no stored file is deleted, and the first card is still the default

#### Scenario: The cap follows the declaration
- **WHEN** the enforced cap is exercised against a kind whose declared maximum is changed
- **THEN** the append honours the declared maximum with no edit to the enforcing module

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

### Requirement: The recorded generation error is last-attempt state, not a permanent mark
The generation error a `GalleryRecord` carries SHALL describe the subject's LAST generation attempt.
Recording an error SHALL replace any previously recorded code and timestamp, and `world/art/gallery.py`
SHALL expose a clearing operation that resets both to `None`. Clearing a subject that has no record
SHALL be a side-effect-free no-op — it SHALL NOT create a record, because a subject that never failed
has nothing to clear. Both operations SHALL run under the same `gallery_lock` as every other record
mutation and SHALL emit their existing bounded facade events.

#### Scenario: A second failure replaces the first code
- **WHEN** a subject records error code `A` and later records error code `B`
- **THEN** the record carries `B` with `B`'s timestamp and no trace of `A`

#### Scenario: Clearing a subject with no record creates nothing
- **WHEN** the recorded error is cleared for a subject that has never been written
- **THEN** no record is created, no error is raised, and the subject still reads as an empty gallery

#### Scenario: Clearing leaves every card untouched
- **WHEN** the recorded error is cleared for a subject holding cards and a default
- **THEN** the error code and timestamp are `None` and the card list and `default_image_id` are unchanged

### Requirement: One read-only accessor reports every subject whose gallery carries an error
`world/art/gallery.py` SHALL expose one read-only accessor returning the subjects whose record carries
a recorded generation error, each with its bounded code and timestamp. The single-writer rule keeps the
record class inside that module, so operator surfaces SHALL read cross-record gallery state ONLY
through the gallery module's read-only accessors and SHALL NOT query the record class themselves. The
erroring-subject accessor is the sole cross-record ERROR read; the gallery module MAY expose additional
read-only accessors of the same discipline (for example per-record state summaries for the staff status
surface). Every such accessor SHALL create no record, SHALL write nothing, and SHALL be tolerant: a
record whose persisted kind or subject key no longer parses SHALL be skipped rather than raising, so one
corrupt row can never blind the whole surface.

#### Scenario: Only erroring subjects are reported
- **WHEN** the accessor runs against a store holding one subject with a recorded error and two without
- **THEN** exactly the erroring subject is returned, with its code and timestamp

#### Scenario: The accessor never writes
- **WHEN** the accessor runs against a store with no gallery records at all
- **THEN** it returns nothing, creates no record, and raises no error

#### Scenario: An unparseable record is skipped, not fatal
- **WHEN** the accessor runs against a store where one gallery record's persisted subject no longer parses
- **THEN** that row is skipped, every other erroring subject is still returned, and no exception escapes

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

### Requirement: A card's image pixel size is recorded from verified bytes at append
Every card append SHALL record the appended image's actual pixel dimensions in `image_size`, and
that value SHALL be derived only from trusted server-side provenance — the dimensions actually
decoded from the image bytes — never from a player- or client-supplied field and never from the
requested render dimensions a generation call carried: a `generated` card's append receives the
size decoded from the worker's rendered bytes (the request parameters are request metadata, not
proof); a `seed` card's append derives the size by decoding the copied bytes. An append that
cannot establish a trusted pixel size for its image SHALL raise a typed validation error and
persist nothing. Face-rect squareness at every write boundary SHALL be checked against this
recorded size, so the stored card is self-describing: rect plus `image_size` fully determine the
square it marks without opening the image.

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

### Requirement: A face-rect update is checked against the card's recorded image size
`update_card_face_rect` SHALL validate the incoming rect against the stored card's `image_size`
under the pixel-square rule with no value exemptions, so a client cannot square-lock around a size
other than the card's own and cannot store the legacy constant on a non-square card. A stored card
whose `image_size` is missing or malformed fails the tolerant card contract and is skipped on
reads, which makes its face rect un-updatable through the tolerant-match rule (the existing miss
error) rather than silently checked against a guessed size.

#### Scenario: An update whose squareness disagrees with the stored size is refused
- **WHEN** `update_card_face_rect` is called with a rect that is pixel-square for some other image size but not for the card's recorded one
- **THEN** a typed validation error is raised and the card is unchanged

#### Scenario: Replaying the legacy constant onto a non-square card is refused
- **WHEN** `update_card_face_rect` submits a rect field-for-field equal to `DEFAULT_FACE_RECT` for a card whose recorded `image_size` is not square-compatible with it
- **THEN** a typed validation error is raised and the card is unchanged

#### Scenario: A pixel-square update against the recorded size commits verbatim
- **WHEN** `update_card_face_rect` is called with a rect that is pixel-square for the card's recorded `image_size`
- **THEN** the stored rect matches field for field and every other card field is unchanged
