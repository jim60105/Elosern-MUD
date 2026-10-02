# art-gallery-resolution — delta for square-face-rect-contract

## MODIFIED Requirements

### Requirement: Every resolution payload carries a face rectangle or null
`world/art/presenter.py` SHALL add `face_rect` to every resolution payload it produces: the resolved
card's normalized rectangle when a card resolved, validated through the gallery face-rect validator
against that card's recorded `image_size`; the shared default rectangle when a classic asset
resolved (the card-less composition anchor, which knows no image size), the rectangle the fallback
seam supplies (defaulting to the shared default) when a
fallback image resolved, and `null` for every placeholder payload. The value SHALL be a mapping
of exactly `x`, `y`, `w`, `h` in `[0, 1]`, and a rectangle carried from a card or the fallback map
SHALL be pixel-square on the image it ships with — every rectangle a client receives from a
resolution marks a square region of its image. The server SHALL NOT crop, transform, or produce a second
image: the rectangle is placement metadata for the client alone. A malformed or non-square-for-its-image
stored rectangle SHALL
degrade to the fitted default square for that card's `image_size` (the shared default constant where
no image size is known) with one bounded diagnostic, never to a failed payload.

#### Scenario: A resolved card carries its own rectangle
- **WHEN** a card with an explicit rectangle resolves
- **THEN** the payload carries a URL and exactly that rectangle

#### Scenario: A placeholder carries a null rectangle
- **WHEN** the chain resolves to any placeholder
- **THEN** the payload carries a null URL and a null `face_rect`

#### Scenario: A malformed stored rectangle degrades to the default
- **WHEN** the resolution seam hands the presenter a card whose stored rectangle fails validation against the card's recorded image size — including one that is not pixel-square
- **THEN** the payload carries the fitted default square for that card's image and one bounded diagnostic is logged

#### Scenario: A classic-asset payload keeps the shared constant
- **WHEN** a classic (non-card) asset resolves
- **THEN** the payload carries the shared default constant rectangle, bounds-validated with no image size
