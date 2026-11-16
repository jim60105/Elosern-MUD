## MODIFIED Requirements

### Requirement: One gallery record per art subject carries an ordered card list and a default
One lazily created gallery record per subject SHALL carry typed subject kind/key, ordered cards, nullable default image id, capability-scoped official preferences and last generation error/timestamp. Presentation and startup scanning SHALL NOT create records; append, explicit preferences/defaults and generation errors SHALL use the established writer.

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
- **WHEN** a character writes its first official preference or a monster writes one through a valid entity context
- **THEN** the character retains its cardless-record behavior; the monster stores only entity-local preference state and creates no species record or card

#### Scenario: Clearing an unset preference creates nothing
- **WHEN** a character or monster clears an unset official preference
- **THEN** the clear is a no-op and creates no record or entity preference state

#### Scenario: The record holds no live object reference
- **WHEN** a gallery record is persisted and re-read
- **THEN** it carries only serialized state and no live object reference

#### Scenario: Record creation follows the documented lazy triggers
- **WHEN** gallery record creation is exercised
- **THEN** card append, recorded generation error and explicit card default retain their existing triggers; personal official writes create a character record only, while monster personal writes stay entity-local; startup and presentation never manufacture a record

#### Scenario: An explicit default set names an existing card
- **WHEN** an explicit default set is submitted
- **THEN** it SHALL name an existing card of that record and SHALL be rejected otherwise, and card-default semantics SHALL be unchanged and SHALL stay distinct from the personal official selection, which is not a default-card operation

#### Scenario: The first append sets the default and later appends do not
- **WHEN** cards are appended to a record
- **THEN** the first card appended to an empty record SHALL become that record's default, and a later append SHALL NOT change the default

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
- **WHEN** unknown-size fallback composition validates `DEFAULT_FACE_RECT` with no image size
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
- **THEN** `world/art/gallery.py` SHALL keep one `DEFAULT_FACE_RECT` constant equal to `{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}` for card-less presentation use (the unknown-size composition anchor and the fallback-map gap fill)

#### Scenario: One validator enforces bounds always and squareness when the size is known
- **WHEN** a rect passes through the single validator `validate_face_rect`
- **THEN** it enforces the bounds contract always and the square contract wherever the writer knows the image pixel size; validation with no known size bounds-checks only, because a composition anchor on an unknown image marks no box on any image

#### Scenario: The server stores rects verbatim and does no imaging work
- **WHEN** the server handles an accepted rectangle
- **THEN** it SHALL store it verbatim and SHALL NEVER crop, transform, adjust, resize, or derive a second image from a rect, and SHALL NOT perform face detection
