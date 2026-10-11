# Spec Delta

## MODIFIED Requirements

### Requirement: A personal official selection is an entity-local art preference
An entity SHALL be able to explicitly select one official image — identified by its stable root-relative identity within its content reference — as a personal art preference stored on the entity's own art state. For character subjects, setting an explicit runtime default SHALL clear personal official selection and selecting official artwork SHALL clear the explicit runtime default. For monsters, a shared species card default SHALL remain separate from an entity-local official choice; the entity choice SHALL win without changing another individual.

#### Scenario: Explicit official selection presents ahead of the runtime default
- **WHEN** a subject holds a gallery default card and explicitly selects a valid official image from its content reference
- **THEN** the official image presents (official origin), the gallery default card still exists unchanged, and a matching equipment-bound card would still outrank both

#### Scenario: Selections clear each other
- **WHEN** a character subject with a personal official selection sets a runtime gallery default, and another character subject with a runtime default selects an official image
- **THEN** each ends with exactly one personal default and presents accordingly

#### Scenario: Selection touches no shared state
- **WHEN** a player selects an official image
- **THEN** the mounted directory bytes are unchanged, no card is appended to `GalleryRecord.cards`, and no other entity's presentation changed

#### Scenario: Equipment precedence retained at step 1
- **WHEN** a selected-and-resolving official image competes in presentation step 1
- **THEN** the selection replaces the personal gallery-default choice at step 1, presenting ahead of
  the gallery default card, while equipment-bound runtime cards retain their existing precedence

#### Scenario: Selection side-effect limits
- **WHEN** a personal official selection is set
- **THEN** the selection SHALL NOT edit the mounted directory, SHALL NOT create or modify a gallery card, and SHALL NOT change any other entity's presentation

#### Scenario: Species default edits do not clear an individual choice
- **WHEN** a species gallery default changes while two same-species individuals hold distinct official choices
- **THEN** both choices remain unchanged and present independently, and no other species preference changes

