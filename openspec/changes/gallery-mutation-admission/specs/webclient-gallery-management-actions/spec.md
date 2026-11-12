## ADDED Requirements

### Requirement: Gallery mutations require an admitted subject
Every mutating gallery adapter SHALL, before reading or writing any card, record or preference, re-derive whether its subject belongs to any enabled gallery category for the acting session's actor. A subject in no enabled category SHALL be rejected with `subject_not_admitted` and the standard gallery refresh; a subject admitted through a category other than the selected one SHALL proceed.

#### Scenario: A stranger's gallery cannot be edited
- **WHEN** `gallery.default.set` names a card of a named NPC that is neither in the actor's party nor in any other enabled category
- **THEN** the result is `rejected` with `subject_not_admitted`, no record changed, and one update refreshes gallery, art and roster

#### Scenario: Another category's subject is admitted
- **WHEN** the selected category is `monster` and `gallery.generate` names a party companion's subject
- **THEN** the request proceeds through the service seam as before

#### Scenario: An unsighted species is refused
- **WHEN** `gallery.generate` names a registered species the actor has not sighted
- **THEN** the result is `rejected` with `subject_not_admitted` and nothing is queued

#### Scenario: Official preference writes are covered
- **WHEN** `gallery.official.select` names a subject in no enabled category
- **THEN** the result is `rejected` with `subject_not_admitted` and no preference changed
