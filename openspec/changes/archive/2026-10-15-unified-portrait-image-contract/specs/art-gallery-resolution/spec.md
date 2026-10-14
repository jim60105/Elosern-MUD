# Spec Delta

## MODIFIED Requirements

### Requirement: Every resolution payload carries a face rectangle or null
Canonical portrait resources SHALL carry each original candidate or alpha terminal's own validated face rectangle in its geometry, not a top-level shared payload field. Existing card/fallback pixel-square and classic shared-anchor semantics SHALL remain. Scene geometry SHALL have null face rectangle. Metadata remains placement-only without server crop/transform or second pixels.

#### Scenario: A resolved card carries its own rectangle
- **WHEN** a card with explicit rectangle becomes a canonical candidate
- **THEN** that candidate geometry carries its own validated rectangle and admitted URL

#### Scenario: A placeholder carries a null rectangle
- **WHEN** no real portrait candidate exists
- **THEN** no real geometry is fabricated; separately admitted alpha terminal keeps its own rectangle

#### Scenario: A malformed stored rectangle degrades to the default
- **WHEN** stored card rectangle is malformed or nonsquare
- **THEN** safe fitted candidate geometry is used with an attributed metadata fault and bounded diagnostic

#### Scenario: A classic-asset payload keeps the shared constant
- **WHEN** a classic (non-card) asset resolves
- **THEN** the payload carries the shared default constant rectangle, bounds-validated with no image size

#### Scenario: An official payload carries validated metadata geometry
- **WHEN** an official default with a valid declared manifest rectangle and a non-identity declared stage resolves
- **THEN** the payload carries that rectangle validated against the image's decoded dimensions, and that declared stage — the identity triple only when none is declared or it is invalid

#### Scenario: A card payload carries its own validated rectangle
- **WHEN** a card resolves
- **THEN** the payload carries the resolved card's normalized rectangle, validated through the
  gallery face-rect validator against that card's recorded `image_size`

#### Scenario: A classic payload carries the shared composition anchor
- **WHEN** a classic asset resolves
- **THEN** the payload carries the shared default rectangle — the card-less composition anchor, which
  knows no image size

#### Scenario: A fallback payload carries the seam's rectangle
- **WHEN** a fallback image resolved
- **THEN** the payload carries the rectangle the fallback seam supplies, defaulting to the shared
  default

#### Scenario: An official payload carries validated directory geometry
- **WHEN** an official image resolved
- **THEN** the payload carries the directory-metadata or fitted-default rectangle validated against
  the decoded image dimensions (see the `official-art-resolution` capability)

#### Scenario: Every placeholder payload carries a null rectangle
- **WHEN** no real image is described
- **THEN** there is no top-level face_rect; real geometry is absent and alpha-terminal geometry remains separate

#### Scenario: A bad stored rectangle degrades with a diagnostic, never failure
- **WHEN** stored image geometry is invalid
- **THEN** the candidate uses safe fitted/shared geometry with source-scoped metadata fault and diagnostic, rather than failing the whole descriptor



#### Scenario: All geometry locations use the exact canonical schema
- **WHEN** roster/art catalog descriptors are serialized
- **THEN** face_rect is inside each applicable resource.geometry; obsolete flat url/face_rect/stage fields fail validation

