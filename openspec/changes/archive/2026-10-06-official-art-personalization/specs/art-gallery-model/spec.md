## MODIFIED Requirements

### Requirement: One gallery record per art subject carries an ordered card list and a default
`world/art/gallery.py` SHALL persist at most one `GalleryRecord` (an Evennia `DefaultScript`) per
art subject, keyed `gallery:<full-subject-key>`, carrying the subject kind and un-prefixed subject
key (mirroring `ArtAssetRecord`), an append-ordered `cards` list, a nullable `default_image_id`,
the subject's personal official-art preference state (see the preference requirement), and
the subject's last generation error code and timestamp. The record SHALL hold no live object
reference. Records SHALL be created lazily — on the first card append, the first recorded generation
error, the first explicit default set, or the first explicit official-preference write (a personal
official selection or geometry override) — never by a startup scan, so a subject with no record is a
legal state that yields an empty card list and unset preferences. An official-preference write on a
subject with no record SHALL create the record with `cards: []` and `default_image_id` `None`, and a
clear of an absent preference SHALL be a no-op that creates nothing. The first card appended to an empty record SHALL become that record's default; a later
append SHALL NOT change the default. An explicit default set SHALL name an existing card of that
record and SHALL be rejected otherwise. Card-default semantics SHALL be unchanged and SHALL stay
distinct from the personal official selection, which is not a default-card operation.

#### Scenario: A subject with no record yields an empty gallery
- **WHEN** the card list is read for a subject that has never been written
- **THEN** the read returns an empty list, no record is created, and no error is raised

#### Scenario: The first appended card becomes the default
- **WHEN** a card is appended to a subject with no record
- **THEN** the record is created with that one card and `default_image_id` equal to that card's `image_id`

#### Scenario: A later append leaves the default alone
- **WHEN** a second card is appended to a record that already has a default
- **THEN** the card list has two entries in append order and `default_image_id` still names the first card

#### Scenario: Setting a default to an unknown card is rejected
- **WHEN** an explicit default set names an `image_id` that no card of the record carries
- **THEN** a typed validation error is raised and the record's `default_image_id` is unchanged

#### Scenario: The first official preference creates a card-less record
- **WHEN** a personal official selection is written for a subject that has never been written
- **THEN** the record is created with `cards: []`, `default_image_id: None`, and the selection set — and a runtime default-card rule is otherwise unchanged

#### Scenario: Clearing an unset preference creates nothing
- **WHEN** a clear-selection or clear-override request arrives for a subject with no record
- **THEN** the write is a no-op and no record exists afterward

## ADDED Requirements

### Requirement: Gallery records carry entity-local official-art preferences as first-class fields
`world/art/gallery.py` SHALL extend each subject's `GalleryRecord` with personal official-art
preference state — the explicitly selected official image identity (nullable) and a bounded map of
per-identity geometry overrides (face rectangle and stage triple) — written ONLY through
`world/art/gallery.py`'s public API under the existing `gallery_lock` discipline, exactly like card
mutations. Preference state SHALL NOT be stored as a card in `cards` and SHALL NOT participate in
card rules (the card contract, the monster card cap, binding eligibility, and default-card
semantics are unchanged). A preference write SHALL NOT create, modify, or delete any file under the
official root or the art store. Reads of preference state SHALL be tolerant with the existing skip
discipline: a malformed stored preference SHALL be treated as absent with one bounded diagnostic,
never fatal.

#### Scenario: Preference writes obey the sole writer
- **WHEN** the production modules are inspected for writes to official-art preference fields
- **THEN** only `world/art/gallery.py` mutates them, every write ran under `gallery_lock`, and no other module writes the record

#### Scenario: Preferences are not cards
- **WHEN** a subject holds a personal official selection and one geometry override while its `cards` list is empty
- **THEN** the tolerant card read still returns zero cards, the monster one-card cap is unaffected, and the panel's card rows remain empty

#### Scenario: A malformed preference degrades to absent
- **WHEN** a stored preference fails validation on read
- **THEN** it reads as absent, one `gallery_card_invalid`-style bounded diagnostic names the subject, and the record's valid fields still read
