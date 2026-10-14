# Spec Delta

## MODIFIED Requirements

### Requirement: The fallback seam supplies a URL and a face rectangle and reports its use
The single art-domain silhouette selector SHALL supply the existing closed key, committed resource identity/URL and its own geometry as the descriptor's alpha terminal. Existing declaration, demographics and stable-hash rules SHALL remain unchanged. Backend-selected fallback use SHALL emit gallery_fallback_used through named facade imports; browser-only failures SHALL not claim backend logging.

#### Scenario: A subject with no card and no classic asset resolves a fallback image
- **WHEN** the chain reaches the seam for a subject with no card and no `done` classic asset
- **THEN** the payload carries the `/art/defaults/<key>.<ext>` URL and that key's face rectangle, and one `gallery_fallback_used` event is logged

#### Scenario: Every declared rectangle is square on its own image
- **WHEN** the contract test decodes each committed fallback image and pairs it with its map entry
- **THEN** `w × width` equals `h × height` within one pixel for every key, and a deliberately
  non-square map entry fails the test naming its key

#### Scenario: The fallback writes nothing
- **WHEN** the fallback resolves for a subject that has no gallery record
- **THEN** no record is created, no card is appended, no file is copied into the store, and the subject still has no gallery record

#### Scenario: A fresh database with every service offline still shows art
- **WHEN** a character is resolved on a database with no generated art while the image server and every LLM service are unreachable
- **THEN** the payload carries a fallback image URL and its face rectangle rather than a placeholder

#### Scenario: A silhouette payload never claims generation success
- **WHEN** a subject whose asset state is `missing`, `pending`, or `failed` resolves a fallback silhouette
- **THEN** the payload carries the silhouette identity with the subject's true underlying status, the `silhouette` origin discriminator, and no `done`/generated label, and the persisted asset record is unchanged

#### Scenario: A later real image keeps the decorative reference but not the claim
- **WHEN** a real portrait later fails in the browser
- **THEN** shared loading can reach the carried alpha terminal, retain the real-source failure and leave persisted generation state unchanged

#### Scenario: The presenter builds the fallback URL like every other branch
- **WHEN** the presenter builds the payload for a resolved fallback identity
- **THEN** it builds the `/art/defaults/<key>.<ext>` URL from the identity exactly like every other
  payload branch

#### Scenario: Map entries are pixel-square against their committed images
- **WHEN** each entry of the fixed per-key rectangle map is checked against its committed image's
  pixel dimensions
- **THEN** `w × width` and `h × height` agree within one pixel, so every rectangle the seam supplies
  marks a square region of the image it ships with

#### Scenario: The presenter threads its entity; a subject-only call stays legal
- **WHEN** the presenter calls the seam with the entity it already resolved as the optional argument,
  or calls it with a bare subject
- **THEN** a subject-only call stays legal and recovers only a deterministic identification, and an
  ambiguous shared stable key recovers no entity and fails closed to the band rule

#### Scenario: Every stage-eligible payload carries the decorative fallback field
- **WHEN** an eligible figure descriptor is produced, with or without a real source
- **THEN** it carries its distinct canonical alpha terminal and geometry without a generated-success claim or mutation

#### Scenario: The payload establishes the closed origin discriminator vocabulary
- **WHEN** a canonical descriptor is produced
- **THEN** real resources carry runtime or official origin, alpha terminal carries silhouette origin, and missing real imagery has no fabricated successful origin

#### Scenario: The fallback field is decorative presentation data
- **WHEN** a silhouette terminal is provided
- **THEN** it never completes or mutates the subject generation state and remains separate from real-source attempts

