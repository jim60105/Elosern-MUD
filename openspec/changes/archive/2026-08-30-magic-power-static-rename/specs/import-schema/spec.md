## MODIFIED Requirements

### Requirement: stats only accepts the eight documented trait keys
`CHARACTER_SCHEMA_V1`'s `stats` property SHALL restrict its keys to exactly `hp`, `mp`, `sp`,
`atk_phys`, `agility`, `defense`, `magic_power`, and `guild_merit`, each a non-negative integer
(`hp` strictly positive), with no additional properties permitted.

#### Scenario: An unknown stats key fails schema validation
- **WHEN** a character record's `stats` object includes a key not in the documented eight (e.g.
  `"luck": 10`)
- **THEN** schema validation fails due to `additionalProperties: false`

#### Scenario: A negative stat value fails schema validation
- **WHEN** a character record's `stats.atk_phys` is `-5`
- **THEN** schema validation fails
