# art-gallery-model — delta for square-face-rect-contract

## MODIFIED Requirements

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

## ADDED Requirements

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
