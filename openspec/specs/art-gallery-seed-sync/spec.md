# art-gallery-seed-sync Specification

## Purpose

Define the bulk seed-art synchronization layer: the external read-only seed
folder behind the `ART_SEED_ROOT` directory-root setting, the idempotent
path-derived startup sync that mirrors it into the gallery store as ordinary
`source` `seed` cards, the optional per-subject manifest contract for the
default image and face rectangle, and the `gallery_seed_sync` observability
event — so an operator can seed hundreds of portraits offline and have them
appear in the gallery without ever committing art to git or running a
generation service.
## Requirements
### Requirement: Bulk seed art lives outside git behind one directory-root setting
`server/conf/settings.py` SHALL declare `ART_SEED_ROOT`, defaulting to the `art-seed` directory under
`GAME_DIR` and overridable through an environment variable of the same name, following the
`PROMPT_ROOT` precedent for directory roots rather than the typed `ART_SD_*` knob table. The
repository SHALL gitignore the default directory, so bulk seed art can never be committed. An absent,
empty, symlinked, or unreadable seed root SHALL be a supported configuration meaning "synchronize
nothing" — it SHALL log exactly one `gallery_seed_sync` event and SHALL NEVER fail startup. Seed
images SHALL be copied into the art store rather than served from the seed root, so the read-only
mount is never on a serving path.

#### Scenario: A missing seed root is a supported no-op
- **WHEN** the server starts with no directory at the configured seed root
- **THEN** one `gallery_seed_sync` event reports the skip, no card is created, and startup completes normally

#### Scenario: The default seed directory is untracked
- **WHEN** the repository's ignore rules are inspected
- **THEN** the default seed directory is ignored and no seed image is tracked by version control

#### Scenario: Seed images are served from the store, not the seed root
- **WHEN** a seed-synced card resolves to a media URL
- **THEN** the URL addresses the copied file under the art store root and no request path resolves into the seed root

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

### Requirement: Seed cards carry seed provenance and no reproduction set
A card appended by seed synchronization SHALL carry `source` `seed`, `prompt` `None`, `seed` `None`,
`checkpoint` `None`, an empty `requested_fields`, and `binding` `None`. It SHALL otherwise be an
ordinary card: deletable, default-settable, and resolvable through the standard chain.

#### Scenario: A seed card declares its provenance
- **WHEN** a seed image is synchronized
- **THEN** its card carries `source` `seed`, no prompt pair, no generation seed, no checkpoint, an empty field list, and no binding

#### Scenario: A seed card is an ordinary card
- **WHEN** a player deletes a seed card or makes it the subject's default
- **THEN** the operation succeeds exactly as it does for a generated card

### Requirement: An optional per-subject manifest declares the default and the face rectangle
A subject's seed folder MAY contain a `manifest.json` declaring a `default` filename and a
`face_rect`. When present and valid, the named file's card SHALL become the subject's default and the
declared rectangle SHALL be validated by the standard face-rect rules and applied to that subject's
seed cards. When the manifest is absent, unreadable, or invalid, the first file by sorted name SHALL
be the default candidate and seed cards SHALL take the shared default rectangle, with one bounded
diagnostic for an invalid manifest. A manifest default SHALL apply only when the subject has no
`default_image_id` yet, so a player's chosen default is never overwritten by a later restart.

#### Scenario: A manifest selects the default and the rectangle
- **WHEN** a subject's seed folder declares a valid manifest naming one of its files and a valid rectangle
- **THEN** that file's card becomes the subject's default and the seed cards carry the declared rectangle

#### Scenario: No manifest falls back to sorted order and the shared rectangle
- **WHEN** a subject's seed folder has no manifest
- **THEN** the first file by sorted name is the default candidate and the seed cards carry the shared default rectangle

#### Scenario: An invalid manifest degrades with one diagnostic
- **WHEN** a manifest is unreadable, is not an object, names a missing file, or declares an invalid rectangle
- **THEN** one bounded diagnostic is logged, the sorted-name and shared-rectangle rules apply, and synchronization continues

#### Scenario: A player's chosen default survives a restart
- **WHEN** a subject already has an explicitly chosen default and its manifest names a different file
- **THEN** the chosen default is preserved across the synchronization

