## MODIFIED Requirements

### Requirement: One closed declaration states what every subject kind's gallery may do
`world/art/gallery_kinds.py` SHALL declare exactly one immutable capability record per art subject
kind, and that declaration SHALL be the single origin of every per-kind gallery rule. Each record
SHALL carry at least: whether the kind has a gallery at all, the directory segment its stored
identities use, the maximum number of cards one record may hold, whether the kind supports equipment
bindings, whether a generation request for the kind requires the canonical-age precondition, whether
the kind supports a prompt field selection, and whether the kind supports free-form prompt text. A
kind without a gallery SHALL be declared explicitly as such rather than being represented by an absent
entry, so "this kind has no gallery" is an assertion in the table and not an accident of a missing key.

The character portrait kind SHALL declare the age precondition, field-selection support, binding
support, free-text support, and no card maximum. The monster portrait kind SHALL declare none of those
four capabilities and a maximum of one card: a monster's fewer capabilities are a declaration, not a
special case in the code that serves it.

The declaration SHALL be data only: it SHALL perform no I/O, read no settings, and hold no mutable
state, so the same kind resolves the same capabilities in every process.

#### Scenario: Every declared capability is readable from one place
- **WHEN** the capability record for the character kind and for the monster kind are read
- **THEN** each reports its gallery-bearing flag, store directory segment, maximum card count, binding support, age precondition, field-selection support, and free-text support without consulting any other module

#### Scenario: A kind with no gallery is declared, not omitted
- **WHEN** the capability record for the scene kind is read
- **THEN** an entry exists that declares the kind as having no gallery, and reading it raises no error

#### Scenario: The declaration is immutable
- **WHEN** a caller attempts to mutate a capability record or the table that holds them
- **THEN** the attempt fails and no other caller observes a changed capability

#### Scenario: The monster kind declares strictly fewer capabilities than the character kind
- **WHEN** the character and monster capability records are compared
- **THEN** the monster declares no binding support, no field selection, no free text, no age precondition, and a maximum of one card, while the character declares all four capabilities and no maximum
