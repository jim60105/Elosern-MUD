## MODIFIED Requirements

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
