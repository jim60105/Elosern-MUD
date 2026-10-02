# webclient-gallery-management-actions — delta for square-face-rect-contract

## MODIFIED Requirements

### Requirement: Face-rect save stores the validated rect verbatim

`gallery.face_rect.update` SHALL accept exactly `subject_key`, `image_id`, and
`face_rect` (`x`, `y`, `w`, `h` reals in [0,1], `x+w ≤ 1`, `y+h ≤ 1`, positive
`w`/`h`), SHALL reject a rect that is not pixel-square against the target card's
recorded `image_size` (`w × width` and `h × height` within one pixel; no rect
value is exempt — a replayed shared default constant on a non-square card is
rejected like any other non-square rect), SHALL
persist an accepted rect verbatim through
`world/art/gallery.py::update_card_face_rect`, and SHALL NOT crop,
resize, or store any second image. The payload schema SHALL NOT admit an image
size: the squareness reference is always the card's server-recorded size, never
client-asserted. The 1:1 crop preview is a client-local
rendering of the same image; the server stores only the rectangle.

#### Scenario: A stored rect equals the submitted rect exactly

- **WHEN** a pixel-square rect is saved for a card
- **THEN** the stored card rect matches field-for-field and exactly one image file remains referenced by that card

#### Scenario: An out-of-bounds rect rejects with no write

- **WHEN** `face_rect` carries `x + w > 1`
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: A non-square rect rejects with no write

- **WHEN** `face_rect` marks a box whose pixel width and height disagree beyond one pixel on the card's recorded image size
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: The legacy default constant rejects on a non-square card

- **WHEN** `face_rect` is field-for-field equal to the shared default constant for a card whose recorded `image_size` makes it non-square
- **THEN** the result is `rejected` and the stored card is unchanged

#### Scenario: A square-on-screen rect on a portrait card is accepted

- **WHEN** a card whose recorded `image_size` is 768×1024 receives `face_rect` `w = 0.4`, `h = 0.3` inside the unit square
- **THEN** the result is the declared success presentation and the stored rect equals the submitted rect verbatim
