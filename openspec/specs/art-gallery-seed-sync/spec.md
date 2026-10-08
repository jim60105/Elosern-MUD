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
`PROMPT_ROOT` precedent for directory roots rather than the typed `ART_SD_*` knob table. Seed
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

#### Scenario: Bulk seed art can never be committed
- **WHEN** seed art lands in the default `ART_SEED_ROOT` directory
- **THEN** the repository gitignores the default directory, so bulk seed art can never be committed

#### Scenario: A degenerate seed root means "synchronize nothing"
- **WHEN** the seed root is absent, empty, symlinked, or unreadable
- **THEN** that is a supported configuration meaning "synchronize nothing"
- **AND** it logs exactly one `gallery_seed_sync` event and NEVER fails startup

### Requirement: Seed synchronization is idempotent, path-derived, and additive
`world/art/gallery_seed.py::sync_all()` SHALL run as a named startup step and SHALL walk the seed
root's `<kind>/<subject-key>/` layout. For each image file whose extension is in the closed set of
store extensions, it SHALL derive that file's card `image_id` deterministically from the file's
path relative to the seed root, copy the file into the subject's gallery path under the store
root, and append one card through the gallery write API.

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

#### Scenario: A hard-linked destination is replaced without touching the other link
- **WHEN** an unreferenced derived destination shares its inode with another name (as a world save's hardlinked mirror does) and its bytes differ from the seed file
- **THEN** the destination name receives the seed bytes through an atomic rename, the other name keeps its original bytes, and the card is appended

#### Scenario: Kind and subject-key segments are validated against declarations
- **WHEN** `sync_all()` interprets a `<kind>/<subject-key>/` path segment
- **THEN** `<kind>` is the store directory segment of a subject kind whose capability declaration
  has a gallery — read from that declaration rather than from a vocabulary restated here — and
  `<subject-key>` is a valid art subject key

#### Scenario: A card whose derived id already exists is skipped without copying
- **WHEN** a seed file's derived card id is already present in the subject's gallery
- **THEN** it is skipped without copying, so repeated runs never duplicate a card and never
  rewrite a file

#### Scenario: Invalid seed entries are skipped with a bounded diagnostic
- **WHEN** a file has an unsupported extension, an unresolvable subject key, or an unknown kind
  directory
- **THEN** it is skipped with a bounded diagnostic

#### Scenario: Existing cards are never deleted, replaced, or reordered
- **WHEN** `sync_all()` runs against a subject whose gallery already holds cards
- **THEN** synchronization NEVER deletes, replaces, or reorders a card that already exists,
  including cards the player generated

#### Scenario: The card maximum is read from the kind's declaration
- **WHEN** surplus seed files would exceed a kind's declared card maximum
- **THEN** the surplus files are skipped with a bounded diagnostic rather than replacing an
  existing card, and that limit is read from the declaration rather than tested for a particular
  kind

#### Scenario: Hostile seed files are verified after opening
- **WHEN** `sync_all()` reads files out of the (potentially hostile) seed tree
- **THEN** each opened file is verified AFTER the open — regular, hard-link count one, within a
  size cap, never reached through a symlink — so a planted link or aliased inode is refused rather
  than copied

#### Scenario: Store writes are no-follow and atomic
- **WHEN** `sync_all()` writes into the store
- **THEN** an existing destination is opened no-follow and anything that is not a regular file is
  refused, and a differing destination is replaced only by writing a temporary sibling and
  atomically renaming it over the name, never by writing in place, so another hard link to the old
  inode (a world save) keeps its bytes

#### Scenario: Raw record entries reserve their stored identity
- **WHEN** a raw record entry (valid or malformed) names a `stored_identity`
- **THEN** the file it points at is never overwritten even when the card itself no longer
  validates

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
seed cards.

#### Scenario: A manifest selects the default and the rectangle
- **WHEN** a subject's seed folder declares a valid manifest naming one of its files and a rectangle that is pixel-square for every eligible image of that subject
- **THEN** that file's card becomes the subject's default and the seed cards carry the declared rectangle

#### Scenario: No manifest falls back to sorted order and the shared rectangle
- **WHEN** a subject's seed folder has no manifest
- **THEN** the first file by sorted name is the default candidate and each seed card carries the shared default rectangle as fitted to that card's own image (the fitted default square computed from its decoded pixel size)

#### Scenario: A rectangle square for only some of the subject's images degrades whole
- **WHEN** a manifest declares a rectangle that is pixel-square for one eligible image but not for another of the same subject's eligible images
- **THEN** one bounded invalid-rect diagnostic is logged, neither the manifest default nor the rectangle is honored, the sorted-name rule applies, cards take their fitted defaults, and synchronization continues

#### Scenario: An invalid manifest degrades with one diagnostic
- **WHEN** a manifest is unreadable, is not an object, names a missing file, or declares an invalid or non-square rectangle
- **THEN** one bounded diagnostic is logged, the sorted-name and fitted-default rules apply, and synchronization continues

#### Scenario: A player's chosen default survives a restart
- **WHEN** a subject already has an explicitly chosen default and its manifest names a different file
- **THEN** the chosen default is preserved across the synchronization

#### Scenario: The declared rectangle must be pixel-square for every eligible image
- **WHEN** a manifest's fields are about to be honored
- **THEN** the sync first decodes the pixel sizes of the subject's eligible images and requires
  the declared rectangle to be pixel-square for every one of them, since the standard rules
  include the pixel-square contract and the manifest's rect is applied across every eligible
  image of the subject (an undecodable or missing size degrades the manifest the same way an
  invalid rect does — a rectangle square on two different aspect ratios only coincidentally
  exists)

#### Scenario: A manifest default applies only before any default exists
- **WHEN** a manifest declares a default for a subject
- **THEN** it applies only when the subject has no `default_image_id` yet, so a player's chosen
  default is never overwritten by a later restart
