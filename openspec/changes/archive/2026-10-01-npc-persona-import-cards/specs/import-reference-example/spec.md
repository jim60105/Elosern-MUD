## REMOVED Requirements

### Requirement: The reference example exercises the persona block with a background
**Reason**: The reference example is a shipped NPC import example, and NPC imports now carry exactly the seven-field compact card, which has no `background` key.
**Migration**: See "The reference example carries a complete compact NPC card"; player imports may still carry `background` through the opaque player persona.

### Requirement: The reference example exercises every major schema branch it can demonstrate on its race
**Reason**: Its persona clause required an uninspected opaque object, which contradicts NPC-target card validation.
**Migration**: Replaced unchanged except for the persona clause by "The reference example exercises every major schema branch and a complete NPC card".

## ADDED Requirements

### Requirement: The reference example carries a complete compact NPC card
`world/imports/examples/example_character.json`'s `persona` SHALL be a complete compact NPC card
written in Traditional Chinese — `identity` with `public` and `hidden`, `appearance`,
`personality`, `speech_style`, `life_story`, `habit`, and `social_connection` — that passes the
card contract as validated against the NPC default target with zero rejections and zero warnings,
and SHALL carry no `background` key.

#### Scenario: The reference persona is a valid compact card
- **WHEN** the example is validated with `world.imports.validate` against the NPC default
- **THEN** its persona passes the compact card contract and the report has zero rejections and zero warnings

#### Scenario: The reference persona has no background key
- **WHEN** the example's `persona` object is inspected
- **THEN** it has exactly the seven card fields and no `background` key

### Requirement: The reference example exercises every major schema branch and a complete NPC card
`examples/example_character.json` SHALL set a `subrace` (exercising the race/subrace cross-check),
a fully populated `stats` object (all eight keys), an empty `disguised_stats` object (the record's
`human` race cannot use divine arts, so a non-empty layer would be rejected by the
`disguised-stats-boundary` capability's race guard), non-empty `skills` and `passives` arrays, a
`sexual_baseline` with `arousal`, `virgin`, `sensitivity`, and at least one additional optional level
field set, and a `persona` that is a complete compact NPC card.

#### Scenario: The example sets a subrace consistent with its race
- **WHEN** `examples/example_character.json`'s `race` and `subrace` fields are inspected
- **THEN** `subrace` resolves in `SUBRACE_REGISTRY` and its `race_key` equals the record's `race`

#### Scenario: The example's stats object sets all eight documented keys
- **WHEN** `examples/example_character.json`'s `stats` object is inspected
- **THEN** it contains exactly `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_power`,
  and `guild_merit`

#### Scenario: The example's disguised_stats stays empty because its race cannot carry a layer
- **WHEN** `examples/example_character.json`'s `disguised_stats` object is inspected
- **THEN** it is empty, because the record's race cannot use divine arts and a non-empty layer on
  such a race is rejected at validation

#### Scenario: The example's sexual_baseline sets an optional field beyond the required three
- **WHEN** `examples/example_character.json`'s `sexual_baseline` object is inspected
- **THEN** it sets `arousal`, `virgin`, and `sensitivity` (the required fields) plus at least one of
  `wetness`, `shame`, `exposure`, or `climax_phase`

#### Scenario: The example's persona is a complete compact card
- **WHEN** `examples/example_character.json`'s `persona` object is inspected through the card contract
- **THEN** it is a valid seven-field compact NPC card
