## MODIFIED Requirements

### Requirement: Proposals are validated deterministically against the registries
The `character_creation` layer SHALL emit proposals of exactly
`{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`.
Every proposal SHALL be validated deterministically before any presentation or activation proceeds:
`race_key` exists in the lore registry; `subrace_key` is a registered subrace belonging to that
race (a null, missing, or incompatible subrace is a whole-proposal failure, since every race has at
least one subrace); `allocations` fall within that race's bands; every `suggested_skills` key
exists in the skill registry; and `persona` contains exactly the three text fields with bounded
lengths. The proposal SHALL NOT carry numeric values beyond the allocation dict and SHALL NOT carry
an age field: the LLM never chooses mechanical numbers or ages, and the adult gate remains entirely
player-entered and deterministically validated. Any failure — including an invalid persona shape,
over-length text, or a missing/incompatible subrace — SHALL be treated as a whole-proposal
validation failure: the proposal SHALL be retried with the error appended and, on exhaustion,
degrade to the stable unavailable message; no partial proposal (for example race accepted but
persona discarded) SHALL ever proceed.

#### Scenario: A valid proposal passes and guides the flow
- **WHEN** the layer returns a proposal whose keys all resolve in the registries and whose
  allocations lie inside the race's bands
- **THEN** the proposal is accepted, its summary is presented, and no registration or activation
  state changes yet

#### Scenario: A proposal without a subrace is rejected
- **WHEN** the proposal's `subrace_key` is null, missing, or absent
- **THEN** validation rejects the whole proposal with a named error and it never proceeds

#### Scenario: An unregistered race or skill key is rejected
- **WHEN** the proposal references a race, subrace, or skill key absent from the registries
- **THEN** the proposal is retried with the named validation error and never proceeds

#### Scenario: Out-of-band allocations are rejected
- **WHEN** the proposal's allocations exceed the race's allowed bands
- **THEN** the proposal is rejected with a named error and nothing proceeds

#### Scenario: An invalid persona rejects the whole proposal
- **WHEN** the proposal's persona is missing a field, has an extra field, or exceeds the length
  bounds
- **THEN** the whole proposal is rejected and retried with the named error; the race and
  allocations are never accepted independently of the persona

#### Scenario: An age or mechanical number in the proposal is rejected
- **WHEN** the proposal carries an age field or a numeric field outside the allocation dict
- **THEN** validation rejects the proposal and the adult gate remains the only age authority
