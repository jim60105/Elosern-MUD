## MODIFIED Requirements

### Requirement: Seed synchronization is idempotent, path-derived, and additive
`world/art/gallery_seed.py::sync_all()` SHALL run as a named startup step and SHALL walk the seed
root's `<kind>/<subject-key>/` layout, where `<kind>` is the store directory segment of a subject kind
whose capability declaration has a gallery — read from that declaration rather than from a vocabulary
restated here — and `<subject-key>` is a valid art subject key. For each image file whose extension is
in the closed set of store extensions, it SHALL derive that file's card `image_id` deterministically
from the file's path relative to the seed root, copy the file into the subject's gallery path under
the store root, and append one card through the gallery write API. A card whose derived id is already
present SHALL be skipped without copying, so repeated runs never duplicate a card and never rewrite a
file. A file with an unsupported extension, an unresolvable subject key, or an unknown kind directory
SHALL be skipped with a bounded diagnostic. Synchronization SHALL NEVER delete, replace, or reorder a
card that already exists, including cards the player generated. Where a kind's declared card maximum
would be exceeded, the surplus seed files SHALL be skipped with a bounded diagnostic rather than
replacing an existing card, and that limit SHALL be read from the declaration rather than tested for a
particular kind.

Reading files out of the (potentially hostile) seed tree SHALL verify each opened file AFTER the
open — regular, hard-link count one, within a size cap, never reached through a symlink — so a
planted link or aliased inode is refused rather than copied. Writing into the store SHALL likewise
open each destination no-follow and refuse anything that is not a single-link regular file, and a
raw record entry (valid or malformed) SHALL reserve its `stored_identity`: the file it points at is
never overwritten even when the card itself no longer validates.

#### Scenario: A second run copies and appends nothing
- **WHEN** `sync_all()` runs twice against an unchanged seed root
- **THEN** the second run appends no card, copies no file, and leaves every stored identity untouched

#### Scenario: A newly added seed file appears on the next start
- **WHEN** a new image is added to an already-synchronized subject's seed folder and the server restarts
- **THEN** exactly one new card is appended for it and the existing cards are unchanged

#### Scenario: Unsupported and unresolvable entries are skipped
- **WHEN** the seed root contains a file with an unsupported extension, a folder naming an invalid subject key, and an unknown kind directory
- **THEN** each is skipped with a bounded diagnostic and the valid entries still synchronize

#### Scenario: Generated cards are never disturbed
- **WHEN** `sync_all()` runs for a subject that already holds player-generated cards
- **THEN** those cards, their order, and their bindings are unchanged

#### Scenario: Surplus seed files for a capped kind are skipped
- **WHEN** a subject folder for a kind whose declared maximum is one holds several eligible image files
- **THEN** at most one card is appended, the surplus files are skipped with a bounded diagnostic, and no existing card is replaced
