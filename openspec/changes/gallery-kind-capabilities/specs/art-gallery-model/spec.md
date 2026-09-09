## MODIFIED Requirements

### Requirement: Monster subjects hold at most one card
A `GalleryRecord` SHALL hold at most the number of cards its subject kind's capability declaration
names as that kind's maximum. The monster portrait kind SHALL declare a maximum of one; the character
portrait kind SHALL declare NO maximum and SHALL therefore stay uncapped exactly as it is today —
appending to it always accumulates and never replaces, however many cards it already holds. Appending
a card to a record whose kind declares a maximum and already holds it SHALL replace the existing card —
deleting the replaced card's stored file under the confinement rules — and SHALL leave the new card as
the record's default. A card SHALL be rejected when it carries a non-`None` binding for a kind whose
declaration does not support bindings, which the monster portrait kind does not. Both rules SHALL be
enforced by reading the declaration, never by comparing the subject kind inline, so the monster cap and
the monster unbound rule are consequences of that kind's declared capabilities rather than
monster-specific enforcement code.

#### Scenario: A second monster card replaces the first
- **WHEN** a card is appended to a monster subject that already has one card
- **THEN** the record holds exactly one card, it is the new one, it is the default, and the previous card's stored file is deleted

#### Scenario: A bound monster card is rejected
- **WHEN** a card carrying a binding is appended to a monster subject
- **THEN** a typed validation error is raised and the record is unchanged

#### Scenario: A character record stays uncapped
- **WHEN** many cards are appended to a character subject
- **THEN** every card is retained in append order, none is replaced, no stored file is deleted, and the first card is still the default

#### Scenario: The cap follows the declaration
- **WHEN** the enforced cap is exercised against a kind whose declared maximum is changed
- **THEN** the append honours the declared maximum with no edit to the enforcing module
