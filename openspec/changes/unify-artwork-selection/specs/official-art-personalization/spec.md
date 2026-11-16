## MODIFIED Requirements

### Requirement: A personal official selection is an entity-local art preference
Explicit official selections SHALL use stable identities inside the resolved content reference. Capability-declared preference scope SHALL preserve character subject state and monster entity-local state; scenes SHALL use shared archetype subject state. Explicit runtime-default actions SHALL clear the same owner's official selection; generation alone SHALL NOT clear it.

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

#### Scenario: Scene selection is archetype-scoped
- **WHEN** one admitted scene action selects an official image and two rooms share that archetype
- **THEN** both inherit that choice through the common chain while room overrides remain higher priority; no room attributes or official files change

#### Scenario: Regeneration preserves explicit official choice
- **WHEN** a subject with an explicit official selection settles a generated replacement
- **THEN** its selection remains stored and resolves ahead of that replacement
