## MODIFIED Requirements

### Requirement: Monster subjects hold at most one card
A gallery SHALL enforce the capability-declared maximum. Scene and monster subjects SHALL hold at most one generated card; successful regeneration SHALL atomically replace its card/default and clean the replaced file after commit. Failure SHALL retain the previous card/default and bytes. Character galleries SHALL remain uncapped.

#### Scenario: A second monster card replaces the first
- **WHEN** a card is appended to a monster subject that already has one card
- **THEN** the record holds exactly one card, it is the new one, it is the default, and the previous card's stored file is deleted

#### Scenario: Appending to a capped record installs the sole card
- **WHEN** a card is appended to a record whose kind declares a maximum
- **THEN** the append SHALL install the new card as its sole card and SHALL leave the new card as the record's default

#### Scenario: A bound monster card is rejected
- **WHEN** a card carrying a binding is appended to a monster subject
- **THEN** a typed validation error is raised and the record is unchanged

#### Scenario: A character record stays uncapped
- **WHEN** many cards are appended to a character subject
- **THEN** every card is retained in append order, none is replaced, no stored file is deleted, and the first card is still the default

#### Scenario: The cap follows the declaration
- **WHEN** the enforced cap is exercised against a kind whose declared maximum is changed
- **THEN** the append honours the declared maximum with no edit to the enforcing module

#### Scenario: Character appends always accumulate
- **WHEN** cards are appended to the character portrait kind
- **THEN** appending always accumulates and never replaces, however many cards it already holds

#### Scenario: A replaced card's file is deleted under the confinement rules
- **WHEN** appending a card to a record whose kind declares a maximum replaces an existing card
- **THEN** the replaced card's stored file is deleted under the confinement rules; because the only admitted maximum is one, a capped record is never partially full and appending to an empty capped record installs the card exactly as the monster append does today

#### Scenario: A binding on a binding-incapable kind is rejected
- **WHEN** a card carries a non-`None` binding for a kind whose declaration does not support bindings, which the monster portrait kind does not
- **THEN** the card SHALL be rejected, so the monster cap and the monster unbound rule are consequences of that kind's declared capabilities rather than monster-specific enforcement code

#### Scenario: Scene and monster replacement is observable
- **WHEN** a scene and a monster subject each hold a card and each settles another generation
- **THEN** each gallery contains only its replacement with its default naming that replacement; replaced files are removed after commit

#### Scenario: Failed replacement preserves display
- **WHEN** a capped subject has a valid card and its next generation fails
- **THEN** the prior card, default and file remain unchanged and its recorded failure stays truthful

### Requirement: One gallery record per art subject carries an ordered card list and a default
One lazily created gallery record per subject SHALL carry typed subject kind/key, ordered cards, nullable default image id, capability-scoped official preferences and last generation error/timestamp. Subject-scoped character/scene preferences SHALL create cardless records on explicit writes; monster preferences SHALL stay entity-local. Presentation and startup scans SHALL NOT create records.

#### Scenario: A subject with no record yields an empty gallery
- **WHEN** the card list is read for a subject that has never been written
- **THEN** the read returns an empty list, no record is created, and no error is raised

#### Scenario: The first appended card becomes the default
- **WHEN** a card is appended to a subject with no record
- **THEN** the record is created with that one card and `default_image_id` equal to that card's `image_id`

#### Scenario: A later append leaves the default alone
- **WHEN** a second card is appended to an uncapped record that already has a default
- **THEN** the card list has two entries in append order and `default_image_id` still names the first card

#### Scenario: Setting a default to an unknown card is rejected
- **WHEN** an explicit default set names an `image_id` that no card of the record carries
- **THEN** a typed validation error is raised and the record's `default_image_id` is unchanged

#### Scenario: The first official preference creates a card-less record
- **WHEN** a character or scene writes its first official preference or a monster writes one through a valid entity context
- **THEN** a subject-scoped owner gets a cardless record; a monster stores only entity-local preference state and creates no species record or card

#### Scenario: Clearing an unset preference creates nothing
- **WHEN** a character, scene or monster clears an unset official preference
- **THEN** the clear is a no-op and creates no record or entity preference state

#### Scenario: The record holds no live object reference
- **WHEN** a gallery record is persisted and re-read
- **THEN** it carries only serialized state and no live object reference

#### Scenario: Record creation follows the documented lazy triggers
- **WHEN** gallery record creation is exercised
- **THEN** card append, recorded generation error and explicit card default retain their existing triggers; official writes create character or scene subject records according to declared scope, while monster writes stay entity-local; startup and presentation never manufacture a record

#### Scenario: An explicit default set names an existing card
- **WHEN** an explicit default set is submitted
- **THEN** it SHALL name an existing card of that record and SHALL be rejected otherwise, and card-default semantics SHALL be unchanged and SHALL stay distinct from the personal official selection, which is not a default-card operation

#### Scenario: The first append sets the default and later appends do not
- **WHEN** cards are appended to an uncapped record
- **THEN** the first card appended to an empty record SHALL become that record's default, and a later append SHALL NOT change the default
