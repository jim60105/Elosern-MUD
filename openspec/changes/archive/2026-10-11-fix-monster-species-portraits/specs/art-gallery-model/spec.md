# Spec Delta

## MODIFIED Requirements

### Requirement: Gallery records carry entity-local official-art preferences as first-class fields
Character subjects SHALL retain official preferences in their own gallery record. Monster official preferences SHALL be stored on the individual entity, separate from reusable species cards, through the existing public preference writer and gallery lock. Both stores SHALL carry a nullable official selection and bounded identity-keyed geometry overrides with the same tolerant validation and no file writes.

#### Scenario: Preference writes obey the sole writer
- **WHEN** production modules write official preference state
- **THEN** only the existing gallery preference owner writes it under its lock; monster entity attributes and character records obey the same writer discipline

#### Scenario: Preferences stay out of the card rules
- **WHEN** preference state is stored alongside cards
- **THEN** it SHALL NOT be stored as a card in `cards` and SHALL NOT participate in card rules (the card contract, the monster card cap, binding eligibility, and default-card semantics are unchanged)

#### Scenario: Preference writes touch no files
- **WHEN** a preference write runs
- **THEN** it SHALL NOT create, modify, or delete any file under the official root or the art store

#### Scenario: Preference reads are tolerant with the skip discipline
- **WHEN** preference state is read
- **THEN** reads SHALL be tolerant with the existing skip discipline: a malformed stored preference SHALL be treated as absent with one bounded diagnostic, never fatal

#### Scenario: Preferences are not cards
- **WHEN** a subject holds a personal official selection and one geometry override while its `cards` list is empty
- **THEN** the tolerant card read still returns zero cards, the monster one-card cap is unaffected, and the panel's card rows remain empty

#### Scenario: A malformed preference degrades to absent
- **WHEN** a stored preference fails validation on read
- **THEN** it reads as absent, one `gallery_card_invalid`-style bounded diagnostic names the subject, and the record's valid fields still read
#### Scenario: Species cards cannot carry another entity personal choice
- **WHEN** two monsters of one visual species have different official selections and geometry
- **THEN** their species record contains reusable cards only, and each entity retains its own independent preferences


### Requirement: One gallery record per art subject carries an ordered card list and a default
`world/art/gallery.py` SHALL persist at most one `GalleryRecord` (an Evennia `DefaultScript`) per
art subject, keyed `gallery:<full-subject-key>`, carrying the subject kind and un-prefixed subject
key (mirroring `ArtAssetRecord`), an append-ordered `cards` list, a nullable `default_image_id`,
the subject's personal official-art preference state (see the preference requirement), and the
subject's last generation error code and timestamp. Records SHALL be created lazily, never by a
startup scan.

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
- **WHEN** a character writes its first official preference or a monster writes one through a valid entity context
- **THEN** the character retains its cardless-record behavior; the monster stores only entity-local preference state and creates no species record or card

#### Scenario: Clearing an unset preference creates nothing
- **WHEN** a character or monster clears an unset official preference
- **THEN** the clear is a no-op and creates no record or entity preference state

#### Scenario: The record holds no live object reference
- **WHEN** a gallery record is persisted and re-read
- **THEN** it carries only serialized state and no live object reference

#### Scenario: Record creation follows the documented lazy triggers
- **WHEN** gallery record creation is exercised
- **THEN** card append, recorded generation error and explicit card default retain their existing triggers; personal official writes create a character record only, while monster personal writes stay entity-local; startup and presentation never manufacture a record

#### Scenario: An explicit default set names an existing card
- **WHEN** an explicit default set is submitted
- **THEN** it SHALL name an existing card of that record and SHALL be rejected otherwise, and card-default semantics SHALL be unchanged and SHALL stay distinct from the personal official selection, which is not a default-card operation

#### Scenario: The first append sets the default and later appends do not
- **WHEN** cards are appended to a record
- **THEN** the first card appended to an empty record SHALL become that record's default, and a later append SHALL NOT change the default

