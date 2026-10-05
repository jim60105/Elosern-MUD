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
existing `/art/defaults/<key>.<ext>` route. These SHALL be the only generated-art files the
repository tracks: every runtime and seed-synced image stays outside git under the art store root. A
contract test SHALL lock the vocabulary and the directory to each other in both directions — every
key resolves to exactly one committed file, and every file in the directory belongs to the
vocabulary — so a key can never resolve to a missing image and an untracked stray file can never be
served. Each committed image SHALL be bounded in file size and SHALL depict no sexualized content.

#### Scenario: Every key resolves to a committed file
- **WHEN** the contract test enumerates the fallback vocabulary
- **THEN** each key has exactly one committed file in the defaults directory, within the declared size bound

#### Scenario: No stray file is servable
- **WHEN** the contract test enumerates the defaults directory
- **THEN** every file corresponds to a vocabulary key and nothing else is present

#### Scenario: Runtime art is still absent from git
- **WHEN** the repository is inspected for tracked art files
- **THEN** the defaults directory carries the only generated-art images: a
  reviewed, exact allowlist of non-runtime images (the
  `docs/design/elosern-redesign2/` documentation mockups and the
  `web/webclient-app/assets/redesign/` webclient fixture samples) and the
  art store root and the seed directory remain untracked

### Requirement: A fallback key resolves by declaration, then band, then deterministic hash
`world/art/gallery_fallback.py` SHALL resolve a subject's fallback key by this ordered rule: (1) a
fallback key explicitly declared by the subject's registry entry — player presets and the NPC and
monster registries MAY declare one and every existing entry stays valid without one — wins outright;
(2) otherwise a monster subject resolves `monster_anon`; (3) otherwise the subject's stored sex and
apparent age select one band, and the subject's full key is hashed deterministically into that band's
ordered key pool. A band's pool MAY hold more than one key, which is how a sex outside the
female/male pair resolves. The resolution SHALL be a pure function of the subject key and the stored
sex and apparent age: the same subject SHALL resolve the same key on every restart, on every process,
and on every machine. Missing or malformed sex or apparent-age values SHALL fail closed to the adult
band rather than raising.

#### Scenario: A declared key wins over the band rule
- **WHEN** a subject's registry entry declares a fallback key
- **THEN** that key is resolved regardless of the subject's sex or apparent age

#### Scenario: Sex and apparent age select the band
- **WHEN** subjects with adult, child, and elder apparent ages and female and male sexes resolve without a declaration
- **THEN** each resolves the key its band declares for that sex

#### Scenario: A sex outside the pair hashes deterministically inside its band
- **WHEN** a subject whose sex is neither female nor male resolves without a declaration
- **THEN** its key is chosen from its band's pool by a hash of the subject key, and repeating the resolution yields the same key

#### Scenario: Determinism survives a restart
- **WHEN** the same subject is resolved before and after a server restart
- **THEN** the same fallback key, and therefore the same image, is resolved

#### Scenario: Malformed sex or age fails closed to the adult band
- **WHEN** a subject's stored sex or apparent age is missing or malformed
- **THEN** the adult band is used, no exception propagates, and a key is still resolved

### Requirement: The fallback seam supplies a URL and a face rectangle and reports its use
`world/art/gallery_match.py::fallback_for(subject, entity=None)` SHALL return the resolved key's
committed `defaults/<key>.<ext>` identity together with that key's declared face rectangle, taken
from a fixed per-key rectangle map that falls back to the shared default rectangle for any key
without its own entry (the presenter builds the `/art/defaults/<key>.<ext>` URL from the identity
exactly like every other payload branch). Every entry of the fixed map SHALL be pixel-square
against its committed image's pixel dimensions (`w × width` and `h × height` agree within one
pixel), so every rectangle the seam supplies marks a square region of the image it ships with; a
contract test SHALL decode each committed default and fail when its map entry is not pixel-square
for that file's decoded size. The presenter threads the entity it already resolved as
the optional argument; a subject-only call SHALL stay legal and recover only a deterministic
identification — an ambiguous shared stable key recovers no entity and fails closed to the band
rule. Each use SHALL emit one `gallery_fallback_used` info event
through the `world.observability`
facade carrying the `subject`, `kind`, and resolved fallback `key` in `context`. The seam SHALL NOT
create a record, append a card, copy a file into the store, or write any state.

The presenter SHALL carry the resolved fallback key, media identity, and rectangle as a distinct
decorative `fallback` field on every stage-eligible payload — including payloads whose real
portrait resolved — so a browser whose real image later fails to load can render the
already-resolved silhouette without a new request or state mutation. The payload SHALL establish
the closed origin discriminator vocabulary itself (`runtime` for card/classic images, `silhouette`
when only the fallback resolved, `placeholder` otherwise), which the `official-art-resolution`
capability later extends with the `official` value; the fallback field is decorative
presentation data and SHALL NOT report the subject's portrait as `done`, generated, or completed
by virtue of resolving (only a real payload image carries a media URL of its own), and it SHALL NOT change the subject's underlying
missing/pending/failed/unavailable status, which SHALL pass through from the asset/gallery state
exactly as before. A subject's real portrait state SHALL therefore remain observable even while a
silhouette media identity is present for stage rendering.

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
- **WHEN** the same subject later resolves a real runtime image and that image then fails to load in the browser
- **THEN** the payload's real image carries the `runtime` origin beside the retained decorative `fallback` reference, the browser renders the silhouette with the load-failure label without any new request or state mutation, and no generated-state write ever occurred during the silhouette phase

### Requirement: The built-in fallback images carry a transparent background
Each committed built-in fallback image SHALL be produced from the project art prompt library
through the same background-removal and encoding stages the portrait worker applies to generated
character and monster portraits, so each image carries an alpha channel in which the backdrop
around the figure is fully transparent and the figure itself is opaque and composes over any stage
or panel background without a visible rectangle or halo. The background SHALL have been removed
with a permissively licensed model, so the committed images carry no non-commercial licence
obligation. Each image SHALL keep its key, file name, and `.webp` extension, stay within the
declared size bound, and carry a face rectangle re-authored against its own pixels. A contract test
SHALL decode every committed default and fail when an image has no alpha channel, when any pixel
of its corner regions is not fully transparent, or when the figure's eroded interior is not opaque.

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
