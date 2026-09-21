## ADDED Requirements

### Requirement: Authored room prose is Traditional Chinese
Every authored room description the game ships SHALL be Traditional Chinese prose — both the
`desc` of a grid prototype and the interior description a place record carries. A room's name
and its description SHALL be in the same language: a Chinese room name over an English body is
the specific defect this rule exists to prevent, because it is the state the codebase reached
by nobody checking.

Authoring notes, specification identifiers and change names SHALL NOT appear in a description.
They are player-facing text.

A guard SHALL check this over the whole shipped corpus, so a new English description fails
rather than accumulating.

#### Scenario: Every shipped room description is Traditional Chinese
- **WHEN** every authored grid prototype description and every place's interior description is
  inspected
- **THEN** each is predominantly Han prose with no sentence-length run of English words

#### Scenario: An English description is rejected
- **WHEN** the guard runs against a synthetic room whose description is an English sentence
- **THEN** it fails, naming the room

#### Scenario: No description carries an authoring note
- **WHEN** the shipped descriptions are searched for specification identifiers and change names
- **THEN** none is found
