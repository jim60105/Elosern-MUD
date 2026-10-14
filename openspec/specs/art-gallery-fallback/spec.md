# art-gallery-fallback Specification

## Purpose

Define the built-in gallery fallback layer: the closed six-key image
vocabulary committed to the repository and served through the existing
`/art/defaults/` route, the deterministic declaration → sex/age band →
subject-key hash resolution rule that fills the resolution chain's terminal
fallback seam, the per-key face-rectangle map, and the `gallery_fallback_used`
observability event — so a fresh database with every external service offline
still shows a dignified portrait instead of a placeholder.

## Requirements

### Requirement: The built-in fallback set is a closed vocabulary committed to the repository
The project SHALL commit exactly one image per key of the closed fallback vocabulary `man`, `woman`,
`boy`, `girl`, `elder`, `monster_anon` into one fixed in-repo defaults directory, served through the
existing `/art/defaults/<key>.<ext>` route. Required bundled official scenes SHALL be an additional tracked-art exception; every runtime and seed-synced image stays outside git under the art store root.
Each committed image SHALL be bounded in size and SHALL depict no sexualized content.

#### Scenario: Every key resolves to a committed file
- **WHEN** the contract test enumerates the fallback vocabulary
- **THEN** each key has exactly one committed file in the defaults directory, within the declared size bound

#### Scenario: No stray file is servable
- **WHEN** the contract test enumerates the defaults directory
- **THEN** every file corresponds to a vocabulary key and nothing else is present

#### Scenario: Runtime art is still absent from git
- **WHEN** tracked artwork is inspected
- **THEN** the six alpha defaults, required bundled scenes and existing reviewed documentation fixtures are tracked; runtime store, seed images and operator artwork remain untracked

#### Scenario: A contract test locks the vocabulary and directory together
- **WHEN** the contract test locks the fallback vocabulary and the defaults directory to each other
  in both directions
- **THEN** every key resolves to exactly one committed file and every file in the directory belongs
  to the vocabulary, so a key can never resolve to a missing image and an untracked stray file can
  never be served

### Requirement: A fallback key resolves by declaration, then band, then deterministic hash
`world/art/gallery_fallback.py` SHALL resolve a subject's fallback key in order: (1) every monster
entity or subject resolves `monster_anon`, including unresolved visual provenance; (2) a non-monster
registry-declared fallback key wins; (3) otherwise stored sex and apparent age select a band, and
the full key hashes deterministically into that band's ordered key pool. Resolution SHALL be a pure
function of the subject key and the stored sex and apparent age.

#### Scenario: A declared key wins over the band rule
- **WHEN** a non-monster subject's registry entry declares a fallback key
- **THEN** that key is resolved regardless of the subject's sex or apparent age

#### Scenario: Sex and apparent age select the band
- **WHEN** non-monster subjects with adult, child, and elder apparent ages and female and male sexes resolve without a declaration
- **THEN** each resolves the key its band declares for that sex

#### Scenario: A sex outside the pair hashes deterministically inside its band
- **WHEN** a non-monster subject whose sex is neither female nor male resolves without a declaration
- **THEN** its key is chosen from its band's pool by a hash of the subject key, and repeating the resolution yields the same key

#### Scenario: Determinism survives a restart
- **WHEN** the same subject is resolved before and after a server restart
- **THEN** the same fallback key, and therefore the same image, is resolved

#### Scenario: Malformed sex or age fails closed to the adult band
- **WHEN** a non-monster subject's stored sex or apparent age is missing or malformed
- **THEN** the adult band is used, no exception propagates, and a key is still resolved

#### Scenario: A declaration is optional and existing entries stay valid
- **WHEN** player presets and the NPC registries declare, or do not declare, a fallback
  key
- **THEN** declaring one is permitted (MAY) and every existing entry stays valid without one

#### Scenario: Monsters always carry the authoritative monster fallback
- **WHEN** a monster has absent or invalid visual provenance, no real image, or a failed image load
- **THEN** its fallback is `monster_anon`, independent of sex, age and threat tier; no tier fallback declaration is read

#### Scenario: A band pool may hold several keys
- **WHEN** a band's ordered key pool holds more than one key
- **THEN** that is how a sex outside the female/male pair resolves

#### Scenario: The same key resolves on every process and machine
- **WHEN** the same subject is resolved on another process or another machine
- **THEN** the pure resolution of subject key, stored sex, and apparent age yields the same key

#### Scenario: Missing or malformed values fail closed rather than raising
- **WHEN** a non-monster subject's stored sex or apparent-age value is missing or malformed
- **THEN** resolution SHALL fail closed to the adult band rather than raising

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

### Requirement: The built-in fallback images carry a transparent background
Each committed built-in fallback image SHALL be produced from the project art prompt library
through the same background-removal and encoding stages the portrait worker applies to generated
character and monster portraits, so each image carries an alpha channel in which the backdrop
around the figure is fully transparent and the figure itself is opaque and composes over any stage
or panel background without a visible rectangle or halo.

#### Scenario: Every default decodes with a transparent background
- **WHEN** the contract test decodes each committed fallback image
- **THEN** each image carries an alpha channel, every pixel in its four corner regions has alpha 0,
  and the mean alpha over the eroded interior of the figure's own silhouette (pixel cores only, so
  antialiased edges and legitimate see-through gaps never count) is at least 250 of 255

#### Scenario: An opaque default fails the contract
- **WHEN** a committed default without an alpha channel, or with an opaque corner, is placed in the
  defaults directory
- **THEN** the contract test fails naming that file

#### Scenario: The vocabulary and serving contract survive regeneration
- **WHEN** the regenerated images replace the opaque ones
- **THEN** the closed six-key vocabulary, the `.webp` extension, the size bound, and the per-key
  face-rectangle resolution all still hold, and each key serves the regenerated file under its
  unchanged name

#### Scenario: The background is removed with a permissively licensed model
- **WHEN** the provenance of the built-in fallback images committed to this repository is considered
- **THEN** their backgrounds were removed during production with the permissively licensed
  `isnet-anime` model, before the project's model-selection escape hatch was removed, so those
  committed images carry no non-commercial licence obligation and are not regenerated by this change

#### Scenario: A future regeneration uses the sole shipped weight
- **WHEN** a built-in fallback image's background is removed during a new production run
- **THEN** it is removed with the project's sole shipped model — the locked rembg default
  `bria-rmbg` (BRIA RMBG-2.0), which the container image bakes in — because
  `rembg-default-baked-model` removed the permissive model-selection escape hatch; the image
  publisher and the operator own the applicable licence for the resulting committed pixels

#### Scenario: Each image keeps its identity and re-authored rectangle
- **WHEN** a built-in fallback image is committed
- **THEN** it keeps its key, file name, and `.webp` extension, stays within the declared size bound,
  and carries a face rectangle re-authored against its own pixels

#### Scenario: The contract test rejects alpha, corner, or opacity defects
- **WHEN** the contract test decodes every committed default
- **THEN** it fails when an image has no alpha channel, when any pixel of its corner regions is not
  fully transparent, or when the figure's eroded interior is not opaque
