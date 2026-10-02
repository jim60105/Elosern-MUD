# art-gallery-fallback — delta for square-face-rect-contract

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
