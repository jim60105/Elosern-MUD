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
