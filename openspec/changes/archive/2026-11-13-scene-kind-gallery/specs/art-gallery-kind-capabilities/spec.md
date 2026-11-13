## MODIFIED Requirements

### Requirement: One closed declaration states what every subject kind's gallery may do
`world/art/gallery_kinds.py` SHALL declare exactly one immutable capability record per art subject
kind, and that declaration SHALL be the single origin of every per-kind gallery rule. Each record
SHALL carry at least a gallery-presence flag, the directory segment its stored identities use, the
maximum number of cards one record may hold, and flags for equipment-binding support,
canonical-age precondition, prompt-field selection, and free-form prompt-text support.

#### Scenario: Every declared capability is readable from one place
- **WHEN** the capability record for the character kind and for the monster kind are read
- **THEN** each reports its gallery-bearing flag, store directory segment, maximum card count, binding support, age precondition, field-selection support, and free-text support without consulting any other module

#### Scenario: A kind with no gallery is declared, not omitted
- **WHEN** a test declaration marks a synthetic kind as having no gallery and its record is read
- **THEN** an entry exists that declares the kind as having no gallery, and reading it raises no error

#### Scenario: The declaration is immutable
- **WHEN** a caller attempts to mutate a capability record or the table that holds them
- **THEN** the attempt fails and no other caller observes a changed capability

#### Scenario: The monster kind declares strictly fewer capabilities than the character kind
- **WHEN** the character and monster capability records are compared
- **THEN** the monster declares no binding support, no field selection, no free text, no age precondition, and a maximum of one card, while the character declares all four capabilities and no maximum

#### Scenario: No-gallery is asserted in the table, never an absent key
- **WHEN** the declaration is consulted for a kind that has no gallery
- **THEN** the kind is declared explicitly as gallery-less rather than represented by an absent entry, so "this kind has no gallery" is an assertion in the table and not an accident of a missing key

#### Scenario: The character portrait kind declares its full capability set
- **WHEN** the character portrait capability record is read
- **THEN** it declares the canonical-age precondition, prompt-field-selection support, equipment-binding support, free-form prompt-text support, and no card maximum

#### Scenario: A monster's fewer capabilities are a declaration, not a code special case
- **WHEN** the monster portrait capability record is read
- **THEN** it declares none of the age precondition, field-selection, binding, and free-text capabilities and a maximum of one card, with no special case for monsters in the code that serves the kind

#### Scenario: The declaration is data only
- **WHEN** the declaration module is exercised in any process
- **THEN** it performs no I/O, reads no settings, and holds no mutable state, so the same kind resolves the same capabilities in every process


## ADDED Requirements

### Requirement: The scene kind declares a one-card gallery without geometry
The scene kind SHALL be declared gallery-bearing with the store directory `scene`, at most one card, card deletion, and no binding, age precondition, prompt field selection, free text, face rectangle or stage transform.

#### Scenario: The scene record reads as declared
- **WHEN** the capability record of the scene kind is read
- **THEN** it reports a gallery, directory `scene`, `max_cards` 1, `supports_card_delete` true, and every other capability false

#### Scenario: A second scene card replaces the first
- **WHEN** a scene subject holding one card settles a new gallery job
- **THEN** the record holds only the new card and the old card's file is deleted
